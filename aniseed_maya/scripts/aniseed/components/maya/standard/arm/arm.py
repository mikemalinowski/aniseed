import os
import snappy
import typing
import aniseed
import qtility
import collections
import aniseed_toolkit
import maya.cmds as mc


# noinspection PyInterpreter
class ArmComponent(aniseed.RigComponent):

    identifier = "Standard : Arm"
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
            value="",
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
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Hand To World",
            value=True,
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

        self.declare_option(
            name="Guide Org",
            value="",
            hidden=True,
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
        return {
            "Create Joints": self.build_skeleton,
            "Create Guide": self.create_guide,
            "Remove Guide": self.delete_guide,
            "Align Ik Orients": self.align_guide_ik,
        }

    def is_valid(self):
        """
        This gives us the chance to validate the skeleton
        before we commit to building.
        """
        if self.get_guide():
            print("You must remove the guide before building")
            return False

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
            parent=self.input("Parent").get(),
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

    def create_ik_setup(self):

        # -- Now create the Ik joints
        replicated_joints = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.arm_joints[1],
            to_this=self.arm_joints[-1],
            parent=self.shoulder_control.ctl,
        )

        # -- Rename the ik joints
        for joint in replicated_joints:
            joint = mc.rename(
                joint,
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}ArmIK",
                    location=self.location,
                )
            )
            self.ik_joints.append(joint)

        # -- Ensure all the rotation values are on the joint
        # -- orients to allow for correct assignment of the
        # -- ik vector
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            self.ik_joints,
        )

        # -- Create the Ik setup
        handle, effector = mc.ikHandle(
            startJoint=self.ik_joints[0],
            endEffector=self.ik_joints[-1],
            solver='ikRPsolver',
            priority=1,
        )

        # -- Hide the ik handle as we dont want the animator
        # -- to interact with it directly
        mc.setAttr(
            f"{handle}.visibility",
            0,
        )

        # -- Create the upvector control for the arm
        self.upvector_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.prefix}ArmUpvector",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_sphere",
            config=self.config,
            match_to=self.ik_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )

        mc.xform(
            self.upvector_control.org,
            translation=aniseed_toolkit.run(
                "Calculate Upvector Position",
                point_a=self.ik_joints[0],
                point_b=self.ik_joints[1],
                point_c=self.ik_joints[2],
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

        # -- Apply the upvector constraint
        mc.poleVectorConstraint(
            self.upvector_control.ctl,
            handle,
            weight=1,
        )

        # -- Now create the main IK control
        self.ik_hand_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.prefix}Hand",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_stumpy_cross",
            config=self.config,
            match_to=self.ik_joints[-1],
            shape_scale=20.0,
            rotate_shape=[-90, 0 ,0],
        )

        # -- Parent the ikhandle under the ik control so it
        # -- moves along with it
        mc.parent(
            handle,
            self.ik_hand_control.ctl,
        )

        if self.option("Align Hand To World").get():
            mc.xform(
                self.ik_hand_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        if self.option("Apply Soft Ik").get():

            root_node = mc.createNode("transform")

            mc.parent(
                root_node,
                self.shoulder_control.ctl,
            )

            mc.xform(
                root_node,
                matrix=mc.xform(
                    self.ik_joints[0],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            aniseed_toolkit.run(
                "Create Soft Ik",
                root=root_node,
                target=self.ik_hand_control.ctl,
                second_joint=self.ik_joints[-2],
                third_joint=self.ik_joints[-1],
                host=self.ik_hand_control.ctl,
            )

        # -- We need to constrain the end joint in rotation to the
        # -- hand control, because the ik does not do that.
        mc.parentConstraint(
            self.ik_hand_control.ctl,
            self.ik_joints[-1],
            skipTranslate=['x', 'y', 'z'],
        )

        self.aligned_hand_node = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="loc",
            description="hand",
            location=self.location,
            config=self.config,
            parent=self.ik_joints[2],
            match_to=self.ik_hand_control.ctl,
        )

    def create_nk_setup(self):

        # -- Now create an NK joint hierarchy, which we will use to bind
        # -- between the IK and the FK
        replicated_joints = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.arm_joints[1],
            to_this=self.arm_joints[-1],
            parent=self.shoulder_control.ctl,
        )

        # -- Rename the nk joints
        for nk_joint in replicated_joints:
            nk_joint = mc.rename(
                nk_joint,
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}ArmNK",
                    location=self.location,
                )
            )
            self.nk_joints.append(nk_joint)

        # -- Parent the hand control to the nk joint
        mc.parent(
            self.aligned_hand_node,
            self.nk_joints[-1],
        )

        # -- Build up a list of parameters we want to expose to all aniseed.control.
        # -- Initially the values are the default values but once the attribute
        # -- is generated the value will become the attribute itself.
        proxies = collections.OrderedDict()
        proxies['ik_fk'] = 0
        proxies['show_ik'] = 1
        proxies['show_fk'] = 0

        # -- Add a separator
        aniseed_toolkit.run(
            "Add Separator Attribute",
            self.shoulder_control.ctl,
        )

        for label in proxies:
            mc.addAttr(
                self.config_control.ctl,
                shortName=label,
                at='float',
                min=0,
                max=1,
                dv=proxies[label],
                k=True,
            )
            proxies[label] = label # config_control.attr(label)

        # -- Hook up the vis options for the ik controls
        mc.connectAttr(
            f"{self.config_control.ctl}.{proxies['show_ik']}",
            f"{self.ik_hand_control.off}.visibility",
        )

        mc.connectAttr(
            f"{self.config_control.ctl}.{proxies['show_ik']}",
            f"{self.upvector_control.off}.visibility",
        )

        # -- We need to constrain our nk between the ik and the fk
        for ik_node, fk_node, nk_node, skl_node in zip(self.ik_joints, self.fk_controls, self.nk_joints, self.arm_joints[1:]):

            # -- Create the constraint between the nk and the ik
            mc.parentConstraint(
                ik_node,
                nk_node,
                maintainOffset=True,
            )

            cns = mc.parentConstraint(
                fk_node,
                nk_node,
                maintainOffset=True,
            )[0]

            # -- Hook up the blends to drive the weights
            ik_driven = mc.parentConstraint(cns, query=True, weightAliasList=True)[0]
            fk_driven = mc.parentConstraint(cns, query=True, weightAliasList=True)[1]

            # -- Setting the IK FK blend constraint to shortest
            mc.setAttr(
                f"{cns}.interpType",
                2,  # -- Shortest
            )

            reverse_node = mc.createNode("reverse")

            mc.connectAttr(
                f"{self.config_control.ctl}.{proxies['ik_fk']}",
                f"{reverse_node}.inputX",
            )

            mc.connectAttr(
                f"{reverse_node}.outputX",
                f"{cns}.{ik_driven}",
            )

            mc.connectAttr(
                f"{self.config_control.ctl}.{proxies['ik_fk']}",
                f"{cns}.{fk_driven}",
            )

            fk_offset = aniseed_toolkit.run("Get Control", fk_node).off

            mc.connectAttr(
                f"{self.config_control.ctl}.{proxies['show_fk']}",
                f"{fk_offset}.visibility",
            )

            mc.parentConstraint(
                nk_node,
                skl_node,
                maintainOffset=True,
            )

            mc.scaleConstraint(
                nk_node,
                skl_node,
                maintainOffset=True,
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

        self.arm_joints = aniseed_toolkit.run(
            "Get Joints Between",
            start=self.input('Shoulder').get(),
            end=self.input("Hand").get(),
        )

        self.chain_direction = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            start=self.arm_joints[1],
            end=self.arm_joints[-1],
        )

        if self.chain_direction == self.chain_direction.NegativeX:
            self.shape_rotation = [0, 0, 0]

        self.create_controls()
        self.create_ik_setup()
        self.create_nk_setup()
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
            "Load Joint File",
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "arm.json",
            ),
            apply_names=False,

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
            parent = upper_arm

            upper_increment = mc.getAttr(
                f"{lower_arm}.translateX",
            ) / (upper_twist_count - 1)

            upper_twist_joints = list()

            for idx in range(upper_twist_count):
                twist_joint = aniseed_toolkit.run(
                    "Create Joint",
                    description=self.option("Description Prefix").get() + "UpperArmTwist",
                    location=self.option("Location").get(),
                    parent=parent,
                    match_to=parent,
                    config=self.config
                )
                upper_twist_joints.append(twist_joint)

                mc.setAttr(
                    f"{twist_joint}.translateX",
                    upper_increment * idx
                )

                all_joints.append(twist_joint)

            self.input("Upper Twist Joints").set(upper_twist_joints)

        if lower_twist_count:
            parent = lower_arm

            lower_increment = mc.getAttr(
                f"{hand}.translateX",
            ) / (lower_twist_count - 1)

            lower_twist_joints = list()

            for idx in range(lower_twist_count):
                twist_joint = aniseed_toolkit.run(
                    "Create Joint",
                    description=self.option("Description Prefix").get() + "LowerArmTwist",
                    location=self.option("Location").get(),
                    parent=parent,
                    match_to=parent,
                    config=self.config
                )
                lower_twist_joints.append(twist_joint)

                mc.setAttr(
                    f"{twist_joint}.translateX",
                    lower_increment * idx
                )
                all_joints.append(twist_joint)

            self.input("Lower Twist Joints").set(lower_twist_joints)

        if self.option("Location").get() == self.config.right:
            aniseed_toolkit.run(
                "Global Mirror",
                transforms=all_joints,
                across="YZ"
            )

        self.create_guide()

    def create_guide(self):


        shoulder = self.input("Shoulder").get()
        hand = self.input("Hand").get()

        guide_org = mc.createNode("transform")

        mc.addAttr(
            guide_org,
            shortName="guideRig",
            at="message",
        )

        mc.connectAttr(
            f"{shoulder}.message",
            f"{guide_org}.guideRig",
        )

        all_joints = aniseed_toolkit.run(
            "Get Joints Between",
            shoulder,
            hand,
        )

        all_controls = list()

        for joint in all_joints:
            guide_control = aniseed_toolkit.run(
                "Create Guide",
                joint,
                parent=guide_org,
            )

            all_controls.append(guide_control)

        for idx in range(len(all_joints)):

            # -- Skip the shoulder
            if not idx:
                continue

            if idx == len(all_joints) - 1:
                continue

            joint = all_joints[idx]
            control = all_controls[idx]
            next_control = all_controls[idx + 1]

            for child in mc.listRelatives(joint, children=True, type="joint") or list():

                if child in all_joints:
                    continue

                aniseed_toolkit.run(
                    "Create Guide Tween",
                    child,
                    from_this=control,
                    to_this=next_control,
                    parent=control,
                )

        self.option("Guide Org").set(guide_org)

    def get_guide(self):

        guide_node = self.option("Guide Org").get()

        if mc.objExists(guide_node):
            return guide_node

        return None

    def delete_guide(self):

        guide_root = self.get_guide()

        if not guide_root:
            return

        transforms = dict()

        all_chain = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Shoulder").get(),
            self.input("Hand").get(),
        )

        for joint in all_chain:
            transforms[joint] = mc.xform(
                joint,
                query=True,
                matrix=True,
            )

            for child in mc.listRelatives(joint, children=True, type="joint") or list():
                transforms[child] = mc.xform(
                    child,
                    query=True,
                    matrix=True,
                )

        connections = mc.listConnections(
            f"{all_chain[0]}.message",
            destination=True,
            plugs=True,
        )

        for connection in connections:
            if "guideRig" in connection:
                mc.delete(connection.split(".")[0])

        for joint, matrix in transforms.items():
            mc.xform(
                joint,
                matrix=matrix,
            )

    def align_guide_ik(self):

        guide_root = self.get_guide()

        all_chain = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Shoulder").get(),
            self.input("Hand").get(),
        )

        if guide_root:
            self.delete_guide()

            mc.select(
                [
                    all_chain[1],
                    all_chain[-1],
                ]
            )
            aniseed_toolkit.run("Align Bones For Ik")

            self.create_guide()

        else:
            mc.select(
                [
                    all_chain[1],
                    all_chain[-1],
                ]
            )
            aniseed_toolkit.run("Align Bones For Ik")
