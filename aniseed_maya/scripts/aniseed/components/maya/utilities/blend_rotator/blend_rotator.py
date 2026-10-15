"""
Provides the "Utility : Blend Rotator" component, which builds a cube
control whose offset is parent constrained between Target A and Target B,
with a keyable Blend attribute on the control driving the weighting. The
control then drives a joint, which can optionally be created on stack entry
under the current selection.
"""
import mref
import aniseed
import aniseed_toolkit


class BlendedConstraint(aniseed.RigComponent):
    """
    Creates a control that blends the rotation of a joint between two
    target nodes. A "Blend" attribute on the control (0.0 to 1.0) drives
    a pair of parent constraints between Target A and Target B, while the
    control itself drives the joint's transform.
    """

    identifier = "Utility : Blend Rotator"

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent, Joint, Target A and Target B inputs, the naming
        and Create Joint options, and the Control output.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            validate=True,
            group="Control Rig",
            description="The node under which the blend control will be parented.",
        )

        self.declare_input(
            name="Joint",
            value="",
            description="The joint that will be driven by the blend control. May be created automatically on stack entry if 'Create Joint' is enabled.",
        )

        self.declare_input(
            name="Target A",
            value="",
            description="The first blend target. When the Blend attribute is 0.0 the joint follows this target.",
        )

        self.declare_input(
            name="Target B",
            value="",
            description="The second blend target. When the Blend attribute is 1.0 the joint follows this target.",
        )

        self.declare_option(
            name="Description",
            value="",
            group="Naming",
            pre_expose=True,
            description="Descriptive token used when generating names for the control and joint.",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
            description="Location token (e.g. lf/md/rt) used when generating names.",
        )

        self.declare_option(
            name="Create Joint",
            value=True,
            group="Creation",
            pre_expose=True,
            description="If true, a joint is created and bound to the Joint input on stack entry; otherwise an existing joint is expected.",
        )

        self.declare_output(
            name="Control",
            description="The transform of the blend control that was created.",
        )

    def suggested_label(self):
        """
        Returns the Description option as the component label.
        """
        return self.option("Description").get()

    def on_enter_stack(self):
        """
        Hides the Create Joint option and, if it is enabled, creates a named
        joint under (and matched to) the first selected node, binding it to
        the Joint input. Relies on the current selection; with nothing
        selected the joint is created at the world root.
        """

        self.option("Create Joint").set_hidden(True)

        if not self.option("Create Joint").get():
            return

        description = self.option("Description").get()
        location = self.option("Location").get()

        selection = mref.selected()
        parent = selection[0] if selection else None

        joint = mref.create("joint", parent=parent)
        joint.rename(
            self.config.generate_name(
                classification=self.config.joint,
                description=description,
                location=location,
            ),
        )
        if parent:
            joint.match_to(parent)

        self.input("Joint").set(joint.name())

    def option_widget(self, option_name):
        """
        Returns a location selector for the Location option.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the Parent, Joint, Target A and
        Target B inputs.
        """
        if requirement_name in ["Parent", "Joint", "Target A", "Target B"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        """
        Builds a cube control matched to the joint, adds a keyable Blend
        attribute (default 0.5) to it, and parent constrains the control's
        offset to both targets with Blend driving the weights (no-flip
        interpolation). The control then parent and scale constrains the
        joint, and is written to the Control output.
        """

        joint = self.input("Joint").get()
        target_a = self.input("Target A").get()
        target_b = self.input("Target B").get()
        parent = self.input("Parent").get()
        description = self.option("Description").get()
        location = self.option("Location").get()

        rotator_control = aniseed_toolkit.rig.control.create(
            description=description,
            location=location,
            parent=parent,
            config=self.config,
            shape="core_cube",
            match_to=joint,
        )

        blend_attribute = mref.get(rotator_control.ctl).add_attribute(
            "Blend",
            value=0.5,
            attribute_type="float",
            keyable=True,
        )

        # -- Constrain the control's offset to both targets, with the
        # -- blend attribute driving the weighting between them
        mref.parentConstraint(
            target_a,
            rotator_control.off,
            maintainOffset=True,
        )

        constraint = mref.parentConstraint(
            target_b,
            rotator_control.off,
            maintainOffset=True,
        )[0]
        constraint.attr("interpType").set(0)  # No Flip

        aniseed_toolkit.scene.constraints.blend_weights(blend_attribute, constraint)

        # -- The control then drives the joint
        aniseed_toolkit.scene.constraints.parent_and_scale(
            rotator_control.ctl,
            joint,
            maintain_offset=True,
        )

        self.output("Control").set(rotator_control.ctl)
        return True
