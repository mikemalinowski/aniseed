"""
Provides the "Basic : Singular (Jointless)" component, which creates a single
control placed at a guide without driving a joint.
"""
import aniseed
import aniseed_toolkit


class JointlessSingular(aniseed_toolkit.control_mixins.SingularControlMixin, aniseed.RigComponent):
    """
    A basic component which creates a single control placed at a guide,
    without driving a joint
    """

    identifier = "Basic : Singular (Jointless)"
    placement_input = "Guide"
    placement_label = "Guide"

    def __init__(self, *args, **kwargs):
        """
        Declares the singular control attributes with a "Guide" placement input
        and no joint creation option.
        """
        super().__init__(*args, **kwargs)

        self._declare_singular_attributes(
            placement_description="Name of the guide for placement",
            placement_group="Control Rig",
        )

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
        self._create_singular_controls(offset_visibility_toggle=False)
        return True
