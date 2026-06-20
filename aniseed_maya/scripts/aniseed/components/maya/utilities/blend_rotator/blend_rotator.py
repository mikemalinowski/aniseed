import mref
import aniseed
import aniseed_toolkit
from maya import cmds


class BlendedConstraint(aniseed.RigComponent):
    """
    Creates a control that blends the rotation of a joint between two
    target nodes. A "Blend" attribute on the control (0.0 to 1.0) drives
    a pair of parent constraints between Target A and Target B, while the
    control itself drives the joint's transform.
    """

    identifier = "Utility : Blend Rotator"

    def __init__(self, *args, **kwargs):
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
        return self.option("Description").get()

    def on_enter_stack(self):

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
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    def input_widget(self, requirement_name):
        if requirement_name in ["Parent", "Joint", "Target A", "Target B"]:
            return aniseed.widgets.ObjectSelector(component=self)


    def run(self) -> bool:

        joint = self.input("Joint").get()
        target_a = self.input("Target A").get()
        target_b = self.input("Target B").get()
        parent = self.input("Parent").get()
        description = self.option("Description").get()
        location = self.option("Location").get()

        rotator_control = aniseed_toolkit.control.create(
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

        cmds.parentConstraint(
            target_a,
            rotator_control.off,
            maintainOffset=True,
        )

        constraint = mref.get(
            cmds.parentConstraint(
                target_b,
                rotator_control.off,
                maintainOffset=True,
            )[0]
        )
        constraint.attr("interpType").set(0)  # No Flip

        weight_attributes = constraint.weight_attributes()

        reverse_node = mref.create("reverse")
        blend_attribute.connect(reverse_node.attr("inputX"))
        reverse_node.attr("outputX").connect(weight_attributes[0])
        blend_attribute.connect(weight_attributes[1])

        cmds.parentConstraint(
            rotator_control.ctl,
            joint,
            maintainOffset=True,
        )

        cmds.scaleConstraint(
            rotator_control.ctl,
            joint,
            maintainOffset=True,
        )

        self.output("Control").set(rotator_control.ctl)
        return True
