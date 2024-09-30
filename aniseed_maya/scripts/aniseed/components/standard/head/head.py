import os
import bony
import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
class HeadComponent(aniseed.RigComponent):

    identifier = "Standard : Head"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(HeadComponent, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Parent",
            value="",
            validate=True,
            group="Control Rig",
        )

        self.declare_requirement(
            name="Neck Joint",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_requirement(
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

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name):
        if requirement_name in ["Parent", "Neck Joint", "Head Joint"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
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

    # ----------------------------------------------------------------------------------
    def user_functions(self):
        return {
            "Create Joints": self.build_skeleton,
        }

    # ----------------------------------------------------------------------------------
    def is_valid(self) -> bool:

        leg_root = self.requirement("Neck Joint").get()
        toe_tip = self.requirement("Head Joint").get()

        if not leg_root or not toe_tip:
            return False

        return True

    # ----------------------------------------------------------------------------------
    # noinspection DuplicatedCode
    def run(self):

        neck_joint = self.requirement("Neck Joint").get()
        head_joint = self.requirement("Head Joint").get()

        prefix = self.option("Description Prefix").get()
        location = self.option("Location").get()

        shape_rotation = [0, 0, 0]

        # -- Create the main hip control
        neck_control = aniseed.control.create(
            description=f"{prefix}Neck",
            location=location,
            parent=self.requirement("Parent").get(),
            shape="core_circle",
            config=self.config,
            match_to=neck_joint,
            shape_scale=20.0,
            rotate_shape=shape_rotation,
        )
        self.output("Neck Control").set(neck_control)

        if self.option("Align Neck To World").get():
            mc.xform(
                aniseed.control.get_classification(
                    neck_control,
                    "org",
                ),
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        mc.parentConstraint(
            neck_control,
            neck_joint,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            neck_control,
            neck_joint,
            maintainOffset=True,
        )

        # -- Create the main hip control
        head_control = aniseed.control.create(
            description=f"{prefix}Head",
            location=location,
            parent=neck_control,
            shape="core_lollipop",
            config=self.config,
            match_to=head_joint,
            shape_scale=30.0,
            rotate_shape=[90, 0, 0],
        )
        self.output("Head Control").set(head_control)

        if self.option("Align Head To World").get():
            mc.xform(
                aniseed.control.get_classification(
                    head_control,
                    "org",
                ),
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        mc.parentConstraint(
            head_control,
            head_joint,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            head_control,
            head_joint,
            maintainOffset=True,
        )

    # ----------------------------------------------------------------------------------
    def build_skeleton(self):

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        joint_map = bony.writer.load_joints_from_file(
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "head_joints.json",
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

        self.requirement("Neck Joint").set(neck)
        self.requirement("Head Joint").set(head)