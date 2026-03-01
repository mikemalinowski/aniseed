import os
import mref
from maya import cmds

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

        # -- This is a dynamic option which we only use to ask the user
        # -- if they want us to create a joint. After the component is added
        # -- to a stack it is never visible again
        self.declare_option(
            name="Create Joint",
            value=True,
            pre_expose=True,
        )
        self.declare_option(
            name="Has Initialised",
            value=False,
            hidden=True,
        )

    def on_enter_stack(self):
        """
        This is called when the component enters the stack. We will check if
        it is the first time its been added, and if it is we will create the
        joint automatically if we're allowed to do so.
        """
        super(GlobalControlRoot, self).on_enter_stack()

        # -- Get the option and check if we have already been initialised
        initialised_option = self.option("Has Initialised")
        joint_option = self.option("Create Joint")
        if initialised_option.get():
            return

        # -- Before doing anything else, lets mark our two
        # -- options as hidden
        initialised_option.set(True)
        joint_option.set_hidden(True)

        # -- This is being added to the stack by the user if we're reaching
        # -- here, so lets check if they want us to automatically add the joint
        if not joint_option.get():
            return

        # -- To reach here the user would like us to create the joint.
        parent = mref.selected()[0] if mref.selected() else None
        joint = mref.create("joint", parent=parent)
        joint.rename(
            self.config.generate_name(
                description="global_srt",
                classification=self.config.joint,
                location=self.config.middle,
            )
        )
        joint.set_parent(parent)

        # -- Finally set the input parameter
        self.input("Joint To Drive").set(joint.name())

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

        srt_control = aniseed_toolkit.control.create(
            description=self.option("Label").get(),
            location=self.config.middle,
            shape="core_srt",
            shape_scale=100,
            config=self.config,
            parent=parent,
            match_to=joint_to_drive,
        )

        root_control = aniseed_toolkit.control.create(
            description=self.option("Label").get() + "Root",
            location=self.config.middle,
            shape="core_arrow",
            shape_scale=10,
            config=self.config,
            parent=srt_control.ctl,
            match_to=joint_to_drive,
        )

        if joint_to_drive:
            cmds.parentConstraint(
                root_control.ctl,
                joint_to_drive,
                maintainOffset=False,
            )

            cmds.scaleConstraint(
                root_control.ctl,
                joint_to_drive,
                maintainOffset=False,
            )

        self.output("Main Control").set(srt_control.ctl)
        self.output("Location Control").set(root_control.ctl)

        return True
