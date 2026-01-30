import os
import maya.cmds as mc

import aniseed
import aniseed_toolkit


class GlobalControlRoot(aniseed.RigComponent):

    identifier = "Core : Global Control Root"
    icon = os.path.join(
        os.path.dirname(__file__),
        "root.png",
    )

    def __init__(self, *args, **kwargs):
        super(GlobalControlRoot, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="Typically the root of the rig",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Joint To Drive",
            description="The joint which should be driven by this control",
            validate=True,
            group="Required Joints",
        )

        self.declare_option(
            name="Label",
            value="Global",
            group="Naming",
            description="The main control will take on this name",
        )

        self.declare_output(
            name="Main Control",
            description="The main control that the rest of the rig will move with"
        )

        self.declare_output(
            name="Location Control",
            description=(
                "A control which is a child of the main control. "
                "This control drives the joint"
            ),
        )


    def option_widget(self, option_name):
        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                default_item=self.option("Shape").get()
            )

    def input_widget(self, requirement_name):
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Joint To Drive":
            return aniseed.widgets.ObjectSelector(component=self)

    def run(self):

        parent = self.input("Parent").get()
        joint_to_drive = self.input("Joint To Drive").get()

        srt_control = aniseed_toolkit.run(
            "Create Control",
            description=self.option("Label").get(),
            location=self.config.middle,
            shape="core_srt",
            shape_scale=100,
            config=self.config,
            parent=parent,
            match_to=joint_to_drive,
        )

        root_control = aniseed_toolkit.run(
            "Create Control",
            description=self.option("Label").get() + "Root",
            location=self.config.middle,
            shape="core_arrow",
            shape_scale=10,
            config=self.config,
            parent=srt_control.ctl,
            match_to=joint_to_drive,
        )

        if joint_to_drive:
            mc.parentConstraint(
                root_control.ctl,
                joint_to_drive,
                maintainOffset=False,
            )

            mc.scaleConstraint(
                root_control.ctl,
                joint_to_drive,
                maintainOffset=False,
            )

        self.output("Main Control").set(srt_control.ctl)
        self.output("Location Control").set(root_control.ctl)

        return True
