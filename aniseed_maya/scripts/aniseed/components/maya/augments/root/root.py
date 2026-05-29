import os
import mref
from maya import cmds

import aniseed
import aniseed_toolkit


class GlobalControlRoot(aniseed.RigComponent):
    """
    Creates a two-tier "global control" root: an SRT control that
    carries the overall world transform of the rig, plus a Root
    control parented under it which constrains the actual driving
    joint.

    On first add to the stack (controlled by the one-shot
    ``Create Joint`` option), the component will also create the
    driving joint itself, using the user's current Maya selection as
    its parent if anything is selected. After the first add the
    ``Create Joint`` and ``Has Initialised`` options are hidden so
    they don't clutter the UI on subsequent edits.
    """

    identifier = "Core : Global Control Root"
    icon = os.path.join(
        os.path.dirname(__file__),
        "root.png",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
            description="The main control that the rest of the rig will move with",
            is_default=True,
        )

        self.declare_output(
            name="Location Control",
            description=(
                "A control which is a child of the main control. "
                "This control drives the joint"
            ),
        )

        # -- One-shot option asked at add-time only: should we auto-create
        # -- the driving joint? Hidden from the UI after the first
        # -- ``on_enter_stack`` runs.
        self.declare_option(
            name="Create Joint",
            description=(
                "If enabled when the component is first added to the "
                "stack, the driving joint is created automatically "
                "(parented to the current Maya selection). Hidden after "
                "first use."
            ),
            value=True,
            pre_expose=True,
        )

        # -- Internal flag tracking whether ``on_enter_stack`` has
        # -- already done its one-shot setup. Hidden because the user
        # -- should never need to touch it.
        self.declare_option(
            name="Has Initialised",
            description=(
                "Internal flag: True once the component's first-add "
                "joint-creation has run. Should not be edited by hand."
            ),
            value=False,
            hidden=True,
        )

    def on_enter_stack(self):
        """
        This is called when the component enters the stack. We will check if
        it is the first time its been added, and if it is we will create the
        joint automatically if we're allowed to do so.
        """
        super().on_enter_stack()

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
        selected = mref.selected()
        parent = selected[0] if selected else None
        joint = mref.create("joint", parent=parent)
        joint.rename(
            self.config.generate_name(
                description="global_srt",
                classification=self.config.joint,
                location=self.config.middle,
            )
        )

        # -- Finally set the input parameter
        self.input("Joint To Drive").set(joint.name())

    def input_widget(self, requirement_name):
        if requirement_name in ("Parent", "Joint To Drive"):
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
