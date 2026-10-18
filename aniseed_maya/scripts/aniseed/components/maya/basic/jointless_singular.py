"""
Provides the "Basic : Singular (Jointless)" component, which creates a single
control placed at a guide without driving a joint.
"""
import mref
import aniseed
import aniseed_toolkit


class JointlessSingular(aniseed.RigComponent, aniseed.mixins.MirrorMixin):
    """
    A basic component which creates a single control placed at a guide,
    without driving a joint
    """

    identifier = "Basic : Singular (Jointless)"

    def __init__(self, *args, **kwargs):
        """
        Declares the "Parent" and "Guide" inputs, the naming, shape, offset and
        world alignment options, and the "Control" and "Offset Control"
        outputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the generated control's org will be parented under",
            group="Control Rig",
        )

        self.declare_input(
            name="Guide",
            value="",
            description="Name of the guide for placement",
            group="Control Rig",
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
        Returns an object selector for the "Parent" and "Guide" inputs, or
        None otherwise.
        """
        if requirement_name in ["Parent", "Guide"]:
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def is_valid(self) -> bool:
        """
        Checks that a parent is given and that the guide exists.
        """
        if not self.input("Parent").get(resolved=False):
            print("You must specify a Parent")
            return False

        guide = self.input("Guide").get()
        if not guide or not mref.objExists(guide):
            print("You must specify a valid Guide")
            return False

        return True

    def suggested_label(self):
        """
        Returns the "Description" option as the suggested label.
        """
        return self.option("Description").get()

    def on_enter_stack(self):
        """
        Hooks the "Parent" input up to the parent component's default output.
        """
        super().on_enter_stack()
        self.input("Parent").hook_to_parent()

    def run(self):
        """
        Creates the singular control at the guide, without an offset visibility
        toggle.
        """
        control, offset_control = aniseed_toolkit.rig.control.create_with_offset(
            description=self.option("Description").get(),
            location=self.option("Location").get(),
            config=self.config,
            shape=self.option("Shape").get(),
            parent=self.input("Parent").get(),
            match_to=self.input("Guide").get(),
            align_to_world=self.option("Align Control To World").get(),
            add_offset=self.option("Add Offset Control").get(),
            offset_visibility_toggle=False,
        )

        self.output("Control").set(control.ctl)

        if offset_control:
            self.output("Offset Control").set(offset_control.ctl)

        return True

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the guide, which is mirrored onto the mirrored component's guide. Empty if
        no guide is set.
        """
        guide = self.input("Guide").get()
        if not guide:
            return []
        return [guide]

    def mirror_mixin_parent_item(self) -> str:
        """
        Nothing is created from the selection, so there is no parent item.
        """
        return ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's guide if it already exists (the search and
        replaced name), otherwise copies the original guide into the mirrored
        hierarchy for this component.
        """
        original_guide = mirrored_from.input("Guide").get()
        if not original_guide:
            return

        if self.mirror_mixin_counterparts_exist([original_guide], [self.input("Guide").get()]):
            return

        self.input("Guide").set(self.mirror_mixin_copy_nodes([original_guide])[0])
