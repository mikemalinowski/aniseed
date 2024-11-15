import os
import bony
import typing
import collections
import maya.cmds as mc

import aniseed


# --------------------------------------------------------------------------------------
class SimpleIKComponent(aniseed.RigComponent):

    identifier = "Mechanics : Two Bone IK"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(SimpleIKComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Root Joint",
            description="The root of the chain",
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Tip Joint",
            description="The tip of the chain",
            validate=True,
            group="Required Joints"
        )

        self.declare_option(
            name="Name",
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
            name="Align Controls To World",
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
            value=False,
            group="Behaviour",

        )
        self.declare_output(
            name="Blended Upper",
        )

        self.declare_output(
            name="Blended Lower",
        )

        self.declare_output(
            name="Blended Tip",
        )

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name):

        object_fields = [
            "Parent",
            "Root Joint",
            "Tip Joint",
        ]
        if requirement_name in object_fields:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "Parent":
            return aniseed.widgets.everywhere.ObjectSelector(component=self)


    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Joints": self.build_skeleton,
        }

    # ----------------------------------------------------------------------------------
    def is_valid(self):

        arm_joints = bony.hierarchy.get_between(
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
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
        parent = self.input("Parent").get()
        root_joint = self.input('Root Joint').get()
        tip_joint = self.input("Tip Joint").get()

        name = self.option('Name').get()
        location = self.option("Location").get()

        # -- Create a node to place everything under
        component_org = mc.rename(
            mc.createNode("transform"),
            self.config.generate_name(
                classification=self.config.organisational,
                description=name + "Component",
                location=location,
            ),
        )

        mc.parent(
            component_org,
            parent,
        )

        skeletal_joints = bony.hierarchy.get_between(
            root_joint,
            tip_joint,
        )

        shape_y_flip = [0, 180, 0]

        facing_dir = bony.direction.get_chain_facing_direction(
            skeletal_joints[1],
            skeletal_joints[-1],
        )

        if facing_dir == bony.direction.Facing.NegativeX:
            shape_y_flip = [0, 0, 0]


        # -- Add the configuration control
        config_control = aniseed.control.create(
            description=f"{name}Config",
            location=location,
            parent=component_org,
            shape="core_lollipop",
            config=self.config,
            match_to=skeletal_joints[0],
            shape_scale=20.0,
            rotate_shape=shape_y_flip,
        )

        # -- Now create an NK joint hierarchy, which we will use to bind
        # -- between the IK and the FK
        nk_joints = list()

        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=skeletal_joints[0],
            to_this=skeletal_joints[-1],
            parent=component_org,
        )

        # -- Rename the nk joints
        for nk_joint in replicated_joints:
            nk_joint = mc.rename(
                nk_joint,
                self.config.generate_name(
                    classification="mech",
                    description=f"{name}NK",
                    location=location,
                )
            )
            nk_joints.append(nk_joint)

        self.output("Blended Upper").set(nk_joints[0])
        self.output("Blended Lower").set(nk_joints[1])
        self.output("Blended Tip").set(nk_joints[2])

        # ----------------------------------------------------------------------
        # -- IK SETUP

        # -- Now create the Ik joints
        ik_joints = list()

        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=skeletal_joints[0],
            to_this=skeletal_joints[-1],
            parent=component_org,
        )

        # -- Rename the ik joints
        for ik_joint in replicated_joints:
            ik_joint = mc.rename(
                ik_joint,
                self.config.generate_name(
                    classification="mech",
                description=f"{name}IK",
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
            description=f"{name}Upvector",
            location=location,
            parent=component_org,
            shape="core_sphere",
            config=self.config,
            match_to=ik_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )

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
        ik_control = aniseed.control.create(
            description=f"{name}IK",
            location=location,
            parent=component_org,
            shape="core_sphere",
            config=self.config,
            match_to=ik_joints[-1],
            shape_scale=10.0,
            rotate_shape=None,
        )

        # -- Parent the ikhandle under the ik control so it
        # -- moves along with it
        mc.parent(
            handle,
            ik_control,
        )

        if self.option("Align Controls To World").get():
            hand_org = aniseed.control.get_classification(
                ik_control,
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
                component_org,
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
                ik_control,
                ik_joints[-2],
                ik_joints[-1],
                host=ik_control,
            )

        # -- We need to constrain the end joint in rotation to the
        # -- hand control, because the ik does not do that.
        mc.parentConstraint(
            ik_control,
            ik_joints[-1],
            skipTranslate=['x', 'y', 'z'],
        )

        # ----------------------------------------------------------------------
        # -- FK Setup
        upper_fk = aniseed.control.create(
            description=f"{name}UpperFK",
            location=location,
            parent=component_org,
            shape="core_paddle",
            config=self.config,
            match_to=nk_joints[0],
            shape_scale=10.0,
            rotate_shape=shape_y_flip,
        )

        lower_fk = aniseed.control.create(
            description=f"{name}LowerFK",
            location=location,
            parent=upper_fk,
            shape="core_paddle",
            config=self.config,
            match_to=nk_joints[1],
            shape_scale=10.0,
            rotate_shape=shape_y_flip,
        )

        tip_fk = aniseed.control.create(
            description=f"{name}TipFK",
            location=location,
            parent=lower_fk,
            shape="core_paddle",
            config=self.config,
            match_to=nk_joints[2],
            shape_scale=10.0,
            rotate_shape=shape_y_flip,
        )

        # -- We'll iterate over our fk joints, so place them all in a list
        fk_transforms = [
            upper_fk,
            lower_fk,
            tip_fk,
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
        aniseed.utils.attribute.add_separator_attr(config_control)

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
            f"{ik_control}.visibility",
        )

        mc.connectAttr(
            f"{config_control}.{proxies['show_ik']}",
            f"{upvector}.visibility",
        )

        # -- We need to constrain our nk between the ik and the fk
        for ik_node, fk_node, nk_node, skl_node in zip(ik_joints, fk_transforms, nk_joints, skeletal_joints):

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

            mc.connectAttr(
                f"{config_control}.{proxies['show_fk']}",
                f"{fk_node}.visibility",
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

    # ----------------------------------------------------------------------------------
    def build_skeleton(self):

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        if parent and not mc.nodeType(parent) == "joint":
            print("You must select a joint")
            return None

        joint_map = bony.writer.load_joints_from_file(
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "joints.json",
            ),
            apply_names=False,

        )

        name = self.option("Name").get()
        location = self.option("Location").get()

        upper_joint = mc.rename(
            joint_map["upper"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{name}Upper",
                location=location
            ),
        )


        lower_joint = mc.rename(
            joint_map["lower"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{name}Lower",
                location=location
            ),
        )

        tip_joint = mc.rename(
            joint_map["tip"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{name}Tip",
                location=location
            ),
        )

        all_joints = [
            upper_joint,
            lower_joint,
            tip_joint,
        ]

        self.input("Root Joint").set(upper_joint)
        self.input("Tip Joint").set(tip_joint)

        if self.option("Location").get() == self.config.right:
            bony.flip.global_mirror(
                transforms=all_joints,
                across="YZ"
            )
