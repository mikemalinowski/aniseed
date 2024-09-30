import os
import qute
import bony
import functools
import shapeshift
import collections

import aniseed
import maya.cmds as mc



# --------------------------------------------------------------------------------------
class LegComponent(aniseed.RigComponent):

    identifier = "Standard : Leg"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(LegComponent, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_requirement(
            name="Leg Root",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_requirement(
            name="Toe Tip",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_requirement(
            name="Upper Twist Joints",
            description="All upper twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_requirement(
            name="Lower Twist Joints",
            description="All lower twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_requirement(
            name="Marker : Foot Control",
            value="",
            validate=False,
            group="Guide Objects",
        )

        self.declare_requirement(
            name="Marker : Tip Roll",
            value="",
            validate=False,
            group="Guide Objects",
        )

        self.declare_requirement(
            name="Marker : Heel Roll",
            value="",
            validate=False,
            group="Guide Objects",
        )

        self.declare_requirement(
            name="Marker : Ball Roll",
            value="",
            validate=False,
            group="Guide Objects",
        )

        self.declare_requirement(
            name="Marker : Inner Roll",
            value="",
            validate=False,
            group="Guide Objects",
        )

        self.declare_requirement(
            name="Marker : Outer Roll",
            value="",
            validate=False,
            group="Guide Objects",
        )

        self.declare_requirement(
            name="_MarkerCreation",
            value=None,
            validate=False,
            group="Guide Objects",
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
            name="Align Foot To World",
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

        self.declare_output(name="Blended Upper Leg")
        self.declare_output(name="Blended Lower Leg")
        self.declare_output(name="Blended Foot")
        self.declare_output(name="Blended Toe")
        self.declare_output("Ik Foot")
        self.declare_output("Upvector")

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name):

        if requirement_name in ["Parent", "Leg Root", "Toe Tip"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "_MarkerCreation":
            return aniseed.widgets.everywhere.ButtonWidget(
                button_name="Create Guide Markers",
                func=functools.partial(
                    self._create_markers,
                )
            )

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    # ----------------------------------------------------------------------------------
    def user_functions(self):
        return {
            "Create Joints": self.build_skeleton,
        }

    # ----------------------------------------------------------------------------------
    def is_valid(self) -> bool:

        leg_root = self.requirement("Leg Root").get()
        toe_tip = self.requirement("Toe Tip").get()

        all_joints = bony.hierarchy.get_between(
            leg_root,
            toe_tip,
        )

        if len(all_joints) < 4:
            print(
                (
                    f"Expected at least 4 joints "
                    "(upper leg, lower leg, foot, toe). "
                    f"But got {len(all_joints)} joints"
                )
            )
            return False

        facing_dir = bony.direction.get_chain_facing_direction(
            leg_root,
            all_joints[2],
        )

        directions = bony.direction.Facing

        if facing_dir != directions.NegativeX and facing_dir != directions.PositiveX:
            print("The leg must be aligned to the X axis")
            return False

        return True

    # ----------------------------------------------------------------------------------
    # noinspection DuplicatedCode
    def run(self):

        leg_root = self.requirement("Leg Root").get()
        toe_tip = self.requirement("Toe Tip").get()
        parent = self.requirement("Parent").get()
        directions = bony.direction.Facing

        all_joints = bony.hierarchy.get_between(
            leg_root,
            toe_tip,
        )

        # -- We now make an assumption about the number of bones in our chain
        knee_joint = all_joints[1]
        foot_joint = all_joints[2]
        toe_joint = all_joints[3]

        # -- Determine the options we're building with
        prefix = self.option('Description Prefix').get()
        location = self.option("Location").get()

        org = mc.rename(
            mc.createNode("transform"),
            self.config.generate_name(
                classification=self.config.organisational,
                description=prefix + "Leg",
                location=location,
            ),
        )

        mc.parent(
            org,
            parent,
        )

        parent = org

        # -- This is the default rotation of our shapes based on X down the chain
        fk_shape_rotation = [0, 0, 0]

        shape_y_flip = False

        facing_dir = bony.direction.get_chain_facing_direction(
            leg_root,
            foot_joint,
        )

        if facing_dir == directions.NegativeX:
            shape_y_flip = True
            fk_shape_rotation = [180, 0, 0]

        # -- Add the configuration control
        config_control = aniseed.control.create(
            description=f"{prefix}LegConfig",
            location=location,
            parent=self.requirement("Parent").get(),
            shape="core_lollipop",
            config=self.config,
            match_to=leg_root,
            shape_scale=20.0,
            rotate_shape=fk_shape_rotation,
        )

        # ----------------------------------------------------------------------
        # -- NK SETUP

        # -- Now create an NK joint hierarchy, which we will use to bind
        # -- between the IK and the FK
        nk_joints = list()
        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=leg_root,
            to_this=toe_joint,
            parent=parent,
        )

        # -- Rename the nk joints
        for nk_joint in replicated_joints:
            nk_joint = mc.rename(
                nk_joint,
                self.config.generate_name(
                    classification="mech",
                description=f"{prefix}LegNK",
                    location=location,
                )
            )
            nk_joints.append(nk_joint)

        self.output("Blended Upper Leg").set(nk_joints[0])
        self.output("Blended Lower Leg").set(nk_joints[1])
        self.output("Blended Foot").set(nk_joints[2])
        self.output("Blended Toe").set(nk_joints[3])

        # ----------------------------------------------------------------------
        # -- IK SETUP

        # -- Now create the Ik joints
        ik_controls = list()
        ik_joints = list()

        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=leg_root,
            to_this=foot_joint,
            parent=parent,
        )

        # -- Rename the ik joints
        for ik_joint in replicated_joints:

            ik_joint = mc.rename(
                ik_joint,
                self.config.generate_name(
                    classification="mech",
                description=f"{prefix}LegIK",
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
            description=f"{prefix}LegUpvector",
            location=location,
            parent=parent,
            shape="core_sphere",
            config=self.config,
            match_to=ik_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )
        ik_controls.append(upvector)
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
        ik_foot_ctl = aniseed.control.create(
            description=f"{prefix}Foot",
            location=location,
            parent=parent,
            shape="core_paddle",
            config=self.config,
            match_to=self.requirement("Marker : Foot Control").get(),
            shape_scale=40.0,
            rotate_shape=[0, 90, 0] if shape_y_flip else [0, -90, 0],
        )
        ik_controls.append(ik_foot_ctl)
        self.output("Ik Foot").set(ik_foot_ctl)

        if self.option("Align Foot To World").get():
            foot_org = aniseed.control.get_classification(
                ik_foot_ctl,
                "org",
            )

            mc.xform(
                foot_org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        pivot_tip, pivot_controls = self._ik_pivot(
            foot_control=ik_foot_ctl,
            foot_bone=foot_joint,
        )
        ik_controls.extend(pivot_controls)

        # -- Add the heel control
        heel_control = aniseed.control.create(
            description=f"{prefix}Heel",
            location=location,
            parent=pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=toe_joint,
            shape_scale=10,
            rotate_shape=[90, 0, 0],
        )
        ik_controls.append(heel_control)

        heel_org = aniseed.control.get_classification(heel_control, "org")
        mc.xform(
            heel_org,
            rotation=mc.xform(
                ik_foot_ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        # -- Parent the ikhandle under the heel control so it
        # -- moves along with it
        mc.parent(
            handle,
            heel_control,
        )

        # -- Add the toe control
        toe_control = aniseed.control.create(
            description=f"{prefix}Toe",
            location=location,
            parent=pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=toe_joint,
            shape_scale=10,
            rotate_shape=[180, 0, 0],
        )
        ik_controls.append(toe_control)

        toe_org = aniseed.control.get_classification(toe_control, "org")
        mc.xform(
            toe_org,
            rotation=mc.xform(
                ik_foot_ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        if self.option("Apply Soft Ik").get():

            root_marker = mc.createNode("transform")

            mc.parent(
                root_marker,
                parent,
            )

            mc.xform(
                root_marker,
                matrix=mc.xform(
                    ik_joints[0],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            tip_marker = mc.createNode("transform")

            mc.parent(
                tip_marker,
                pivot_tip,
            )

            mc.xform(
                tip_marker,
                matrix=mc.xform(
                    ik_joints[-1],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )
            aniseed.utils.mech.soft_ik.create(
                root_marker,
                tip_marker,
                ik_joints[-2],
                ik_joints[-1],
                host=ik_foot_ctl,
            )


        # -- We need to constrain the end joint in rotation to the
        # -- hand control, because the ik does not do that.
        mc.parentConstraint(
            pivot_tip,
            ik_joints[-1],
            skipTranslate=['x', 'y', 'z'],
        )

        ik_bindings = [
            ik_joints[0],
            ik_joints[1],
            # ik_joints[2],
            heel_control,
            toe_control,
        ]

        # ----------------------------------------------------------------------
        # -- FK SETUP
        fk_controls = []

        fk_parent = self.requirement("Parent").get()

        for joint in all_joints[:-1]:

            fk_control = aniseed.control.create(
            description=f"{prefix}{self.config.extract_description(joint)}FK",
                location=location,
                parent=fk_parent,
                shape="core_paddle",
                config=self.config,
                match_to=joint,
                shape_scale=20.0,
                rotate_shape=fk_shape_rotation,
            )
            fk_controls.append(fk_control)
            fk_parent = fk_control

        # ----------------------------------------------------------------------
        # -- Bink the IK, FK and NK
        proxies = collections.OrderedDict()
        proxies['ik_fk'] = 0
        proxies['show_ik'] = 1
        proxies['show_fk'] = 0

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

        for ik_control in ik_controls:
            mc.connectAttr(
                f"{config_control}.show_ik",
                f"{ik_control}.visibility",
            )

        for fk_control in fk_controls:
            mc.connectAttr(
                f"{config_control}.show_fk",
                f"{fk_control}.visibility",
            )

        # -- We need to constrain our nk between the ik and the fk
        for ik_node, fk_node, nk_node, skl_node in zip(ik_bindings, fk_controls, nk_joints, all_joints[:-1]):

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
                f"{config_control}.ik_fk",
                f"{reverse_node}.inputX",
            )

            mc.connectAttr(
                f"{reverse_node}.outputX",
                f"{cns}.{ik_driven}",
            )

            mc.connectAttr(
                f"{config_control}.ik_fk",
                f"{cns}.{fk_driven}",
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

        upper_twist_joints = self.requirement("Upper Twist Joints").get()
        lower_twist_joints = self.requirement("Lower Twist Joints").get()

        if upper_twist_joints:
            twist_component = self.rig.component_library.get("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.requirement("Joints").set(upper_twist_joints)
            twist_component.requirement("Parent").set(parent)
            twist_component.requirement("Root").set(nk_joints[0])
            twist_component.requirement("Tip").set(nk_joints[1])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("UpperTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                shapeshift.rotate_shape(twist, *fk_shape_rotation)

        if lower_twist_joints:

            twist_component = self.rig.component_library.get("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.requirement("Joints").set(lower_twist_joints)
            twist_component.requirement("Parent").set(nk_joints[1])
            twist_component.requirement("Root").set(nk_joints[1])
            twist_component.requirement("Tip").set(nk_joints[2])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("LowerTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                shapeshift.rotate_shape(twist, *fk_shape_rotation)

    # ----------------------------------------------------------------------------------
    def _ik_pivot(self, foot_control, foot_bone):

        aniseed.utils.attribute.add_separator_attr(foot_control)

        # ----------------------------------------------------------------------
        # -- Now create the start pivot
        pivot_order = [
            'Marker : Ball Roll',
            'Marker : Heel Roll',
            'Marker : Tip Roll',
            'Marker : Inner Roll',
            'Marker : Outer Roll',
        ]

        controls = list()

        last_parent = foot_control

        for pivot_label in pivot_order:

            guide = self.requirement(pivot_label).get()
            description = pivot_label.split(":")[-1].replace(" ", "")

            pivot_control = aniseed.control.create(
            description=description,
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
                match_to=guide,
            )

            parameter_pivot = mc.createNode("transform")
            parameter_pivot = mc.rename(
                parameter_pivot,
                self.config.generate_name(
                    classification="piv",
                    location=self.option("Location").get(),
                description=description,
                ),
            )

            mc.parent(
                parameter_pivot,
                pivot_control,
            )

            mc.xform(
                parameter_pivot,
                matrix=mc.xform(
                    guide,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            # -- Add the parameter to the foot control
            mc.addAttr(
                foot_control,
                shortName=description,
                at="float",
                dv=0,
                k=True,
            )

            mc.connectAttr(
                f"{foot_control}.{description}",
                f"{parameter_pivot}.rotateY",
            )

            controls.append(pivot_control)
            last_parent = parameter_pivot

        return last_parent, controls


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
                label="How many twist joints do you want on the upper arm?"
            )
            lower_twist_count = int(lower_twist_count)

        joint_map = bony.writer.load_joints_from_file(
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "leg_joints.json",
            ),
            apply_names=False,
        )

        location = self.option("Location").get()

        upper_leg = mc.rename(
            joint_map["JNT_UpperLeg_01_LF"],
            self.config.generate_name(
                classification=self.config.joint,
                description="UpperLeg",
                location=location
            ),
        )

        lower_leg = mc.rename(
            joint_map["JNT_LowerLeg_01_LF"],
            self.config.generate_name(
                classification=self.config.joint,
                description="LowerLeg",
                location=location
            ),
        )

        foot = mc.rename(
            joint_map["JNT_Foot_01_LF"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Foot",
                location=location
            ),
        )

        toe = mc.rename(
            joint_map["JNT_Toe_01_LF"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Toe",
                location=location
            ),
        )

        toe_tip = mc.rename(
            joint_map["JNT_Toe_02_LF"],
            self.config.generate_name(
                classification=self.config.joint,
                description="ToeTip",
                location=location
            ),
        )

        all_joints = [upper_leg, lower_leg, foot, toe, toe_tip]

        self.requirement("Leg Root").set(upper_leg)
        self.requirement("Toe Tip").set(toe_tip)

        if upper_twist_count:
            parent = upper_leg

            upper_increment = mc.getAttr(
                f"{lower_leg}.translateX",
            ) / (upper_twist_count - 1)

            upper_twist_joints = list()

            for idx in range(upper_twist_count):
                twist_joint = aniseed.joint.create(
                    description=self.option("Description Prefix").get() + "UpperLegTwist",
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
            self.requirement("Upper Twist Joints").set(upper_twist_joints)

        if lower_twist_count:
            parent = lower_leg

            lower_increment = mc.getAttr(
                f"{foot}.translateX",
            ) / (lower_twist_count - 1)

            lower_twist_joints = list()

            for idx in range(lower_twist_count):
                twist_joint = aniseed.joint.create(
                    description=self.option("Description Prefix").get() + "LowerLegTwist",
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

            self.requirement("Lower Twist Joints").set(lower_twist_joints)

        # -- Trigger the markers
        all_joints.extend(self._create_markers())

        if self.option("Location").get() == self.config.right:
            bony.flip.global_mirror(
                transforms=all_joints,
                across="YZ"
            )

    # ----------------------------------------------------------------------------------
    def _create_markers(self):

        marker_parent = mc.createNode("transform")
        marker_parent = mc.rename(
            marker_parent,
            self.config.generate_name(
                classification="gde",
            description="foot_markers",
                location=self.option("Location").get(),
            )
        )

        mc.pointConstraint(
            self.requirement("Toe Tip").get(),
            marker_parent,
            maintainOffset=False,
            skip=["y"],
        )

        markers = {
            "Marker : Tip Roll": dict(tz=1.5, ry=180, rz=90),
            "Marker : Heel Roll": dict(tz=-2.5, rz=-90),
            "Marker : Inner Roll": dict(tx=-1.5, rx=-90, rz=-90),
            "Marker : Outer Roll": dict(tx=1.5, rx=90, rz=-90),
            "Marker : Ball Roll": dict(rx=-180, ry=-180),
            "Marker : Foot Control": dict(),
        }

        created_markers = []

        for marker_label, attributes in markers.items():

            marker = mc.createNode("transform")

            marker = mc.rename(
                marker,
                self.config.generate_name(
                    classification="gde",
                description=marker_label.split(":")[-1].replace(" ", ""),
                    location=self.option("Location").get(),
                )
            )
            mc.parent(
                marker,
                marker_parent,
            )

            mc.xform(
                marker,
                matrix=mc.xform(
                    marker_parent,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            for attribute_name, attribute_value in attributes.items():
                mc.setAttr(
                    f"{marker}.{attribute_name}",
                    attribute_value,
                )

            shapeshift.apply(
                node=marker,
                data="core_symbol_rotator",
            )

            self.requirement(marker_label).set(marker)

            created_markers.append(marker)

        return created_markers
