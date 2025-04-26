import os
import aniseed
import aniseed_toolkit
import maya.cmds as mc


class HeadComponent(aniseed.RigComponent):
    """
    This is a very simple component which includes a single neck bone/control and
    a head bone/control in a linear hierarchy.
    """

    identifier = "Standard : Head"
    icon = os.path.join(
        os.path.dirname(__file__),
        "head.png",
    )

    def __init__(self, *args, **kwargs):
        super(HeadComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Neck Joint",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Head Joint",
            value="",
            validate=True,
            group="Required Joints"
        )

        self.declare_option(
            name="Description Prefix",
            value="",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Align Head To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Neck To World",
            value=True,
            group="Behaviour",
        )

        self.declare_output(
            "Neck Control",
        )

        self.declare_output(
            "Head Control",
        )

        # -- Declare our properties we will use during our build process
        self.neck_control = None
        self.head_control = None

    def input_widget(self, requirement_name):
        if requirement_name in ["Parent", "Neck Joint", "Head Joint"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        if option_name in ["Location"]:
            return aniseed.widgets.everywhere.ItemSelector(
                items=[
                    self.config.left,
                    self.config.middle,
                    self.config.right,
                ],
                default_item=self.config.middle,
            )

    def user_functions(self):
        return {
            "Create Joints": self.build_skeleton,
        }

    def is_valid(self) -> bool:

        leg_root = self.input("Neck Joint").get()
        toe_tip = self.input("Head Joint").get()

        if not leg_root or not toe_tip:
            return False

        return True

    def run(self):
        self.create_controls()
        self.constrain_skeleton()
        self.store_outputs()

    def create_controls(self):

        neck_joint = self.input("Neck Joint").get()
        head_joint = self.input("Head Joint").get()

        prefix = self.option("Description Prefix").get()
        location = self.option("Location").get()

        # -- Create the main hip control
        self.neck_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}Neck",
            location=location,
            parent=self.input("Parent").get(),
            shape="core_circle",
            config=self.config,
            match_to=neck_joint,
            shape_scale=20.0,
        )

        if self.option("Align Neck To World").get():
            mc.xform(
                self.neck_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Create the main hip control
        self.head_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}Head",
            location=location,
            parent=self.neck_control.ctl,
            shape="core_lollipop",
            config=self.config,
            match_to=head_joint,
            shape_scale=30.0,
            rotate_shape=[90, 0, 0],
        )

        if self.option("Align Head To World").get():
            mc.xform(
                self.head_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

    def constrain_skeleton(self):

        neck_joint = self.input("Neck Joint").get()
        head_joint = self.input("Head Joint").get()

        mc.parentConstraint(
            self.neck_control.ctl,
            neck_joint,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            self.neck_control.ctl,
            neck_joint,
            maintainOffset=True,
        )

        mc.parentConstraint(
            self.head_control.ctl,
            head_joint,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            self.head_control.ctl,
            head_joint,
            maintainOffset=True,
        )

    def store_outputs(self):
        self.output("Neck Control").set(self.neck_control.ctl)
        self.output("Head Control").set(self.head_control.ctl)

    def build_skeleton(self):

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        joint_map = aniseed_toolkit.run(
            "Load Joints File",
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "head.json",
            ),
            apply_names=False,
        )

        location = self.option("Location").get()
        prefix = self.option("Description Prefix").get()

        neck = mc.rename(
            joint_map["JNT_Neck_01_MD"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{prefix}Neck",
                location=location
            ),
        )


        head = mc.rename(
            joint_map["JNT_Head_01_MD"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{prefix}Head",
                location=location
            ),
        )

        self.input("Neck Joint").set(neck)
        self.input("Head Joint").set(head)