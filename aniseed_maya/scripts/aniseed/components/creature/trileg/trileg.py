import os
import typing

import bony
import qute
import aniseed
import shapeshift
import collections

import functools
import maya.cmds as mc



# ------------------------------------------------------------------------------
class TriLegComponent(aniseed.RigComponent):

    identifier = "Creature : Tri Leg"

    # -- These are indices to get the various joints
    INDEX_UPPER_LEG = 0
    INDEX_LOWER_LEG = 1
    INDEX_ANKLE = 2
    INDEX_FOOT = 3
    INDEX_TOE = 4

    LABELS = [
        "Upper",
        "Lower",
        "Ankle",
        "Foot",
        "Toe",
    ]

    PIVOT_ORDER = [
        "Marker : Ball Roll",
        "Marker : Heel Roll",
        "Marker : Tip Roll",
        "Marker : Inner Roll",
        "Marker : Outer Roll",
        "Marker : Foot Control"
    ]

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(TriLegComponent, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_requirement(
            name="Start Joint",
            value="",
            group="Joint Requirements"
        )

        self.declare_requirement(
            name="End Joint",
            value="",
            group="Joint Requirements"
        )

        self.declare_requirement(
            name="Twist Joints",
            value="",
            group="Joint Requirements",
            validate=False
        )

        self.declare_requirement(
            name="_MarkerCreation",
            value="",
            validate=False,
        )

        for pivot_requirement in self.PIVOT_ORDER:
            self.declare_requirement(
                name=pivot_requirement,
                value="",
                group="Guide Objects",
            )

        self.declare_option(
            name="Descriptive Prefix",
            value="Leg",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="lf",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Align Foot To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Upvector Distance Multiplier",
            value=0.5,
            group="Behaviour",
        )

        self.declare_option(
            name="Twist Count",
            value=3,
            group="Behaviour",
        )

        self.declare_output("Upper Leg")
        self.declare_output("Lower Leg")
        self.declare_output("Ankle")
        self.declare_output("Toe")

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name: str):
        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

        if requirement_name == "_MarkerCreation":
            return aniseed.widgets.everywhere.ButtonWidget(
                button_name="Create Guide Markers",
                func=functools.partial(
                    self._create_markers,
                )
            )

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(config=self.config)

    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Joints": self.create_skeleton,
        }

    # ----------------------------------------------------------------------------------
    def run(self):

        parent = self.requirement("Parent").get()
        root_joint = self.requirement("Start Joint").get()
        tip_joint = self.requirement("End Joint").get()

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Declare our list of controls
        ik_controls = []
        fk_controls = []

        org = mc.rename(
            mc.createNode("transform"),
            self.config.generate_name(
                classification=self.config.organisational,
                description=self.option("Descriptive Prefix").get(),
                location=location,
            ),
        )
        fk_shape_rotation = [180, 0, 0]
        shape_y_flip = False

        facing_dir = bony.direction.get_chain_facing_direction(
            root_joint,
            tip_joint,
        )

        if facing_dir == bony.direction.Facing.NegativeX:
            shape_y_flip = True
            fk_shape_rotation = [0, 0, 0]

        mc.parent(
            org,
            parent,
        )

        parent = org

        # -- Add the configuration control
        config_control = aniseed.control.create(
            description=f"{prefix}LegConfig",
            location=location,
            parent=parent,
            shape="core_lollipop",
            config=self.config,
            match_to=root_joint,
            shape_scale=20.0,
            rotate_shape=[0, 0, 0],
        )

        # -- Get the chain we"re to drive
        joint_chain = bony.hierarchy.get_between(
            start=root_joint,
            end=tip_joint,
        )

        # -- Create the main ik chain
        upper_to_foot_chain = bony.hierarchy.replicate_chain(
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=parent,
        )

        # -- Create the upper chain
        upper_to_ankle_chain = bony.hierarchy.replicate_chain(
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_ANKLE],
            parent=upper_to_foot_chain[0],
        )

        # -- Create the lower chain
        lower_to_foot_chain = bony.hierarchy.replicate_chain(
            from_this=joint_chain[self.INDEX_LOWER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=upper_to_foot_chain[1],
        )

        # -- Set the orients for all our mech joints
        bony.orients.move_rotations_to_joint_orients(upper_to_foot_chain)
        bony.orients.move_rotations_to_joint_orients(upper_to_ankle_chain)
        bony.orients.move_rotations_to_joint_orients(lower_to_foot_chain)

        # -- Name all our mech joints
        upper_to_foot_chain = self.apply_name_to_mech_nodes(
            nodes=upper_to_foot_chain,
            name="FullSolveIK",
        )

        upper_to_ankle_chain = self.apply_name_to_mech_nodes(
            nodes=upper_to_ankle_chain,
            name="UpperSolveIK",
        )

        lower_to_foot_chain = self.apply_name_to_mech_nodes(
            nodes=lower_to_foot_chain,
            name="LowerSolveIK",
        )
        # -- Ensure all our mech joints are not visible/selectable
        self.set_joints_to_invisible(upper_to_foot_chain)
        self.set_joints_to_invisible(upper_to_ankle_chain)
        self.set_joints_to_invisible(lower_to_foot_chain)

        # -- Create the ik handles
        upper_to_foot_ikh, _ = mc.ikHandle(
            startJoint=upper_to_foot_chain[0],
            endEffector=upper_to_foot_chain[-1],
            solver="ikRPsolver",
            priority=1,
        )

        upper_to_ankle_ikh, _ = mc.ikHandle(
            startJoint=upper_to_ankle_chain[0],
            endEffector=upper_to_ankle_chain[-1],
            solver="ikRPsolver",
            priority=1,
        )

        lower_to_foot_ikh, _ = mc.ikHandle(
            startJoint=lower_to_foot_chain[0],
            endEffector=lower_to_foot_chain[-1],
            solver="ikRPsolver",
            priority=1,
        )

        # -- Hide all our ik handles
        mc.setAttr(f"{upper_to_foot_ikh}.visibility", False)
        mc.setAttr(f"{upper_to_ankle_ikh}.visibility", False)
        mc.setAttr(f"{lower_to_foot_ikh}.visibility", False)

        # -- Determine the ankle length so we can decide how big to make the
        # -- foot controls
        reference_scale = bony.hierarchy.chain_length(
            joint_chain[2],
            joint_chain[4],
        )

        # -- Create our main controls
        foot_control = aniseed.control.create(
            description=prefix + "Foot",
            location=location,
            parent=parent,
            shape="core_paddle",
            shape_scale=reference_scale,
            rotate_shape=[0, 90, 0] if shape_y_flip else [0, -90, 0],
            config=self.config,
            match_to=self.requirement("Marker : Foot Control").get()
        )

        ik_controls.append(foot_control)

        if self.option("Align Foot To World").get():
            foot_org = aniseed.control.get_classification(
                foot_control,
                "org",
            )

            mc.xform(
                foot_org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        foot_pivot_tip, pivot_controls = self._ik_pivot(
            foot_control=foot_control,
        )

        # -- Add the heel control
        heel_control = aniseed.control.create(
            description=f"{prefix}Heel",
            location=location,
            parent=foot_pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=joint_chain[-1],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[90, 0, 0],
        )

        ik_controls.append(heel_control)

        heel_org = aniseed.control.get_classification(heel_control, "org")

        mc.xform(
            heel_org,
            rotation=mc.xform(
                foot_control,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        # -- Add the toe control
        toe_control = aniseed.control.create(
            description=f"{prefix}Toe",
            location=location,
            parent=foot_pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=joint_chain[-1],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[180, 0, 0],
        )

        ik_controls.append(toe_control)

        toe_org = aniseed.control.get_classification(toe_control, "org")
        mc.xform(
            toe_org,
            rotation=mc.xform(
                foot_control,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        full_chain_upv = aniseed.control.create(
            description=prefix + "Upvector",
            location=location,
            parent=foot_control,
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
        )

        ik_controls.append(full_chain_upv)

        full_chain_upvector_org = aniseed.control.get_classification(
            full_chain_upv,
            "org",
        )

        mc.xform(
            full_chain_upvector_org,
            translation=aniseed.utils.math.calculate_upvector_position(
                length=1,
                *upper_to_ankle_chain
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        mc.xform(
            full_chain_upv,
            translation=aniseed.utils.math.calculate_upvector_position(
                length=1,
                *upper_to_ankle_chain
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        mc.poleVectorConstraint(
            full_chain_upv,
            upper_to_foot_ikh,
            weight=1,
        )

        upper_upv_control = aniseed.control.create(
            description=prefix + "UpperUpvector",
            location=location,
            parent=upper_to_foot_chain[self.INDEX_UPPER_LEG],
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
            match_to=joint_chain[self.INDEX_LOWER_LEG],
        )

        upper_upvector_org = aniseed.control.get_classification(
            upper_upv_control,
            "org",
        )

        mc.xform(
            upper_upvector_org,
            translation=aniseed.utils.math.calculate_upvector_position(
                length=1,
                *upper_to_ankle_chain
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        lower_upv_control = aniseed.control.create(
            description=prefix + "LowerUpvector",
            location=location,
            parent=upper_to_foot_chain[self.INDEX_LOWER_LEG],
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
            match_to=joint_chain[self.INDEX_ANKLE],
        )

        lower_upvector_org = aniseed.control.get_classification(
            lower_upv_control,
            "org",
        )

        mc.xform(
            lower_upvector_org,
            translation=aniseed.utils.math.calculate_upvector_position(
                length=1,
                *lower_to_foot_chain
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        # -- Setup the upvector visibility attributes
        mc.addAttr(
            full_chain_upv,
            shortName="upperUpvectorVisibility",
            at="bool",
            dv=False,
            k=True,
        )

        mc.addAttr(
            full_chain_upv,
            shortName="lowerUpvectorVisibility",
            at="bool",
            dv=False,
            k=True,
        )

        mc.connectAttr(
            f"{full_chain_upv}.upperUpvectorVisibility",
            f"{upper_upvector_org}.visibility",
        )

        mc.connectAttr(
            f"{full_chain_upv}.lowerUpvectorVisibility",
            f"{lower_upvector_org}.visibility",
        )

        # -- Apply the upvector constraint
        mc.poleVectorConstraint(
            upper_upv_control,
            upper_to_ankle_ikh,
            weight=1,
        )

        mc.poleVectorConstraint(
            lower_upv_control,
            lower_to_foot_ikh,
            weight=1,
        )

        xform_targets = list()

        for idx in range(self.INDEX_TOE+1):

            node = mc.rename(
                mc.createNode("transform"),
                self.config.generate_name(
                    classification="xfo",
                    description=prefix + self.LABELS[idx],
                    location=location,
                ),
            )

            mc.parent(
                node,
                parent,
            )

            xform_targets.append(node)

        # -- Setup the ik handle parenting
        mc.parent(
            upper_to_foot_ikh,
            heel_control,
        )

        mc.parent(
            lower_to_foot_ikh,
            heel_control,
        )

        mc.parent(
            upper_to_ankle_ikh,
            lower_to_foot_chain[1]
        )

        mc.parentConstraint(
            heel_control,
            lower_to_foot_chain[-1],
            skipTranslate=["x", "y", "z"],
            maintainOffset=True,
        )

        mc.parentConstraint(
            upper_to_ankle_chain[0],
            xform_targets[0],
            maintainOffset=False,
        )

        mc.parentConstraint(
            upper_to_ankle_chain[1],
            xform_targets[1],
            maintainOffset=False,
        )

        mc.parentConstraint(
            lower_to_foot_chain[1],
            xform_targets[2],
            maintainOffset=False,
        )

        mc.parentConstraint(
            lower_to_foot_chain[2],
            xform_targets[3],
            maintainOffset=False,
        )

        mc.parentConstraint(
            toe_control,
            xform_targets[4],
            maintainOffset=False,
        )

        # ----------------------------------------------------------------------
        # -- FK SETUP
        fk_controls = []

        fk_parent = parent

        for idx, joint in enumerate(joint_chain):

            fk_control = aniseed.control.create(
            description=f"{prefix}{self.LABELS[idx]}FK",
                location=location,
                parent=fk_parent,
                shape="core_paddle",
                config=self.config,
                match_to=joint,
                shape_scale=reference_scale / 3.0,
                rotate_shape=[0, 0, 0],
            )

            fk_controls.append(fk_control)
            fk_parent = fk_control

        # ----------------------------------------------------------------------
        # -- NK SETUP

        # -- Now create an NK joint hierarchy, which we will use to bind
        # -- between the IK and the FK
        nk_joints = list()

        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=root_joint,
            to_this=tip_joint,
            parent=parent,
        )

        nk_joints = self.apply_name_to_mech_nodes(
            replicated_joints,
            name="LegNK",
        )

        self.set_joints_to_invisible(nk_joints)

        self.output("Upper Leg").set(nk_joints[0])
        self.output("Lower Leg").set(nk_joints[1])
        self.output("Ankle").set(nk_joints[2])
        self.output("Toe").set(nk_joints[3])

        # ----------------------------------------------------------------------
        # -- Set the visibility attributes
        proxies = collections.OrderedDict()
        proxies['ik_fk'] = 0
        proxies['show_ik'] = 1
        proxies['show_fk'] = 0
        proxies["show_twists"] = 0

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
        for idx in range(len(self.LABELS)):

            ik_node = xform_targets[idx]
            fk_node = fk_controls[idx]
            nk_node = nk_joints[idx]
            skl_node = joint_chain[idx]

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

        self.setup_twists(
            skeletal_chain=joint_chain,
            nk_chain=nk_joints,
            root_index=self.INDEX_UPPER_LEG,
            parent=parent, # nk_joints[self.INDEX_UPPER_LEG],
            vis_driver=f"{config_control}.show_twists",
        )

        self.setup_twists(
            skeletal_chain=joint_chain,
            nk_chain=nk_joints,
            root_index=self.INDEX_LOWER_LEG,
            parent=nk_joints[self.INDEX_UPPER_LEG],
            vis_driver=f"{config_control}.show_twists",
        )

        self.setup_twists(
            skeletal_chain=joint_chain,
            nk_chain=nk_joints,
            root_index=self.INDEX_ANKLE,
            parent=nk_joints[self.INDEX_LOWER_LEG],
            vis_driver=f"{config_control}.show_twists",
        )


    # ----------------------------------------------------------------------------------
    def _ik_pivot(self, foot_control):

        aniseed.utils.attribute.add_separator_attr(foot_control)

        controls = list()

        last_parent = foot_control

        for pivot_label in self.PIVOT_ORDER:

            guide = self.requirement(pivot_label).get()
            description = pivot_label.split(":")[-1].replace(" ", "")

            pivot_control = aniseed.control.create(
            description=description,
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_symbol_rotator",
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
            self.requirement("Start Joint").get(),
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

            if self.requirement(marker_label):
                self.requirement(marker_label).set(marker)

            created_markers.append(marker)

        return created_markers

    # ----------------------------------------------------------------------------------
    def create_skeleton(self, twist_count=None):
        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        if mc.nodeType(parent) != "joint":
            confirmation = qute.utilities.request.confirmation(
                title="Confirmation",
                label=(
                    "You are creating a skeleton under a node that is not a joint. "
                    "Are you sure you want to continue?"
                ),
            )

            if not confirmation:
                return

        if twist_count is None:
            twist_count = qute.utilities.request.text(
                title="Twist Count",
                label="How many twist joints do you want on each section?"
            )
            twist_count = int(twist_count)

        joint_map = bony.writer.load_joints_from_file(
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "tri_leg.json",
            ),
            apply_names=False,
        )

        location = self.option("Location").get()

        joint_map["upper"] = mc.rename(
            joint_map["upper"],
            self.config.generate_name(
                classification=self.config.joint,
                description="UpperLeg",
                location=location
            ),
        )

        joint_map["lower"] = mc.rename(
            joint_map["lower"],
            self.config.generate_name(
                classification=self.config.joint,
                description="LowerLeg",
                location=location
            ),
        )

        joint_map["ankle"] = mc.rename(
            joint_map["ankle"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Ankle",
                location=location
            ),
        )

        joint_map["foot"] = mc.rename(
            joint_map["foot"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Foot",
                location=location
            ),
        )

        joint_map["toe"] = mc.rename(
            joint_map["toe"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Toe",
                location=location
            ),
        )

        self.requirement("Start Joint").set(joint_map["upper"])
        self.requirement("End Joint").set(joint_map["toe"])

        all_joints = [n for n in joint_map.values()]

        twist_labels = [
            "upper",
            "lower",
            "ankle",
            "foot",
            "toe",
        ]

        if twist_count > 0:

            twist_joints = list()

            for segment_idx in range(3):

                label = twist_labels[segment_idx]
                parent = joint_map[label]
                next_joint = joint_map[twist_labels[segment_idx + 1]]

                name = self.option(
                    "Descriptive Prefix"
                ).get() + f"{label.title()}LegTwist"

                increment = mc.getAttr(
                    f"{next_joint}.translateX",
                ) / (twist_count - 1)

                for twist_idx in range(twist_count):

                    twist_joint = aniseed.joint.create(
                        description=name,
                        location=self.option("Location").get(),
                        parent=parent,
                        match_to=parent,
                        config=self.config
                    )
                    twist_joints.append(twist_joint)

                    mc.setAttr(
                        f"{twist_joint}.translateX",
                        increment * twist_idx
                    )
                    all_joints.append(twist_joint)

            self.requirement("Twist Joints").set(twist_joints)

        if self.option("Location").get() == self.config.right:
            bony.flip.global_mirror(
                transforms=all_joints,
                across="YZ"
            )

    # ----------------------------------------------------------------------------------
    def setup_twists(self, skeletal_chain, nk_chain, root_index, parent, vis_driver=None):

        all_twist_joints = self.requirement("Twist Joints").get()

        twists_joints_for_segment = []

        for child in  mc.listRelatives(skeletal_chain[root_index], children=True, type="joint") or list():
            if child in all_twist_joints:
                twists_joints_for_segment.append(child)

        if not twists_joints_for_segment:
            return

        twist_component = self.rig.component_library.get("Augment : Twister")(
            "",
            stack=self.rig,
        )

        twist_component.requirement("Joints").set(twists_joints_for_segment)
        twist_component.requirement("Parent").set(parent)
        twist_component.requirement("Root").set(nk_chain[root_index])
        twist_component.requirement("Tip").set(nk_chain[root_index+1])

        twist_component.option("Constrain Root").set(False)
        twist_component.option("Constrain Tip").set(True)
        twist_component.option("Descriptive Prefix").set(f"{self.LABELS[root_index]}Twist")
        twist_component.option("Location").set(self.option("Location").get())

        twist_component.run()
        if vis_driver:
            for twist in twist_component.builder.all_controls():
                mc.connectAttr(
                    vis_driver,
                    f"{twist}.visibility",
                )

    # ----------------------------------------------------------------------------------
    def apply_name_to_mech_nodes(self, nodes, name):
        renamed_nodes = []

        for node in nodes:
            renamed_nodes.append(
                mc.rename(
                    node,
                    self.config.generate_name(
                        classification="mech",
                        description=name,
                        location=self.option("Location").get(),
                    )
                )
            )

        return renamed_nodes

    # ----------------------------------------------------------------------------------
    @classmethod
    def set_joints_to_invisible(cls, joints):
        for joint in joints:
            mc.setAttr(
                f"{joint}.drawStyle",
                2,
            )
