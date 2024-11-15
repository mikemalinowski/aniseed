import os
import qute
import bony
import typing
import shapeshift
import collections
import aniseed

import maya.cmds as mc


# --------------------------------------------------------------------------------------
class ArmComponent(aniseed.RigComponent):

    identifier = "Standard : Arm"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    # ----------------------------------------------------------------------------------
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

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name):

        object_list = [
            "Parent",
            "Shoulder",
            "Hand",
        ]

        if requirement_name in object_list:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Joints": self.build_skeleton,
            "Create Guide": self.create_guide,
            "Remove Guide": self.delete_guide,
            "Align Ik Orients": self.align_guide_ik,
        }

    # ----------------------------------------------------------------------------------
    def is_valid(self):

        if self.get_guide():
            print("You must remove the guide before building")
            return False

        arm_joints = bony.hierarchy.get_between(
            self.input("Shoulder").get(),
            self.input("Hand").get(),
        )[1:]

        facing_direction = bony.direction.get_chain_facing_direction(
            arm_joints[0],
            arm_joints[-1],
        )

        facing = bony.direction.Facing

        if facing_direction != facing.PositiveX and facing_direction != facing.NegativeX:
            print("Validation Warning : Chain is not failing Up/Down X")
            print(f"    Tested Chain : {arm_joints}")
            print(facing_direction)
            return False

        return True

    # ----------------------------------------------------------------------------------
    def run(self):

        # -- Setup default options
        options = dict(
            lock_list='sx;sy;sz',
            hide_list='v;sx;sy;sz',
        )

        # -- Our shoulder control is always FK, so lets build a simple
        # -- fk control for that
        shoulder_joint = self.input('Shoulder').get()
        hand_joint = self.input("Hand").get()
        arm_joints = bony.hierarchy.get_between(
            shoulder_joint,
            hand_joint,
        )

        shape_y_flip = [0, 180, 0]

        facing_dir = bony.direction.get_chain_facing_direction(
            arm_joints[1],
            arm_joints[-1],
        )

        if facing_dir == bony.direction.Facing.NegativeX:
            shape_y_flip = [0, 0, 0]

        prefix = self.option('Description Prefix').get()
        location = self.option("Location").get()

        shoulder_control = aniseed.control.create(
            description=f"{prefix}Shoulder",
            location=location,
            parent=self.input("Parent").get(),
            shape="core_cube",
            config=self.config,
            match_to=shoulder_joint,
            shape_scale=5.0,
            rotate_shape=None,
        )

        if self.option("Align Shoulder To World").get():
            shoulder_org = aniseed.control.get_classification(
                shoulder_control,
                "org",
            )
            mc.xform(
                shoulder_org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        mc.parentConstraint(
            shoulder_control,
            shoulder_joint,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            shoulder_control,
            shoulder_joint,
            maintainOffset=True,
        )

        # -- Add the configuration control
        config_control = aniseed.control.create(
            description=f"{prefix}ArmConfig",
            location=location,
            parent=shoulder_control,
            shape="core_lollipop",
            config=self.config,
            match_to=shoulder_joint,
            shape_scale=20.0,
            rotate_shape=shape_y_flip,
        )

        # -- Now create an NK joint hierarchy, which we will use to bind
        # -- between the IK and the FK
        nk_joints = list()
        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=arm_joints[1],
            to_this=arm_joints[-1],
            parent=shoulder_control,
        )

        # -- Rename the nk joints
        for nk_joint in replicated_joints:
            nk_joint = mc.rename(
                nk_joint,
                self.config.generate_name(
                    classification="mech",
                description=f"{prefix}ArmNK",
                    location=location,
                )
            )
            nk_joints.append(nk_joint)

        self.output("Blended Upper Arm").set(nk_joints[0])
        self.output("Blended Lower Arm").set(nk_joints[1])
        self.output("Blended Hand").set(nk_joints[2])


        # ----------------------------------------------------------------------
        # -- IK SETUP

        # -- Now create the Ik joints
        ik_joints = list()
        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=arm_joints[1],
            to_this=arm_joints[-1],
            parent=shoulder_control,
        )

        # -- Rename the ik joints
        for ik_joint in replicated_joints:
            ik_joint = mc.rename(
                ik_joint,
                self.config.generate_name(
                    classification="mech",
                description=f"{prefix}ArmIK",
                    location=location,
                )
            )
            ik_joints.append(ik_joint)

            # -- Ensure all the rotation values are on the joint
            # -- orients to allow for correct assignment of the
            # -- ik vector
            bony.orients.move_rotations_to_joint_orients(ik_joint)

        # -- Create the Ik setup
        handle, effector = mc.ikHandle(
            startJoint=ik_joints[0],
            endEffector=ik_joints[-1],
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

        upvector = aniseed.control.create(
            description=f"{prefix}ArmUpvector",
            location=location,
            parent=shoulder_control,
            shape="core_sphere",
            config=self.config,
            match_to=ik_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )

        self.output("Upvector").set(upvector)

        upvector_org = aniseed.control.get_classification(
            upvector,
            "org",
        )

        mc.xform(
            upvector_org,
            translation=aniseed.utils.math.calculate_upvector_position(
                length=1,
                *ik_joints
            ),
            worldSpace=True,
        )

        if self.option("Align Upvector To World").get():
            mc.xform(
                upvector_org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Apply the upvector constraint
        mc.poleVectorConstraint(
            upvector,
            handle,
            weight=1,
        )

        # -- Now create the main IK control
        ik_hand = aniseed.control.create(
            description=f"{prefix}Hand",
            location=location,
            parent=shoulder_control,
            shape="core_stumpy_cross",
            config=self.config,
            match_to=ik_joints[-1],
            shape_scale=20.0,
            rotate_shape=[-90, 0 ,0],
        )

        self.output("Ik Hand").set(ik_hand)

        # -- Parent the ikhandle under the ik control so it
        # -- moves along with it
        mc.parent(
            handle,
            ik_hand,
        )

        if self.option("Align Hand To World").get():
            hand_org = aniseed.control.get_classification(
                ik_hand,
                "org",
            )

            mc.xform(
                hand_org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        if self.option("Apply Soft Ik").get():

            n = mc.createNode("transform")

            mc.parent(
                n,
                shoulder_control,
            )

            mc.xform(
                n,
                matrix=mc.xform(
                    ik_joints[0],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            aniseed.utils.mech.soft_ik.create(
                n,
                ik_hand,
                ik_joints[-2],
                ik_joints[-1],
                host=ik_hand,
            )

        # -- We need to constrain the end joint in rotation to the
        # -- hand control, because the ik does not do that.
        mc.parentConstraint(
            ik_hand,
            ik_joints[-1],
            skipTranslate=['x', 'y', 'z'],
        )

        aligned_hand = aniseed.control.basic_transform(
            classification="loc",
            description="hand",
            location=location,
            config=self.config,
            parent=nk_joints[2],
            match_to=ik_hand,
        )
        self.output("Aligned Hand").set(aligned_hand)

        # ----------------------------------------------------------------------
        # -- FK Setup
        upper_arm_fk = aniseed.control.create(
            description=f"{prefix}UpperArmFK",
            location=location,
            parent=shoulder_control,
            shape="core_paddle",
            config=self.config,
            match_to=nk_joints[0],
            shape_scale=20.0,
            rotate_shape=shape_y_flip,
        )

        lower_arm_fk = aniseed.control.create(
            description=f"{prefix}LowerArmFK",
            location=location,
            parent=upper_arm_fk,
            shape="core_paddle",
            config=self.config,
            match_to=nk_joints[1],
            shape_scale=20.0,
            rotate_shape=shape_y_flip,
        )

        hand_fk = aniseed.control.create(
            description=f"{prefix}HandFK",
            location=location,
            parent=lower_arm_fk,
            shape="core_paddle",
            config=self.config,
            match_to=nk_joints[2],
            shape_scale=20.0,
            rotate_shape=shape_y_flip,
        )

        # -- We'll iterate over our fk joints, so place them all in a list
        fk_transforms = [
            upper_arm_fk,
            lower_arm_fk,
            hand_fk,
        ]

        # ----------------------------------------------------------------------
        # -- NK Setup
        # -- Expose the IK FK attribute

        # -- Build up a list of parameters we want to expose to all aniseed.control.
        # -- Initially the values are the default values but once the attribute
        # -- is generated the value will become the attribute itself.
        proxies = collections.OrderedDict()
        proxies['ik_fk'] = 0
        proxies['show_ik'] = 1
        proxies['show_fk'] = 0

        # -- Add a separator
        aniseed.utils.attribute.add_separator_attr(shoulder_control)

        for label in proxies:
            mc.addAttr(
                config_control,
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
            f"{config_control}.{proxies['show_ik']}",
            f"{aniseed.control.get_classification(ik_hand, 'off')}.visibility",
        )

        mc.connectAttr(
            f"{config_control}.{proxies['show_ik']}",
            f"{aniseed.control.get_classification(upvector, 'off')}.visibility",
        )

        # -- We need to constrain our nk between the ik and the fk
        for ik_node, fk_node, nk_node, skl_node in zip(ik_joints, fk_transforms, nk_joints, arm_joints[1:]):

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
                f"{config_control}.{proxies['ik_fk']}",
                f"{reverse_node}.inputX",
            )

            mc.connectAttr(
                f"{reverse_node}.outputX",
                f"{cns}.{ik_driven}",
            )

            mc.connectAttr(
                f"{config_control}.{proxies['ik_fk']}",
                f"{cns}.{fk_driven}",
            )

            fk_offset = aniseed.control.get_classification(
                fk_node,
                "off",
            )

            mc.connectAttr(
                f"{config_control}.{proxies['show_fk']}",
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

        upper_twist_joints = self.input("Upper Twist Joints").get()
        lower_twist_joints = self.input("Lower Twist Joints").get()

        if upper_twist_joints:
            twist_component = self.rig.component_library.get("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(upper_twist_joints)
            twist_component.input("Parent").set(shoulder_control) # aniseed.control.get_classification(shoulder_control, "org"))
            twist_component.input("Root").set(nk_joints[0])
            twist_component.input("Tip").set(nk_joints[1])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("UpperTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                shapeshift.rotate_shape(twist, *shape_y_flip)

        if lower_twist_joints:

            twist_component = self.rig.component_library.get("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(lower_twist_joints)
            twist_component.input("Parent").set(nk_joints[1])
            twist_component.input("Root").set(nk_joints[1])
            twist_component.input("Tip").set(nk_joints[2])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("LowerTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                shapeshift.rotate_shape(twist, *shape_y_flip)

    # ----------------------------------------------------------------------------------
    def build_skeleton(self, upper_twist_count=None, lower_twist_count=None):

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        if upper_twist_count is None:
            upper_twist_count = qute.utilities.request.text(
                title="Upper Twist Count",
                label="How many twist joints do you want on the upper arm?"
            )
            upper_twist_count = int(upper_twist_count)

        if lower_twist_count is None:
            lower_twist_count = qute.utilities.request.text(
                title="Upper Twist Count",
                label="How many twist joints do you want on the lower arm?"
            )
            lower_twist_count = int(lower_twist_count)

        joint_map = bony.writer.load_joints_from_file(
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "arm2.json",
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
                twist_joint = aniseed.joint.create(
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
                twist_joint = aniseed.joint.create(
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
            bony.flip.global_mirror(
                transforms=all_joints,
                across="YZ"
            )

        self.create_guide()

    # ----------------------------------------------------------------------------------
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

        all_joints = bony.hierarchy.get_between(
            shoulder,
            hand,
        )

        arm_joints = all_joints[1:]


        all_controls = list()

        for joint in all_joints:
            guide_control = aniseed.utils.guide.create(
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

                aniseed.utils.guide.tween(
                    child,
                    from_this=control,
                    to_this=next_control,
                    parent=control,
                )

    # ----------------------------------------------------------------------------------
    def get_guide(self):

        connections = mc.listConnections(
            f"{self.input('Shoulder').get()}.message",
            destination=True,
            plugs=True,
        )

        for connection in connections or list():
            if "guideRig" in connection:
                return connection.split(".")[0]

    # ----------------------------------------------------------------------------------
    def delete_guide(self):

        guide_root = self.get_guide()

        if not guide_root:
            return

        transforms = dict()

        all_chain = bony.hierarchy.get_between(
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

    # ----------------------------------------------------------------------------------
    def align_guide_ik(self):

        guide_root = self.get_guide()

        all_chain = bony.hierarchy.get_between(
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
            bony.ik.clean_ik_plane_with_ui()

            self.create_guide()

        else:
            mc.select(
                [
                    all_chain[1],
                    all_chain[-1],
                ]
            )
            bony.ik.clean_ik_plane_with_ui()
