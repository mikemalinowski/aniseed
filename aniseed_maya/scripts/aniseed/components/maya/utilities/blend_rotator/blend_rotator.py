import mref
import aniseed
import aniseed_toolkit
from maya import cmds

from aniseed_toolkit.lib.joints import reverse_chain


class BlendedConstraint(aniseed.RigComponent):

    identifier = "Utility : Blend Rotator"

    def __init__(self, *args, **kwargs):
        super(BlendedConstraint, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Joint",
            value="",
        )

        self.declare_input(
            name="Target A",
            value="",
        )

        self.declare_input(
            name="Target B",
            value="",
        )

        self.declare_option(
            name="Description",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Create Joint",
            value=True,
            group="Creation",
            pre_expose=True,
        )

        self.declare_output("Control")

    def suggested_label(self):
        return self.option("Description").get()

    def on_enter_stack(self):

        self.option("Create Joint").set_hidden(True)

        if not self.option("Create Joint").get():
            return

        selection = mref.selected()
        parent = selection[0] if selection else None

        joint = mref.create("joint", parent=parent)
        joint.set_parent(parent)
        joint.rename(
            self.config.generate_name(
                classification=self.config.joint,
                description=self.option("Description").get(),
                location=self.option("Location").get(),
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

        rotator_control = aniseed_toolkit.control.create(
            description=self.option("Description").get(),
            location=self.option("Location").get(),
            parent=self.input("Parent").get(),
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

        mref.get(rotator_control.off)

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
