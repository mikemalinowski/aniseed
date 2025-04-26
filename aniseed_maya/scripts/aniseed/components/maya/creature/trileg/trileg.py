import os
import typing
import aniseed
import qtility
import functools
import collections
import aniseed_toolkit
import maya.cmds as mc


# noinspection DuplicatedCode,PyUnresolvedReferences
class TriLegComponent(aniseed.RigComponent):

    identifier = "Creature : Tri Leg"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

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
        "Marker : Ball Twist",
        "Marker : Heel Roll",
        "Marker : Tip Roll",
        "Marker : Inner Roll",
        "Marker : Outer Roll",
        "Marker : Foot Control"
    ]

    _DEFAULT_GUIDE_MARKER_DATA = {
        "Marker : Tip Roll": {"node": None, "matrix": [0.0319, -0.9995, 0.0, 0.0, 0.0175, 0.0006, 0.9999, 0.0, -0.9993, -0.0319, 0.0175, 0.0, 3.9326, -2.6052, -0.22, 1.0]},
        "Marker : Heel Roll": {"node": None, "matrix": [0.0319, -0.9995, 0.0, 0.0, -0.0, 0.0, -1.0, 0.0, 0.9995, 0.0319, -0.0, 0.0, -10.6578, -3.0708, -0.1011, 1.0]},
        "Marker : Inner Roll": {"node": None, "matrix": [0.0319, -0.9995, 0.0, 0.0, -0.9995, -0.0319, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.3375, -2.7199, 4.1299, 1.0]},
        "Marker : Outer Roll": {"node": None, "matrix": [0.0319, -0.9995, 0.0, 0.0, 0.9995, 0.0319, 0.0, 0.0, -0.0, -0.0, 1.0, 0.0, 0.3375, -2.7237, -4.1299, 1.0]},
        "Marker : Ball Twist": {"node": None, "matrix": [0.0, 0.0, -1.0, 0.0, -0.0319, 0.9995, -0.0, 0.0, 0.9995, 0.0319, -0.0, 0.0, 0.281, -2.7217, -0.1902, 1.0]},
        "Marker : Foot Control": {"node": None, "matrix": [0.0, 0.0, -1.0, 0.0, -0.0319, 0.9995, -0.0, 0.0, 0.9995, 0.0319, -0.0, 0.0, 0.281, -2.7217, -0.1902, 1.0]},
    }

    def __init__(self, *args, **kwargs):
        super(TriLegComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Leg Root",
            value="",
            group="Joint Requirements"
        )

        self.declare_input(
            name="Toe",
            value="",
            group="Joint Requirements"
        )

        self.declare_input(
            name="Twist Joints",
            value="",
            group="Joint Requirements",
            validate=False
        )

        self.declare_option(
            name="_MarkerData",
            value=self._DEFAULT_GUIDE_MARKER_DATA.copy(),
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

        self.declare_output("Upper Leg")
        self.declare_output("Lower Leg")
        self.declare_output("Ankle")
        self.declare_output("Toe")

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(config=self.config)

    def user_functions(self) -> typing.Dict[str, callable]:
        menu = collections.OrderedDict()

        # -- Only show the skeleton creation tools if we dont have a skeleton
        leg_joint = self.input("Leg Root").get()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        if not leg_joint or not mc.objExists(leg_joint):
            menu["Create Joints"] = functools.partial(self.user_fun_create_skeleton)
            return menu

        # -- Depending on whether we have a guide or not, change what we show
        # -- in the actions menu
        if self._get_guide():
            menu["Remove Guide"] = functools.partial(self.user_func_delete_guide)

        else:
            menu["Create Guide"] = functools.partial(self.user_func_create_guide)

        # -- Providing we have joints or a guide, we show the align ik tool
        menu["Align IK"] = functools.partial(self.user_func_align_guide_ik)

        return menu

    def is_valid(self) -> bool:

        if self._get_guide():
            print("You must remove the guide before building")
            return False

        leg_root = self.input("Leg Root").get()
        toe_tip = self.input("Toe").get()

        all_joints = bony.hierarchy.get_between(
            leg_root,
            toe_tip,
        )

        if len(all_joints) < 5:
            print(
                (
                    f"Expected at least 5 joints "
                    "(upper leg, lower leg, anke, foot, toe). "
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

    def run(self):

        parent = self.input("Parent").get()
        root_joint = self.input("Leg Root").get()
        tip_joint = self.input("Toe").get()

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Declare our list of our ik controls
        ik_controls = []

        parent = aniseed_toolkit.run(
            "Create Basic Transform",
            classification=self.config.organisational,
            description=self.option("Descriptive Prefix").get(),
            location=location,
            config=self.config,
            parent=parent
        )

        facing_dir = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            root_joint,
            tip_joint,
        )

        shape_y_flip = False
        if facing_dir == facing_dir.NegativeX:
            shape_y_flip = True

        # -- Add the configuration control
        config_control = aniseed_toolkit.run("Create Control",
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
        joint_chain = aniseed_toolkit.run(
            "Get Joints Between",
            start=root_joint,
            end=tip_joint,
        )

        # -- Create the main ik chain
        upper_to_foot_chain = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=parent,
        )

        # -- Create the upper chain
        upper_to_ankle_chain = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_ANKLE],
            parent=upper_to_foot_chain[0],
        )

        # -- Create the lower chain
        lower_to_foot_chain = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=joint_chain[self.INDEX_LOWER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=upper_to_foot_chain[1],
        )

        chains = [
            upper_to_ankle_chain,
            upper_to_foot_chain,
            lower_to_foot_chain,
        ]

        # -- Set the orients for all our mech joints
        for chain in chains:
            aniseed_toolkit.run(
                "Move Joint Rotations To Orients",
                chain,
            )
            aniseed_toolkit.run(
                "Hide Nodes",
                chain,
            )

        # -- Name all our mech joints
        upper_to_foot_chain = self._apply_mechanism_name(
            nodes=upper_to_foot_chain,
            description="FullSolveIK",
        )

        upper_to_ankle_chain = self._apply_mechanism_name(
            nodes=upper_to_ankle_chain,
            description="UpperSolveIK",
        )

        lower_to_foot_chain = self._apply_mechanism_name(
            nodes=lower_to_foot_chain,
            description="LowerSolveIK",
        )

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
        reference_scale = aniseed_toolkit.run(
            "Get Chain Length",
            joint_chain[2],
            joint_chain[4],
        )

        # -- Create our main controls
        foot_control = aniseed_toolkit.run(
            "Create Control",
            description=prefix + "Foot",
            location=location,
            parent=parent,
            shape="core_paddle",
            shape_scale=reference_scale,
            rotate_shape=[0, 90, 0] if shape_y_flip else [0, -90, 0],
            config=self.config,
        )

        mc.xform(
            foot_control.org,
            matrix=self.option("_MarkerData").get()["Marker : Foot Control"]["matrix"],
            worldSpace=True,
        )

        ik_controls.append(foot_control.ctl)

        if self.option("Align Foot To World").get():
            mc.xform(
                foot_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        foot_pivot_tip, pivot_controls = self._setup_ik_pivot_behaviour(
            foot_control=foot_control,
        )

        # -- Add the heel control
        heel_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}Heel",
            location=location,
            parent=foot_pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=joint_chain[-1],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[90, 0, 0],
        )

        ik_controls.append(heel_control.ctl)

        mc.xform(
            heel_control.org,
            rotation=mc.xform(
                foot_control.ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        # -- Add the toe control
        toe_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}Toe",
            location=location,
            parent=foot_pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=joint_chain[-1],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[180, 0, 0],
        )

        ik_controls.append(toe_control.ctl)

        mc.xform(
            toe_control.org,
            rotation=mc.xform(
                foot_control.ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        full_chain_upv = aniseed_toolkit.run(
            "Create Control",
            description=prefix + "Upvector",
            location=location,
            parent=foot_control.ctl,
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
        )

        ik_controls.append(full_chain_upv.ctl)

        mc.xform(
            full_chain_upv.org,
            translation=aniseed_toolkit.run(
                "Calculate Upvector Position",
                length=1,
                *upper_to_ankle_chain
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        mc.xform(
            full_chain_upv.ctl,
            translation=aniseed_toolkit.run(
                "Calculate Upvector Position",
                length=1,
                *upper_to_ankle_chain
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        mc.poleVectorConstraint(
            full_chain_upv.ctl,
            upper_to_foot_ikh,
            weight=1,
        )

        upper_upv_control = aniseed_toolkit.run(
            "Create Control",
            description=prefix + "UpperUpvector",
            location=location,
            parent=upper_to_foot_chain[self.INDEX_UPPER_LEG],
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
            match_to=joint_chain[self.INDEX_LOWER_LEG],
        )

        mc.xform(
            upper_upv_control.org,
            translation=aniseed_toolkit.run(
                "Caclculate Upvector Position",
                length=1,
                *upper_to_ankle_chain
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        lower_upv_control = aniseed_toolkit.run(
            "Create Control",
            description=prefix + "LowerUpvector",
            location=location,
            parent=upper_to_foot_chain[self.INDEX_LOWER_LEG],
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
            match_to=joint_chain[self.INDEX_ANKLE],
        )

        mc.xform(
            lower_upv_control.org,
            translation=aniseed_toolkit.run(
                "Calculate Upvector Position",
                length=1,
                *lower_to_foot_chain
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        # -- Setup the upvector visibility attributes
        mc.addAttr(
            full_chain_upv.ctl,
            shortName="upperUpvectorVisibility",
            at="bool",
            dv=False,
            k=True,
        )

        mc.addAttr(
            full_chain_upv.ctl,
            shortName="lowerUpvectorVisibility",
            at="bool",
            dv=False,
            k=True,
        )

        mc.connectAttr(
            f"{full_chain_upv.ctl}.upperUpvectorVisibility",
            f"{upper_upv_control.org}.visibility",
        )

        mc.connectAttr(
            f"{full_chain_upv.ctl}.lowerUpvectorVisibility",
            f"{lower_upv_control.org}.visibility",
        )

        # -- Apply the upvector constraint
        mc.poleVectorConstraint(
            upper_upv_control.ctl,
            upper_to_ankle_ikh,
            weight=1,
        )

        mc.poleVectorConstraint(
            lower_upv_control.ctl,
            lower_to_foot_ikh,
            weight=1,
        )

        xform_targets = list()

        for idx in range(self.INDEX_TOE + 1):
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
            heel_control.ctl,
        )

        mc.parent(
            lower_to_foot_ikh,
            heel_control.ctl,
        )

        mc.parent(
            upper_to_ankle_ikh,
            lower_to_foot_chain[1]
        )

        mc.parentConstraint(
            heel_control.ctl,
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
            toe_control.ctl,
            xform_targets[4],
            maintainOffset=False,
        )

        # -- FK SETUP
        fk_controls = []

        fk_parent = parent

        for idx, joint in enumerate(joint_chain):
            fk_control = aniseed_toolkit.run(
                "Create Control",
                description=f"{prefix}{self.LABELS[idx]}FK",
                location=location,
                parent=fk_parent,
                shape="core_paddle",
                config=self.config,
                match_to=joint,
                shape_scale=reference_scale / 3.0,
                rotate_shape=[0, 0, 0],
            )

            fk_controls.append(fk_control.ctl)
            fk_parent = fk_control.ctl

        # ----------------------------------------------------------------------
        # -- NK SETUP

        # -- Now create an NK joint hierarchy, which we will use to bind
        # -- between the IK and the FK
        replicated_joints = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=root_joint,
            to_this=tip_joint,
            parent=parent,
        )

        nk_joints = self._apply_mechanism_name(
            replicated_joints,
            description="LegNK",
        )
        aniseed_toolkit.run(
            "Hide Nodes",
            nk_joints,
        )
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
                config_control.ctl,
                shortName=label,
                at='float',
                min=0,
                max=1,
                dv=proxies[label],
                k=True,
            )

        for ik_control in ik_controls:
            mc.setAttr(
                f"{ik_control}.visibility",
                lock=False,
            )

            mc.connectAttr(
                f"{config_control.ctl}.show_ik",
                f"{ik_control}.visibility",
            )

        for fk_control in fk_controls:
            mc.setAttr(
                f"{fk_control}.visibility",
                lock=False,
            )

            mc.connectAttr(
                f"{config_control.ctl}.show_fk",
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
                f"{config_control.ctl}.ik_fk",
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

        self._setup_twist_behaviour(
            skeletal_chain=joint_chain,
            nk_chain=nk_joints,
            root_index=self.INDEX_UPPER_LEG,
            parent=parent,  # nk_joints[self.INDEX_UPPER_LEG],
            vis_driver=f"{config_control.ctl}.show_twists",
        )

        self._setup_twist_behaviour(
            skeletal_chain=joint_chain,
            nk_chain=nk_joints,
            root_index=self.INDEX_LOWER_LEG,
            parent=nk_joints[self.INDEX_UPPER_LEG],
            vis_driver=f"{config_control.ctl}.show_twists",
        )

        self._setup_twist_behaviour(
            skeletal_chain=joint_chain,
            nk_chain=nk_joints,
            root_index=self.INDEX_ANKLE,
            parent=nk_joints[self.INDEX_LOWER_LEG],
            vis_driver=f"{config_control.ctl}.show_twists",
        )

    def _setup_ik_pivot_behaviour(self, foot_control):

        aniseed.utils.attribute.add_separator_attr(foot_control.ctl)

        controls = list()

        last_parent = foot_control.ctl

        for pivot_label in self.PIVOT_ORDER:
            marker_transform = self.option("_MarkerData").get()[pivot_label]["matrix"]

            description = pivot_label.split(":")[-1].replace(" ", "")

            pivot_control = aniseed_toolkit.run(
                "Create Control",
                description=description,
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
            )

            mc.xform(
                pivot_control.org,
                matrix=marker_transform,
                worldSpace=True,
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
                pivot_control.ctl,
            )

            mc.xform(
                parameter_pivot,
                matrix=mc.xform(
                    pivot_control.ctl,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            # -- Add the parameter to the foot control
            mc.addAttr(
                foot_control.ctl,
                shortName=description,
                at="float",
                dv=0,
                k=True,
            )

            mc.connectAttr(
                f"{foot_control.ctl}.{description}",
                f"{parameter_pivot}.rotateY",
            )

            controls.append(pivot_control.ctl)
            last_parent = parameter_pivot

        return last_parent, controls

    def _setup_twist_behaviour(
            self, 
            skeletal_chain, 
            nk_chain, 
            root_index, 
            parent, 
            vis_driver=None,
    ):

        all_twist_joints = self.input("Twist Joints").get()

        twists_joints_for_segment = []

        children = mc.listRelatives(
            skeletal_chain[root_index],
            children=True,
            type="joint",
        )

        for child in children or list():
            if child in all_twist_joints:
                twists_joints_for_segment.append(child)

        if not twists_joints_for_segment:
            return

        twist_component = self.rig.component_library.request("Augment : Twister")(
            "",
            stack=self.rig,
        )

        twist_component.input("Joints").set(twists_joints_for_segment)
        twist_component.input("Parent").set(parent)
        twist_component.input("Root").set(nk_chain[root_index])
        twist_component.input("Tip").set(nk_chain[root_index + 1])

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

    def _apply_mechanism_name(self, nodes, description):
        renamed_nodes = []

        for node in nodes:
            renamed_nodes.append(
                mc.rename(
                    node,
                    self.config.generate_name(
                        classification="mech",
                        description=description,
                        location=self.option("Location").get(),
                    )
                )
            )

        return renamed_nodes

    def user_func_create_skeleton(self, twist_count=None):
        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        if mc.nodeType(parent) != "joint":
            confirmation = qtility.request.confirmation(
                title="Confirmation",
                message=(
                    "You are creating a skeleton under a node that is not a joint. "
                    "Are you sure you want to continue?"
                ),
            )

            if not confirmation:
                return

        if twist_count is None:
            twist_count = qtility.request.text(
                title="Twist Count",
                message="How many twist joints do you want on each section?"
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

        self.input("Leg Root").set(joint_map["upper"])
        self.input("Toe").set(joint_map["toe"])

        all_joints = []

        twist_labels = [
            "upper",
            "lower",
            "ankle",
            "foot",
            "toe",
        ]

        for label in twist_labels:
            all_joints.append(joint_map[label])

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
                    twist_joint = aniseed_toolkit.run(
                        "Create Joint",
                        description=name,
                        location=self.option("Location").get(),
                        parent=parent,
                        match_to=parent,
                        config=self.config
                    )
                    twist_joints.append(twist_joint)

                    # -- TODO: We shouldnt hard code X here. We should use boney
                    # -- to determine the axis down the bone
                    mc.setAttr(
                        f"{twist_joint}.translateX",
                        increment * twist_idx
                    )
                    all_joints.append(twist_joint)

            self.input("Twist Joints").set(twist_joints)

        if self.option("Location").get() == self.config.right:
            aniseed_toolkit.run(
                "Global Mirror",
                transforms=all_joints,
                across="YZ"
            )

        # -- After we have build the joints, immediately create the guide
        self.create_guide()

    def _get_guide(self):

        connections = mc.listConnections(
            f"{self.input('Leg Root').get()}.message",
            destination=True,
            plugs=True,
        )

        for connection in connections or list():
            if "guideRig" in connection:
                return connection.split(".")[0]

    def user_func_create_guide(self):

        leg_root = self.input("Leg Root").get()
        toe = self.input("Toe").get()

        guide_org = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="gde",
            description=f"LegManipulationGuide",
            location=self.option("Location").get(),
            config=self.config.ctl,
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

        all_joints = aniseed_toolkit.run(
            "Get Joints Between",
            leg_root,
            toe,
        )

        all_controls = list()
        parent = guide_org

        for joint in all_joints:
            guide_control = aniseed_toolkit.run(
                "Create Guide",
                joint,
                parent=parent,
            )

            parent = guide_control
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

                tween_control = aniseed_toolkit.run(
                    "Create Guide Tween",
                    child,
                    from_this=control,
                    to_this=next_control,
                    parent=control,
                )
                all_controls.append(tween_control)

        # -- Now create the guide markers
        marker_parent = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="gde",
            description="foot_markers",
            location=self.option("Location").get(),
            config=self.config,
            parent=guide_org,
        )

        stored_marker_data = self.option("_MarkerData").get()
        created_markers = dict()

        for marker_label in stored_marker_data:
            marker = aniseed_toolkit.run(
                "Create Basic Transform",
                classification="gde",
                description=marker_label.split(":")[-1].replace(" ", ""),
                location=self.option("Location").get(),
                config=self.config.ctl,
                parent=marker_parent,
            )

            all_controls.append(marker)

            mc.xform(
                marker,
                matrix=stored_marker_data[marker_label]["matrix"],
                worldSpace=True,
            )

            stored_marker_data[marker_label]["node"] = marker

            aniseed_toolkit.run(
                "Apply Shape",
                node=marker,
                data="core_symbol_rotator",
                color=[
                    0,
                    255,
                    0,
                ],
            )

            created_markers[marker_label] = marker

        self.option("_MarkerData").set(stored_marker_data)

        return guide_org

    def user_func_delete_guide(self):

        guide_root = self._get_guide()

        if not guide_root:
            return

        transforms = dict()

        all_chain = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Leg Root").get(),
            self.input("Toe").get(),
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
                    worldSpace=True,
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
                matrix=mc.xform(
                    marker_data[label]["node"],
                    query=True,
                    matrix=True,
                    worldSpace=True,
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

    def user_func_align_guide_ik(self):

        all_chain = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Leg Root").get(),
            self.input("Toe").get(),
        )

        if self._get_guide():
            self.delete_guide()

            mc.select(
                [
                    all_chain[0],
                    all_chain[-1],
                ]
            )
            aniseed_toolkit.run(
                "Align Bones For IK",
            )
            self.create_guide()

        else:
            mc.select(
                [
                    all_chain[0],
                    all_chain[-1],
                ]
            )
            aniseed_toolkit.run(
                "Align Bones For IK",
            )