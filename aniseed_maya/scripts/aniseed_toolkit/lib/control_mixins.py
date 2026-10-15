"""
Mixins shared by the simple components which create a single control (or
control pair). Compose them alongside RigComponent, mixin first.
"""
import mref
import aniseed

from . import control as _control


class InsertControlMixin:
    """
    Mixin for augments which insert a new control into an existing
    hierarchy. It declares the shared options and the Control output,
    provides their widgets and creates the control.

    Call _declare_control_attributes() after the component has declared
    its own inputs and options.
    """

    def _declare_control_attributes(self, match_description: str, location_description: str):
        """
        Declares the options and output common to all insert control
        augments.
        """
        self.declare_option(
            name="Match Transform To",
            description=match_description,
            value="",
            group="Behaviour",
        )

        self.declare_option(
            name="Name",
            description="Descriptive name token used when generating the control's name.",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            description=location_description,
            value=self.config.middle,
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            description="Aniseed-toolkit control shape used for the inserted control.",
            value="core_cube",
            group="Visuals",
        )

        self.declare_output(
            "Control",
            description="The newly-created control node.",
        )

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                default_item=self.option("Shape").get(),
            )

        if option_name == "Match Transform To":
            return aniseed.widgets.ObjectSelector(component=self)

    def suggested_label(self):
        name = self.option("Name").get()
        location = self.option("Location").get().upper()

        return f"Insert {name} Control {location}"

    def _create_control(self, parent: str, default_match_to: str) -> _control.Control:
        """
        Creates the control under the given parent and sets the Control
        output. The control is matched to the "Match Transform To" option,
        or to default_match_to when that option is empty.
        """
        control = _control.create(
            description=self.option("Name").get(),
            location=self.option("Location").get(),
            parent=parent,
            config=self.config,
            shape=self.option("Shape").get(),
            match_to=self.option("Match Transform To").get() or default_match_to,
        )

        self.output("Control").set(control.ctl)
        return control


class SingularControlMixin:
    """
    Mixin for components which create a single control (with an optional
    offset control beneath it) placed at a given node. It declares the
    shared inputs, options and outputs, provides their widgets and
    validation, and creates the controls.
    """

    # -- The name of the input holding the node the control is placed at
    placement_input = ""

    # -- How the placement input is referred to in validation messages
    placement_label = ""

    def _declare_singular_attributes(
            self,
            placement_description: str,
            placement_group: str,
            create_joint_option: bool = False,
    ):
        """
        Declares the inputs, options and outputs of the component. If
        create_joint_option is True, the "Create Joint" option is declared
        too.
        """
        self.declare_input(
            name="Parent",
            value="",
            description="The node the generated control's org will be parented under",
            group="Control Rig",
        )

        self.declare_input(
            name=self.placement_input,
            value="",
            description=placement_description,
            group=placement_group,
        )

        self.declare_option(
            name="Description",
            description=(
                "Descriptive token used when naming the control (and the "
                "auto-created joint, if ``Create Joint`` is enabled)."
            ),
            value="Singular",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            description="Location token (e.g. md/lf/rt) applied to generated node names",
            value=self.config.middle,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            description="Shape used for the generated control (and the offset control, if enabled)",
            value="core_cube",
            group="Visuals",
            pre_expose=True,
        )

        self.declare_option(
            name="Add Offset Control",
            description=(
                "If enabled, a second control is created and parented under "
                "the main control. The offset control becomes the driving "
                "control for the joint, letting animators add layered offsets "
                "on top of the main control."
            ),
            value=False,
            group="Behaviour",
            pre_expose=True,
        )

        if create_joint_option:
            self.declare_option(
                name="Create Joint",
                description=(
                    "If enabled when the component first enters the stack, a "
                    "driving joint is created automatically (parented to the "
                    "current Maya selection) and wired into the ``Joint`` input."
                ),
                value=True,
                group="Creation",
                pre_expose=True,
            )

        self.declare_option(
            name="Align Control To World",
            description=(
                "If enabled, the generated control is aligned to world "
                "orientation instead of inheriting the joint's orientation."
            ),
            value=False,
            group="Behaviour",
        )

        self.declare_output(
            name="Control",
            description="The main control created by this component",
            is_default=True,
        )
        self.declare_output(
            name="Offset Control",
            description=(
                "The optional offset control created when ``Add Offset "
                "Control`` is enabled. Unset otherwise."
            ),
            is_default=False,
        )

    def option_widget(self, option_name):

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(default_item=self.option("Shape").get() or "")

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

        return None

    def input_widget(self, requirement_name):
        if requirement_name in ["Parent", self.placement_input]:
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def is_valid(self) -> bool:
        if not self.input("Parent").get(resolved=False):
            print("You must specify a Parent")
            return False

        placement = self.input(self.placement_input).get()
        if not placement or not mref.objExists(placement):
            print(f"You must specify a valid {self.placement_label}")
            return False

        return True

    def _create_singular_controls(self, offset_visibility_toggle: bool) -> _control.Control:
        """
        Creates the control (and the offset control, if requested) and sets
        the outputs.

        Args:
            offset_visibility_toggle: If True, a "show_offset" attribute on the
                main control drives the visibility of the offset control shapes

        Returns:
            The control which should drive the result - the offset control if
            there is one, otherwise the main control.
        """
        description = self.option("Description").get()
        location = self.option("Location").get()
        shape = self.option("Shape").get()
        placement = self.input(self.placement_input).get()

        control = _control.create(
            description=description,
            location=location,
            config=self.config,
            shape=shape,
            parent=self.input("Parent").get(),
            match_to=placement,
        )
        driving_control = control

        if self.option("Align Control To World").get():
            mref.get(control.org).set_rotation([0, 0, 0], space="world")

        if self.option("Add Offset Control").get():

            if offset_visibility_toggle:
                show_offset = mref.get(control.ctl).add_attribute(
                    "show_offset",
                    value=False,
                    attribute_type="bool",
                    keyable=False,
                )
                show_offset.set(channelBox=True)

            driving_control = _control.create(
                description=description + "_offset",
                location=location,
                config=self.config,
                shape=shape,
                parent=control.ctl,
                match_to=placement,
            )
            self.output("Offset Control").set(driving_control.ctl)

            if offset_visibility_toggle:
                for shape_node in mref.get(driving_control.ctl).shapes():
                    show_offset.connect(shape_node.attr("visibility"))

        self.output("Control").set(control.ctl)
        return driving_control
