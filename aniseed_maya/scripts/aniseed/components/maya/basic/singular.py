"""
Provides the "Basic : Singular" component, which creates a single control
that parent and scale constrains a joint. It can create the joint from the
current selection when added to the stack and supports mirroring.
"""
import re
import mref
import aniseed
import aniseed_toolkit


class Singular(aniseed.RigComponent, aniseed.mixins.MirrorMixin):
    """
    A basic component which creates a single joint and a single control
    """

    identifier = "Basic : Singular"

    def __init__(self, *args, **kwargs):
        """
        Declares the "Parent" and "Joint" inputs, the naming, shape, offset,
        joint creation and world alignment options, and the "Control" and
        "Offset Control" outputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the generated control's org will be parented under",
            group="Control Rig",
        )

        self.declare_input(
            name="Joint",
            value="",
            description="Name of the joint to drive",
            group="Joints",
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
        """
        Returns a shape selector for "Shape" and a location selector for
        "Location", or None otherwise.
        """
        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(default_item=self.option("Shape").get() or "")

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

        return None

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the "Parent" and "Joint" inputs, or
        None otherwise.
        """
        if requirement_name in ["Parent", "Joint"]:
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def is_valid(self) -> bool:
        """
        Checks that a parent is given and that the joint exists.
        """
        if not self.input("Parent").get(resolved=False):
            print("You must specify a Parent")
            return False

        joint = self.input("Joint").get()
        if not joint or not mref.objExists(joint):
            print("You must specify a valid joint")
            return False

        return True

    def suggested_label(self):
        """
        Builds a label from the title-cased description, the location and a two
        digit counter. Note that the existing label check omits the space before
        the counter, so it never matches and the counter is always 01.
        """
        description = self.option("Description").get()
        description = re.sub(
            r"(?<!^)(?=[A-Z])",
            " ",
            description.replace("_", " "),
        ).title()

        # -- Now add the location
        location = self.option("Location").get()
        label = f"{description} {location}"

        # -- Finally, we want to check if there are already components in the rig
        # -- with this label and form an identifier
        existing_labels = {
            component.label()
            for component in self.rig.components(of_type=self.identifier)
        }
        counter = 1
        while f"{label}{counter:02d}" in existing_labels:
            counter += 1
        return f"{label} {counter:02d}"

    def on_enter_stack(self):
        """
        Hides the "Create Joint" option and, if it is enabled, creates the joint
        from the current selection (matched to its parent), sets the "Joint"
        input and hooks the "Parent" input up to the parent component. There is
        no one-shot guard, so this repeats whenever the component enters the
        stack with "Create Joint" enabled.
        """
        super().on_enter_stack()

        joint_option = self.option("Create Joint")
        joint_option.set_hidden(True)

        if not joint_option.get():
            return

        joint = aniseed_toolkit.scene.joints.create_from_selection(
            name=self.config.generate_name(
                classification=self.config.joint,
                description=self.option("Description").get(),
                location=self.option("Location").get(),
            ),
            match_to_parent=True,
        )
        self.input("Joint").set(joint.name())

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def run(self):
        """
        Creates the singular control (with an offset visibility toggle) and
        parent and scale constrains the joint to the driving control.
        """
        control, offset_control = aniseed_toolkit.rig.control.create_with_offset(
            description=self.option("Description").get(),
            location=self.option("Location").get(),
            config=self.config,
            shape=self.option("Shape").get(),
            parent=self.input("Parent").get(),
            match_to=self.input("Joint").get(),
            align_to_world=self.option("Align Control To World").get(),
            add_offset=self.option("Add Offset Control").get(),
            offset_visibility_toggle=True,
        )

        self.output("Control").set(control.ctl)

        # -- The offset control, when there is one, drives the joint
        driving_control = control
        if offset_control:
            self.output("Offset Control").set(offset_control.ctl)
            driving_control = offset_control

        aniseed_toolkit.scene.constraints.parent_and_scale(
            driving_control.ctl,
            self.input("Joint").get(),
        )
        return True

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the joint this component drives, which is mirrored onto the
        mirrored component's joint. Empty if no joint is set.
        """
        joint = self.input("Joint").get()
        if not joint:
            return []
        return [joint]

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the joint, which is where the mirrored component's joint is
        created. Empty if there is no joint or it has no parent.
        """
        joint = self.input("Joint").get()
        if not joint or not mref.objExists(joint):
            return ""

        parent = mref.get(joint).parent()
        return parent.name() if parent else ""
