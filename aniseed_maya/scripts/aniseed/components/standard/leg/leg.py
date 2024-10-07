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

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    _DEFAULT_GUIDE_MARKER_DATA = {
        "Marker : Tip Roll": {
            'node': None,
             'matrix': [-0.1025, -0.9923, 0.0694, 0, 0.0152, 0.0682, 0.9976, 0, -0.9946, 0.1033, 0.0081, 0, 3.9242, 2.3434, -0.22, 1],
        },
        "Marker : Heel Roll": {
            'node': None,
            'matrix': [-0.1025, -0.9923, 0.0694, 0, -0.0152, -0.0682, -0.9976, 0, 0.9946, -0.1033, -0.0081, 0, -10.6328, 3.8549, -0.1011, 1],
        },
        "Marker : Inner Roll": {
            'node': None,
            'matrix': [-0.1025, -0.9923, 0.0694, 0, -0.9946, 0.1033, 0.0081, 0, -0.0152, -0.0682, -0.9976, 0, 0.347, 3.0168, 4.1299, 1],
        },
        "Marker : Outer Roll": {
            'node': None,
            'matrix': [-0.1025, -0.9923, 0.0694, 0, 0.9946, -0.1033, -0.0081, 0, 0.0152, 0.0682, 0.9976, 0, 0.2093, 2.4004, -4.8938, 1],
        },
        "Marker : Ball Roll": {
            'node': None,
            'matrix': [-0.0152, -0.0682, -0.9976, 0, 0.1025, 0.9923, -0.0694, 0, 0.9946, -0.1033, -0.0081, 0, 0.281, 2.7217, -0.1902, 1],
        },
        "Marker : Foot Control": {
            'node': None,
            'matrix': [-0.0152, -0.0682, -0.9976, 0, 0.1025, 0.9923, -0.0694, 0, 0.9946, -0.1033, -0.0081, 0, 0.281, 2.7217, -0.1902, 1],
        },
    }
    
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
            name="Toe",
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

        self.declare_option(
            name="_MarkerData",
            value=self._DEFAULT_GUIDE_MARKER_DATA.copy(),
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

        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):

        if option_name.startswith("_"):
            return self.IGNORE_OPTION_FOR_UI

        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    # ----------------------------------------------------------------------------------
    def user_functions(self):

        menu = collections.OrderedDict()

        # -- Only show the skeleton creation tools if we dont have a skeleton
        leg_joint = self.requirement("Leg Root").get()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        if not leg_joint or not mc.objExists(leg_joint):
            menu["Create Joints"] = self.build_skeleton
            return menu

        # -- Depending on whether we have a guide or not, change what we show
        # -- in the actions menu
        if self.get_guide():
            menu["Remove Guide"] = self.delete_guide

        else:
            menu["Create Guide"] = self.create_guide

        # -- Providing we have joints or a guide, we show the align ik tool
        menu["Align IK"] = self.align_guide_ik

        return menu

    # ----------------------------------------------------------------------------------
    def is_valid(self) -> bool:

        if self.get_guide():
            print("You must remove the guide before building")
            return False

        leg_root = self.requirement("Leg Root").get()
        toe_tip = self.requirement("Toe").get()

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
        toe_tip = self.requirement("Toe").get()
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
            #match_to=self.requirement("Marker : Foot Control").get(),
            shape_scale=40.0,
            rotate_shape=[0, 90, 0] if shape_y_flip else [0, -90, 0],
        )

        bony.transform.apply_matrix_relative_to(
            aniseed.control.get_classification(ik_foot_ctl, "org"),
            matrix=self.option("_MarkerData").get()["Marker : Foot Control"]["matrix"],
            relative_to=toe_joint,
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
            toe_bone=toe_joint,
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

        for joint in all_joints:

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
        for ik_node, fk_node, nk_node, skl_node in zip(ik_bindings, fk_controls, nk_joints, all_joints):

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
    def _ik_pivot(self, foot_control, foot_bone, toe_bone):

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

            marker_transform = self.option("_MarkerData").get()[pivot_label]["matrix"]

            description = pivot_label.split(":")[-1].replace(" ", "")

            pivot_control = aniseed.control.create(
            description=description,
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
            )

            bony.transform.apply_matrix_relative_to(
                aniseed.control.get_classification(pivot_control, "org"),
                matrix=marker_transform,
                relative_to=toe_bone,
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
                    pivot_control,
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
                label="How many twist joints do you want on the upper leg?"
            )
            upper_twist_count = int(upper_twist_count)

        if lower_twist_count is None:
            lower_twist_count = qute.utilities.request.text(
                title="Upper Twist Count",
                label="How many twist joints do you want on the lower leg?"
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
            joint_map["upperleg"],
            self.config.generate_name(
                classification=self.config.joint,
                description="UpperLeg",
                location=location
            ),
        )

        lower_leg = mc.rename(
            joint_map["lowerleg"],
            self.config.generate_name(
                classification=self.config.joint,
                description="LowerLeg",
                location=location
            ),
        )

        foot = mc.rename(
            joint_map["foot"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Foot",
                location=location
            ),
        )

        toe = mc.rename(
            joint_map["toe"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Toe",
                location=location
            ),
        )

        all_joints = [upper_leg, lower_leg, foot, toe]

        self.requirement("Leg Root").set(upper_leg)
        self.requirement("Toe").set(toe)

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

        if self.option("Location").get() == self.config.right:
            bony.flip.global_mirror(
                transforms=all_joints,
                across="YZ"
            )

        self.create_guide()


    # ----------------------------------------------------------------------------------
    def get_guide(self):

        connections = mc.listConnections(
            f"{self.requirement('Leg Root').get()}.message",
            destination=True,
            plugs=True,
        )

        for connection in connections or list():
            if "guideRig" in connection:
                return connection.split(".")[0]

    # ----------------------------------------------------------------------------------
    def create_guide(self):

        leg_root = self.requirement("Leg Root").get()
        toe = self.requirement("Toe").get()

        guide_org = aniseed.control.basic_transform(
            classification="gde",
            description=f"LegManipulationGuide",
            location=self.option("Location").get(),
            config=self.config,
        )

        mc.addAttr(
            guide_org,
            shortName="guideRig",
            at="message",
        )

        mc.connectAttr(
            f"{leg_root}.message",
            f"{guide_org}.guideRig",
        )

        all_joints = bony.hierarchy.get_between(
            leg_root,
            toe,
        )

        all_controls = list()

        for joint in all_joints:
            guide_control = aniseed.utils.guide.create(
                joint,
                parent=guide_org,
            )

            all_controls.append(guide_control)

        for idx in range(len(all_joints)):

            if idx == len(all_joints) - 1:
                continue

            joint = all_joints[idx]
            control = all_controls[idx]
            next_control = all_controls[idx + 1]

            for child in mc.listRelatives(joint, children=True, type="joint") or list():

                if child in all_joints:
                    continue

                tween_control = aniseed.utils.guide.tween(
                    child,
                    from_this=control,
                    to_this=next_control,
                    parent=control,
                )
                all_controls.append(tween_control)

        # -- Now create the guide markers
        marker_parent = mc.createNode("transform")
        marker_parent = mc.rename(
            marker_parent,
            self.config.generate_name(
                classification="gde",
            description="foot_markers",
                location=self.option("Location").get(),
            )
        )

        mc.parent(
            marker_parent,
            guide_org,
        )

        mc.pointConstraint(
            self.requirement("Toe").get(),
            marker_parent,
            maintainOffset=False,
            skip=["y"],
        )

        stored_marker_data = self.option("_MarkerData").get()
        created_markers = dict()

        for marker_label in stored_marker_data:

            marker = aniseed.control.basic_transform(
                classification="gde",
                description=marker_label.split(":")[-1].replace(" ", ""),
                location=self.option("Location").get(),
                config=self.config,
                parent=marker_parent,
            )

            all_controls.append(marker)

            bony.transform.apply_matrix_relative_to(
                marker,
                matrix=stored_marker_data[marker_label]["matrix"],
                relative_to=self.requirement("Toe").get(),
            )
            stored_marker_data[marker_label]["node"] = marker

            shapeshift.apply(
                node=marker,
                data="core_symbol_rotator",
            )

            created_markers[marker_label] = marker

        self.option("_MarkerData").set(stored_marker_data)

    # ----------------------------------------------------------------------------------
    def delete_guide(self):

        guide_root = self.get_guide()

        if not guide_root:
            return

        transforms = dict()

        all_chain = bony.hierarchy.get_between(
            self.requirement("Leg Root").get(),
            self.requirement("Toe").get(),
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

        # -- Store the marker data before it gets removed
        marker_data = self.option("_MarkerData").get() or dict()
        new_data = dict()

        for label in marker_data:

            new_data[label] = dict(
                node=None,
                matrix=bony.transform.get_matrix_relative_to(
                    marker_data[label]["node"],
                    relative_to=self.requirement("Toe").get()
                ),
            )

        self.option("_MarkerData").set(new_data)

        # -- Now we delete the guide rig
        for connection in connections:
            if "guideRig" in connection:
                mc.delete(connection.split(".")[0])

        # -- Ensure all the joints are transformed exactly how
        # -- we want them
        for joint, matrix in transforms.items():
            mc.xform(
                joint,
                matrix=matrix,
            )


    # ----------------------------------------------------------------------------------
    def align_guide_ik(self):

        guide_root = self.get_guide()

        all_chain = bony.hierarchy.get_between(
            self.requirement("Leg Root").get(),
            self.requirement("Toe").get(),
        )

        if guide_root:
            self.delete_guide()

            mc.select(
                [
                    all_chain[0],
                    all_chain[-1],
                ]
            )
            bony.ik.clean_ik_plane_with_ui()

            self.create_guide()

        else:
            mc.select(
                [
                    all_chain[0],
                    all_chain[-1],
                ]
            )
            bony.ik.clean_ik_plane_with_ui()
