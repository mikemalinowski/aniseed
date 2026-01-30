import os
import snappy
import typing
import aniseed
import qtility
import functools
import aniseed_toolkit
import maya.cmds as mc


# noinspection PyInterpreter
class ArmComponent(aniseed.RigComponent):

    identifier = "Limb : Arm"
    icon = os.path.join(
        os.path.dirname(__file__),
        "arm.png",
    )

    # noinspection PyUnresolvedReferences
    def __init__(self, *args, **kwargs):
        super(ArmComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Shoulder",
            description="The root of the spine",
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Hand",
            description="The tip of the spine",
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Upper Twist Joints",
            description="All upper twist joints",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_input(
            name="Lower Twist Joints",
            description="All lower twist joints",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_option(
            name="Description Prefix",
            value="arm",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="lf",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Align Shoulder To World",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Hand To World",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Upvector To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Apply Soft Ik",
            value=True,
            group="Behaviour",
        )

        self.declare_output(
            name="Blended Upper Arm",
        )

        self.declare_output(
            name="Blended Lower Arm",
        )

        self.declare_output(
            name="Blended Hand",
        )
        self.declare_output(
            name="Aligned Hand",
        )

        self.declare_output("Upvector")
        self.declare_output("Ik Hand")

        # -- Declare our build properties - this is only required because i have
        # -- chosen within this component to break up the long build script
        # -- into functions, and therefore we use this to access items created
        # -- from other functions.
        self.prefix: str = ""
        self.location: str = ""
        self.org: str = ""
        self.arm_joints: list[str] = []
        self.chain_direction: "Direction" = None
        self.shoulder_control: "Control" = None
        self.config_control: "Control" = None
        self.upvector_control: "Control" = None
        self.ik_hand_control: "Control" = None
        self.fk_upper_control: "Control" = None
        self.fk_lower_control: "Control" = None
        self.fk_hand_control: "Control" = None
        self.aligned_hand_node: str = ""

        self.controls: list[str] = []
        self.fk_controls: list[str] = []
        self.ik_controls: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [0, 180, 0]

    def option_widget(self, option_name: str):
        """
        This allows us to provide dedicate widgets for specific options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    def input_widget(self, requirement_name):
        """
        This allows us to provide dedicate widgets for specific inputs
        """

        object_list = [
            "Parent",
            "Shoulder",
            "Hand",
        ]

        if requirement_name in object_list:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.ObjectList()

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        These are functions that will be exposed to the user if they
        right click the component
        """
        if not self.input("Shoulder").get():
            return {
                "Create Joints": self.build_skeleton,
            }
        return dict()

    def is_valid(self):
        """
        This gives us the chance to validate the skeleton
        before we commit to building.
        """
        arm_joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Shoulder").get(),
            self.input("Hand").get(),
        )[1:]

        direction = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            arm_joints[0],
            arm_joints[-1],
        )

        if direction != direction.PositiveX and direction != direction.NegativeX:
            print("Validation Warning : Chain is not failing Up/Down X")
            print(f"    Tested Chain : {arm_joints}")
            print(direction)
            return False

        return True

    def create_controls(self):
        """
        Here we create all the controls for the arm
        """
        prefix = self.option('Description Prefix').get()
        location = self.option("Location").get()

        self.shoulder_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}Shoulder",
            location=location,
            parent=self.org,
            shape="core_cube",
            config=self.config,
            match_to=self.arm_joints[0],
            shape_scale=5.0,
            rotate_shape=None,
        )

        if self.option("Align Shoulder To World").get():
            mc.xform(
                self.shoulder_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Add the configuration control
        self.config_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}ArmConfig",
            location=location,
            parent=self.shoulder_control.ctl,
            shape="core_lollipop",
            config=self.config,
            match_to=self.arm_joints[0],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        mc.parentConstraint(
            self.shoulder_control.ctl,
            self.arm_joints[0],
            maintainOffset=True,
        )

        mc.scaleConstraint(
            self.shoulder_control.ctl,
            self.arm_joints[0],
            maintainOffset=True,
        )

        self.fk_upper_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.prefix}UpperArmFK",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_paddle",
            config=self.config,
            match_to=self.arm_joints[1],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        self.fk_lower_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.prefix}LowerArmFK",
            location=self.location,
            parent=self.fk_upper_control.ctl,
            shape="core_paddle",
            config=self.config,
            match_to=self.arm_joints[2],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        self.fk_hand_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.prefix}HandFK",
            location=self.location,
            parent=self.fk_lower_control.ctl,
            shape="core_paddle",
            config=self.config,
            match_to=self.arm_joints[3],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        # -- We'll iterate over our fk joints, so place them all in a list
        self.fk_controls = [
            self.fk_upper_control.ctl,
            self.fk_lower_control.ctl,
            self.fk_hand_control.ctl,
        ]

        # -- Now create the main IK control
        self.ik_hand_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.prefix}Hand",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_stumpy_cross",
            config=self.config,
            match_to=self.arm_joints[-1],
            shape_scale=20.0,
            rotate_shape=[-90, 0 ,0],
        )
        self.ik_controls.append(self.ik_hand_control.ctl)
        if self.option("Align Hand To World").get():
            mc.xform(
                self.ik_hand_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Create the upvector control for the arm
        self.upvector_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.prefix}ArmUpvector",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_sphere",
            config=self.config,
            match_to=self.arm_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )
        self.ik_controls.append(self.upvector_control.ctl)
        mc.xform(
            self.upvector_control.org,
            translation=aniseed_toolkit.run(
                "Calculate Upvector Position",
                point_a=self.arm_joints[1],
                point_b=self.arm_joints[2],
                point_c=self.arm_joints[3],
                length=1,
            ),
            worldSpace=True,
        )
        if self.option("Align Upvector To World").get():
            mc.xform(
                self.upvector_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

    def create_snap(self):
        group = "Arm_%s_%s" % (
            self.prefix,
            self.location,
        )

        snappy.new(
            node=self.ik_hand_control.ctl,
            target=self.nk_joints[2],
            group=group,
        )

        snappy.new(
            node=self.upvector_control.ctl,
            target=self.nk_joints[1],
            group=group,
        )

        snappy.new(
            node=self.fk_upper_control.ctl,
            target=self.nk_joints[0],
            group=group,
        )

        snappy.new(
            node=self.fk_lower_control.ctl,
            target=self.nk_joints[1],
            group=group,
        )

        snappy.new(
            node=self.fk_hand_control.ctl,
            target=self.nk_joints[2],
            group=group,
        )

    def create_twist_setup(self):

        upper_twist_joints = self.input("Upper Twist Joints").get()
        lower_twist_joints = self.input("Lower Twist Joints").get()
        print("nk :: %s" % self.nk_joints)
        if upper_twist_joints:
            twist_component = self.rig.component_library.request("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(upper_twist_joints)
            twist_component.input("Parent").set(self.shoulder_control.ctl)
            twist_component.input("Root").set(self.nk_joints[0])
            twist_component.input("Tip").set(self.nk_joints[1])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("UpperTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                aniseed_toolkit.run(
                    "Rotate Shapes",
                    twist,
                    *self.shape_rotation,
                )

        if lower_twist_joints:

            twist_component = self.rig.component_library.request("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(lower_twist_joints)
            twist_component.input("Parent").set(self.nk_joints[1])
            twist_component.input("Root").set(self.nk_joints[1])
            twist_component.input("Tip").set(self.nk_joints[2])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("LowerTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                aniseed_toolkit.run(
                    "Rotate Shapes",
                    twist,
                    *self.shape_rotation,
                )

    def set_outputs(self):

        self.output("Upvector").set(self.upvector_control.ctl)
        self.output("Ik Hand").set(self.ik_hand_control.ctl)
        self.output("Aligned Hand").set(self.aligned_hand_node)

        self.output("Blended Upper Arm").set(self.nk_joints[0])
        self.output("Blended Lower Arm").set(self.nk_joints[1])
        self.output("Blended Hand").set(self.nk_joints[2])


    def run(self):

        self.prefix = self.option('Description Prefix').get()
        self.location = self.option("Location").get()

        self.org = aniseed_toolkit.run(
            "Create Basic Transform",
            classification=self.config.organisational,
            description=f"{self.prefix}Arm",
            location=self.location,
            config=self.config,
            parent=self.input("Parent").get(),
            match_to=self.input("Parent").get()
        )
        self.arm_joints = aniseed_toolkit.run(
            "Get Joints Between",
            start=self.input('Shoulder').get(),
            end=self.input("Hand").get(),
        )
        self.create_controls()

        ikfk_setup = aniseed_toolkit.run(
            "Create Two Bone IKFK",
            parent=self.shoulder_control.ctl,
            root_joint=self.arm_joints[1],
            end_joint=self.arm_joints[-1],
            attribute_host=self.config_control.ctl,
            attribute_name="ikfk",
            constrain=True,
            soft_ik=self.option("Apply Soft Ik").get(),
        )
        for node in ikfk_setup.all_nodes:
            mc.rename(
                node,
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}Arm{node}",
                    location=self.location,
                ),
            )

        mc.parentConstraint(
            self.ik_hand_control.ctl,
            ikfk_setup.out_ik_target,
            maintainOffset=True,
        )
        mc.parentConstraint(
            self.upvector_control.ctl,
            ikfk_setup.out_ik_upvector,
            maintainOffset=False,
        )

        for idx, fk_marker in enumerate(ikfk_setup.out_fk_joints):
            mc.parentConstraint(
                self.fk_controls[idx],
                fk_marker,
                maintainOffset=True,
            )

        # -- Hook up the visibility attributes
        mc.addAttr(
            self.config_control.ctl,
            shortName="show_ik",
            at='float',
            min=0,
            max=1,
            dv=1,
            k=True,
        )
        mc.addAttr(
            self.config_control.ctl,
            shortName="show_fk",
            at='float',
            min=0,
            max=1,
            dv=0,
            k=True,
        )
        ik_visibility_attribute = f"{self.config_control.ctl}.show_ik"
        fk_visibility_attribute = f"{self.config_control.ctl}.show_fk"

        for ik_control in self.ik_controls:
            ik_control = aniseed_toolkit.run(
                "Get Control",
                ik_control,
            )
            mc.connectAttr(
                f"{self.config_control.ctl}.show_ik",
                f"{ik_control.off}.visibility",
                force=True,
            )

        for fk_control in self.fk_controls:
            fk_control = aniseed_toolkit.run(
                "Get Control",
                fk_control,
            )
            mc.connectAttr(
                f"{self.config_control.ctl}.show_fk",
                f"{fk_control.off}.visibility",
                force=True,
            )

        self.nk_joints = ikfk_setup.out_blend_joints
        self.create_snap()
        self.create_twist_setup()
        self.set_outputs()

    def build_skeleton(self, upper_twist_count=None, lower_twist_count=None):

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        if upper_twist_count is None:
            upper_twist_count = qtility.request.text(
                title="Upper Twist Count",
                message="How many twist joints do you want on the upper arm?"
            )
            upper_twist_count = int(upper_twist_count)

        if lower_twist_count is None:
            lower_twist_count = qtility.request.text(
                title="Upper Twist Count",
                message="How many twist joints do you want on the lower arm?"
            )
            lower_twist_count = int(lower_twist_count)

        joint_map = aniseed_toolkit.run(
            "Load Joints File",
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "arm.json",
            ),
            apply_names=False,
            worldspace_root=True,
        )

        location = self.option("Location").get()

        shoulder = mc.rename(
            joint_map["shoulder"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Shoulder",
                location=location
            ),
        )


        upper_arm = mc.rename(
            joint_map["upperarm"],
            self.config.generate_name(
                classification=self.config.joint,
                description="UpperArm",
                location=location
            ),
        )


        lower_arm = mc.rename(
            joint_map["lowerarm"],
            self.config.generate_name(
                classification=self.config.joint,
                description="LowerArm",
                location=location
            ),
        )

        hand = mc.rename(
            joint_map["hand"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Hand",
                location=location
            ),
        )

        all_joints = [shoulder, upper_arm, lower_arm, hand]

        self.input("Shoulder").set(shoulder)
        self.input("Hand").set(hand)

        if upper_twist_count:
            upper_twists = aniseed_toolkit.run(
                "Create Spread Joints",
                root_joint=upper_arm,
                tip_joint=lower_arm,
                joint_count=upper_twist_count,
                axis="X",
                naming_function=functools.partial(
                    self.config.generate_name,
                    classification=self.config.joint,
                    description=self.option("Description Prefix").get() + "UpperArmTwist",
                    location=self.option("Location").get(),
                )
            )
            self.input("Upper Twist Joints").set(upper_twists)

        if lower_twist_count:
            lower_twists = aniseed_toolkit.run(
                "Create Spread Joints",
                root_joint=lower_arm,
                tip_joint=hand,
                joint_count=upper_twist_count,
                axis="X",
                naming_function=functools.partial(
                    self.config.generate_name,
                    self.config.joint,
                    self.option("Description Prefix").get() + "UpperArmTwist",
                    self.option("Location").get(),
                )
            )

            self.input("Lower Twist Joints").set(lower_twists)

        if self.option("Location").get() == self.config.right:
            aniseed_toolkit.run(
                "Global Mirror",
                transforms=all_joints,
                across="YZ"
            )

