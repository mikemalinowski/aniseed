"""
Provides the "Basic : Singular" component, which creates a single control
that parent and scale constrains a joint. It can create the joint from the
current selection when added to the stack and supports mirroring.
"""
import re
import mref
import aniseed
import aniseed_toolkit


class Singular(aniseed_toolkit.control_mixins.SingularControlMixin, aniseed.RigComponent, aniseed.mixins.MirrorMixin):
    """
    A basic component which creates a single joint and a single control
    """

    identifier = "Basic : Singular"
    placement_input = "Joint"
    placement_label = "joint"

    def __init__(self, *args, **kwargs):
        """
        Declares the singular control attributes with a "Joint" placement input
        and a "Create Joint" option.
        """
        super().__init__(*args, **kwargs)

        self._declare_singular_attributes(
            placement_description="Name of the joint to drive",
            placement_group="Joints",
            create_joint_option=True,
        )

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

        joint = aniseed_toolkit.stack_joints.create_from_selection(
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
        driving_control = self._create_singular_controls(offset_visibility_toggle=True)

        aniseed_toolkit.constraints.parent_and_scale(
            driving_control.ctl,
            self.input("Joint").get(),
        )
        return True

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Return the list of scene-node names representing this component's
        bones. These transforms will be reflected across the mirror plane
        onto the twin side using ``aniseed_toolkit.mirror.global_mirror``.
        """
        return [
            self.input("Joint").get()
        ]

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the name of the node the mirrored joint should be parented to
        """
        return mref.get(self.input("Joint").get()).parent().name()
