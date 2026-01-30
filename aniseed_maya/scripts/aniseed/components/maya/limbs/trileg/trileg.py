import os
import typing
import aniseed
import qtility
import functools
import collections
import aniseed_toolkit
import maya.cmds as mc
import maya


# noinspection DuplicatedCode,PyUnresolvedReferences
class TriLegComponent(aniseed.RigComponent):
    identifier = "Limb : Tri Leg"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    # -- These are indices to get the various joints
    INDEX_UPPER_LEG = 0
    INDEX_MID_LEG = 1
    INDEX_LOWER_LEG = 2
    INDEX_FOOT = 3
    INDEX_TOE = 4

    LABELS = [
        "Upper",
        "Mid",
        "Lower",
        "Foot",
        "Toe",
    ]

    PIVOT_ORDER = [
        "ball",
        "heel",
        "tip",
        "inner",
        "outer",
    ]

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
            name="Upper Twist Joints",
            description="All upper twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_input(
            name="Mid Twist Joints",
            description="All mid twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_input(
            name="Lower Twist Joints",
            description="All lower twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_input(
            name="Foot Twist Joints",
            description="All lower twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_option(
            name="GuideData",
            value=dict(
                Markers=dict(
                    ball=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                          0.0, 0.0, 3.297, 1.0],
                    heel=[0.0, 1.0, 0.0, 0.0, -1.0, 0.05, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                          0.0, 0.0, -7, 1.0],
                    tip=[0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.06, 0.0, -1.0, 0.0,
                         0.0, 0.0, 7.095, 1.0],
                    inner=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0,
                           -4.0, 0.0, 3.3, 1.0],
                    outer=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, -1.0, 0.0, 0.0, 0.0,
                           4.0, 0.0, 3.3, 1.0],
                ),
                LinkedGuide=None,
            ),
            hidden=True,
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
            name="Upvector Position Multiplier",
            value=1.0,
            group="Behaviour",
        )

        self.declare_output("Blended Upper Leg")
        self.declare_output("Blended Mid Leg")
        self.declare_output("Blended Lower Leg")
        self.declare_output("Blended Foot")
        self.declare_output("Blended Toe")

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

    def user_functions(self) -> typing.Dict[str, callable]:
        menu = collections.OrderedDict()

        # -- Only show the skeleton creation tools if we dont have a skeleton
        leg_joint = self.input("Leg Root").get()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        if not leg_joint or not mc.objExists(leg_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)
            return menu

        # -- Depending on whether we have a guide or not, change what we show
        # -- in the actions menu
        guide_data = self.option("GuideData").get()
        linked_guide = guide_data["LinkedGuide"]

        if linked_guide and mc.objExists(linked_guide):
            # -- Depending on whether we have a guide or not, change what we show
            # -- in the actions menu
            menu["Remove Guide"] = functools.partial(self.user_func_remove_guide)

        else:
            menu["Create Guide"] = functools.partial(self.user_func_build_guide)

        return menu

    def is_valid(self) -> bool:

        guide_data = self.option("GuideData").get()
        linked_guide = guide_data["LinkedGuide"]

        if linked_guide and mc.objExists(linked_guide):
            print("You must remove the guide before building")
            return False

        leg_root = self.input("Leg Root").get()
        toe_tip = self.input("Toe").get()

        all_joints = aniseed_toolkit.run(
            "Get Joints Between",
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

        facing_dir = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            leg_root,
            all_joints[2],
        )

        if facing_dir != facing_dir.NegativeX and facing_dir != facing_dir.PositiveX:
            print("The leg must be aligned to the X axis")
            return False

        return True

    def run(self):

        # -- Ensure the spring solver is enabled
        maya.mel.eval("ikSpringSolver()")

        # -- Get the required input and option data
        parent = self.input("Parent").get()
        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Declare our list of our ik controls
        ik_controls = []

        # -- To encapsulate the entire rig segment, create a
        # -- parent node
        parent = aniseed_toolkit.run(
            "Create Basic Transform",
            classification=self.config.organisational,
            description=prefix,
            location=location,
            config=self.config,
            parent=parent
        )

        # -- Create the IK and FK setups
        ik_data = self.create_ik_setup(parent=parent)
        fk_data = self.create_fk_setup(parent=parent)

        # -- Using the data from the ik and fk setups we
        # -- can now construct the blend setup
        self.create_nk_setup(
            parent=parent,
            ik_data=ik_data,
            fk_data=fk_data,
        )

    def create_nk_setup(self, parent, ik_data, fk_data):

        prefix = self.option('Descriptive Prefix').get()
        location = self.option("Location").get()
        leg_root = self.input("Leg Root").get()
        toe_tip = self.input("Toe").get()

        config_control = aniseed_toolkit.run("Create Control",
                                             description=f"{prefix}Config",
                                             location=location,
                                             parent=parent,
                                             shape="core_lollipop",
                                             config=self.config,
                                             match_to=leg_root,
                                             shape_scale=20.0,
                                             rotate_shape=[0, 0, 0],
                                             )

        mc.addAttr(
            config_control.ctl,
            shortName="show_ik",
            at='float',
            min=0,
            max=1,
            dv=1,
            k=True,
        )
        mc.addAttr(
            config_control.ctl,
            shortName="show_fk",
            at='float',
            min=0,
            max=1,
            dv=0,
            k=True,
        )
        ik_visibility_attribute = f"{config_control.ctl}.show_ik"
        fk_visibility_attribute = f"{config_control.ctl}.show_fk"

        for ik_control in ik_data["controls"]:
            ik_control = aniseed_toolkit.run(
                "Get Control",
                ik_control,
            )
            mc.connectAttr(
                f"{config_control.ctl}.show_ik",
                f"{ik_control.off}.visibility",
                force=True,
            )

        for fk_control in fk_data["controls"]:
            fk_control = aniseed_toolkit.run(
                "Get Control",
                fk_control,
            )
            mc.connectAttr(
                f"{config_control.ctl}.show_fk",
                f"{fk_control.off}.visibility",
                force=True,
            )

        deformation_joints = aniseed_toolkit.run(
            "Get Joints Between",
            start=self.input("Leg Root").get(),
            end=self.input("Toe").get(),
        )

        blend_chain_setup = aniseed_toolkit.run(
            "Create Blend Chain",
            parent=parent,
            transforms_a=ik_data["blend_points"],
            transforms_b=fk_data["blend_points"],
            attribute_host=config_control.ctl,
            attribute_name="ikfk",
            match_transforms=deformation_joints,
        )

        nk_joints = []
        for idx, blend_joint in enumerate(blend_chain_setup.out_blend_joints):
            nk_joints.append(
                mc.rename(
                    blend_joint,
                    self.config.generate_name(
                        classification="mech",
                        description=f"{prefix}LegNK",
                        location=location,
                    )
                ),
            )
            mc.parentConstraint(
                nk_joints[-1],
                deformation_joints[idx],
                maintainOffset=True,
            )

            mc.scaleConstraint(
                nk_joints[-1],
                deformation_joints[idx],
                maintainOffset=True,
            )

        self.output("Blended Upper Leg").set(nk_joints[self.INDEX_UPPER_LEG])
        self.output("Blended Mid Leg").set(nk_joints[self.INDEX_MID_LEG])
        self.output("Blended Lower Leg").set(nk_joints[self.INDEX_LOWER_LEG])
        self.output("Blended Foot").set(nk_joints[self.INDEX_FOOT])
        self.output("Blended Toe").set(nk_joints[self.INDEX_TOE])

    def create_fk_setup(self, parent):

        root_joint = self.input("Leg Root").get()
        tip_joint = self.input("Toe").get()

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        fk_controls = []

        # -- Get the chain we"re to drive
        joint_chain = aniseed_toolkit.run(
            "Get Joints Between",
            start=root_joint,
            end=tip_joint,
        )

        reference_scale = aniseed_toolkit.run(
            "Get Chain Length",
            joint_chain[self.INDEX_LOWER_LEG],
            joint_chain[self.INDEX_FOOT],
        )

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

        return dict(
            controls=fk_controls,
            blend_points=fk_controls,
        )

    def create_ik_setup(self, parent):

        root_joint = self.input("Leg Root").get()
        tip_joint = self.input("Toe").get()

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        guide_data = self.option("GuideData").get()

        # -- Get the chain we"re to drive
        joint_chain = aniseed_toolkit.run(
            "Get Joints Between",
            start=root_joint,
            end=tip_joint,
        )

        # -- Create the ik spring chain that will span the whole leg
        upper_to_foot_chain = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=parent,
        )
        upper_to_foot_chain = self._apply_mechanism_name(
            upper_to_foot_chain,
            description="FullSolve"
        )
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            upper_to_foot_chain,
        )
        upper_to_foot_ikh, _ = mc.ikHandle(
            startJoint=upper_to_foot_chain[0],
            endEffector=upper_to_foot_chain[-1],
            solver="ikRPsolver",
            priority=1,
        )
        upper_to_foot_ikh = mc.rename(
            self.config.generate_name(
                classification="ikh",
                description=f"{prefix}SpringSolveHandle",
                location=location,
            ),
        )
        mc.connectAttr(
            "ikSpringSolver.message",
            f"{upper_to_foot_ikh}.ikSolver",
            force=True,
        )
        mc.ikSpringSolverRestPose(upper_to_foot_ikh)

        # -- Create the reverse ankle chain which allows for
        # -- ankle rotation adjustment, which will follow the
        # -- movement of the three bone chain
        reverse_ankle_chain = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=joint_chain[self.INDEX_LOWER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=parent,
        )
        reverse_ankle_chain = self._apply_mechanism_name(
            reverse_ankle_chain,
            description="ReverseAnkle"
        )
        reverse_ankle_chain = aniseed_toolkit.run(
            "Reverse Chain",
            reverse_ankle_chain,
        )
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            reverse_ankle_chain,
        )
        mc.parent(
            reverse_ankle_chain[0],
            upper_to_foot_chain[self.INDEX_LOWER_LEG],
        )

        # -- Create the upper leg two bone ik - which will follow
        # -- the ankle.
        upper_two_bone_ik = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_LOWER_LEG],
            parent=parent,
        )
        upper_two_bone_ik = self._apply_mechanism_name(
            upper_two_bone_ik,
            description="UpperSolve"
        )
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            upper_two_bone_ik,
        )
        upper_chain_ik, _ = mc.ikHandle(
            startJoint=upper_two_bone_ik[0],
            endEffector=upper_two_bone_ik[-1],
            solver="ikRPsolver",
            priority=1,
        )
        mc.parent(
            upper_chain_ik,
            reverse_ankle_chain[-1],
        )

        # -- Now create the controls we will use to manipulate it all
        reference_scale = aniseed_toolkit.run(
            "Get Chain Length",
            upper_to_foot_chain[self.INDEX_LOWER_LEG],
            upper_to_foot_chain[self.INDEX_FOOT],
        )

        # -- Create our main controls
        foot_control = aniseed_toolkit.run(
            "Create Control",
            description=prefix + "IKFoot",
            location=location,
            parent=parent,
            shape="core_paddle",
            shape_scale=reference_scale,
            rotate_shape=[0, 90, 180],
            config=self.config,
        )
        mc.xform(
            foot_control.org,
            matrix=guide_data["Markers"]["ball"],
            worldSpace=True,
        )
        if self.option("Align Foot To World").get():
            mc.xform(
                foot_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Create the foot pivot setup
        foot_pivot_tip, pivot_controls = self._setup_ik_pivot_behaviour(
            foot_control=foot_control,
        )

        # -- Add the toe control
        heel_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}Heel",
            location=location,
            parent=foot_pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=joint_chain[self.INDEX_TOE],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[90, 0, 0],
        )
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
            match_to=joint_chain[self.INDEX_TOE],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[180, 0, 0],
        )
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

        # -- Create the ankle control
        ankle_control = aniseed_toolkit.run(
            "Create Control",
            description=prefix + "Ankle",
            location=location,
            parent=upper_to_foot_chain[self.INDEX_LOWER_LEG],  # heel_control.ctl,
            shape="core_paddle",
            shape_scale=reference_scale,
            match_to=upper_to_foot_chain[self.INDEX_LOWER_LEG],
            config=self.config,
        )
        mc.xform(
            ankle_control.org,
            worldSpace=True,
            translation=mc.xform(
                upper_to_foot_chain[self.INDEX_FOOT],
                query=True,
                translation=True,
                worldSpace=True,
            ),
        )

        # -- Now we have our controls we can start to parent the IK
        # -- accordingly.
        ankle_addition_zero = self._apply_mechanism_name(
            nodes=[mc.createNode("transform")],
            description="AnkleAdditionZero",
        )[0]
        mc.xform(
            ankle_addition_zero,
            worldSpace=True,
            matrix=mc.xform(
                ankle_control.ctl,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
        )
        mc.parent(ankle_addition_zero, upper_to_foot_chain[self.INDEX_LOWER_LEG])

        ankle_addition = self._apply_mechanism_name(
            nodes=[mc.createNode("transform")],
            description="AnkleAdditionBlend",
        )[0]
        mc.xform(
            ankle_addition,
            worldSpace=True,
            matrix=mc.xform(
                ankle_control.ctl,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
        )
        mc.parent(ankle_addition, ankle_addition_zero)
        mc.connectAttr(f"{ankle_control.ctl}.rotate", f"{ankle_addition}.rotate")
        mc.parent(reverse_ankle_chain[0], ankle_addition)
        mc.parent(upper_to_foot_ikh, heel_control.ctl)

        # -- Setup the polevector
        full_chain_upv = aniseed_toolkit.run(
            "Create Control",
            description=prefix + "Upvector",
            location=location,
            parent=foot_control.ctl,
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
        )
        mc.xform(
            full_chain_upv.org,
            translation=aniseed_toolkit.run(
                "Calculate Upvector Position",
                length=1,
                *upper_two_bone_ik
            ),
            rotation=[0, 0, 0],
            worldSpace=True,
        )
        self.non_flip_polevector(
            ik_handle=upper_to_foot_ikh,
            polevector_target=full_chain_upv.ctl,
            check_node=upper_to_foot_chain[self.INDEX_MID_LEG],
        )
        self.non_flip_polevector(
            ik_handle=upper_chain_ik,
            polevector_target=full_chain_upv.ctl,
            check_node=upper_two_bone_ik[self.INDEX_MID_LEG],
        )

        # -- Create the foot/toe chain
        foot_to_toe_chain = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=joint_chain[self.INDEX_FOOT],
            to_this=joint_chain[self.INDEX_TOE],
            parent=parent,
        )
        foot_to_toe_chain = self._apply_mechanism_name(
            nodes=foot_to_toe_chain,
            description="IKFootChain",
        )
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            foot_to_toe_chain,
        )
        mc.parentConstraint(
            heel_control.ctl,
            foot_to_toe_chain[0],
            maintainOffset=True,
        )
        mc.parentConstraint(
            toe_control.ctl,
            foot_to_toe_chain[-1],
            maintainOffset=True,
        )

        ik_controls = pivot_controls[:]
        ik_controls.append(foot_control.ctl)
        ik_controls.append(ankle_control.ctl)
        ik_controls.append(toe_control.ctl)
        ik_controls.append(full_chain_upv.ctl)
        return dict(
            controls=ik_controls,
            blend_points=[
                upper_two_bone_ik[0],  # Upper leg
                upper_two_bone_ik[1],  # Mid Leg
                reverse_ankle_chain[-1],  # Lower Leg
                foot_to_toe_chain[0],  # Foot
                foot_to_toe_chain[1],  # Toe
            ]
        )

    def non_flip_polevector(self, ik_handle, polevector_target, check_node):

        pre_position = mc.xform(
            check_node,
            query=True,
            translation=True,
            worldSpace=True,
        )

        mc.poleVectorConstraint(
            polevector_target,
            ik_handle,
            weight=1,
        )

        post_position = mc.xform(
            check_node,
            query=True,
            translation=True,
            worldSpace=True,
        )

        for idx, axis in enumerate(["X", "Y", "Z"]):
            if abs(pre_position[idx] - post_position[idx]) > 0.1:
                mc.setAttr(f"{ik_handle}.twist", 180)
                return

    def create_twists(self, nk_chain, parent):

        upper_twist_joints = self.input("Upper Twist Joints").get()
        lower_twist_joints = self.input("Lower Twist Joints").get()

        if upper_twist_joints:
            twist_component = self.rig.component_library.request("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(upper_twist_joints)
            twist_component.input("Parent").set(parent)
            twist_component.input("Root").set(nk_chain[0])
            twist_component.input("Tip").set(nk_chain[1])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("UpperTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

        if lower_twist_joints:
            twist_component = self.rig.component_library.request("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(lower_twist_joints)
            twist_component.input("Parent").set(nk_chain[2])
            twist_component.input("Root").set(nk_chain[2])
            twist_component.input("Tip").set(nk_chain[3])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("LowerTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

    def _setup_ik_pivot_behaviour(self, foot_control):

        guide_data = self.option("GuideData").get()
        prefix = self.option("Descriptive Prefix").get()
        controls = list()

        last_parent = foot_control.ctl

        for pivot_label in self.PIVOT_ORDER:
            description = pivot_label.title()

            pivot_control = aniseed_toolkit.run(
                "Create Control",
                description=f"{prefix}{description}",
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
            )

            mc.xform(
                pivot_control.org,
                matrix=guide_data["Markers"][pivot_label],
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

    def _apply_mechanism_name(self, nodes, description):
        renamed_nodes = []
        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        for node in nodes:
            renamed_nodes.append(
                mc.rename(
                    node,
                    self.config.generate_name(
                        classification="mech",
                        description=f"{prefix}{description}",
                        location=location,
                    )
                )
            )

        return renamed_nodes

    def user_func_create_skeleton(
            self,
            parent=None,
            upper_twist_count=None,
            lower_twist_count=None,
    ):
        try:
            parent = parent or mc.ls(sl=True)[0]
        except:
            parent = None

        descriptive_prefix = self.option("Descriptive Prefix").get()

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

        if upper_twist_count is None:
            upper_twist_count = qtility.request.text(
                title="Upper Twist Count",
                message="How many twist joints do you want on the upper leg?"
            )
            upper_twist_count = int(upper_twist_count)

        if lower_twist_count is None:
            lower_twist_count = qtility.request.text(
                title="Upper Twist Count",
                message="How many twist joints do you want on the lower leg?"
            )
            lower_twist_count = int(lower_twist_count)

        joint_map = aniseed_toolkit.run(
            "Load Joints File",
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
                description=f"{descriptive_prefix}UpperLeg",
                location=location
            ),
        )

        joint_map["mid"] = mc.rename(
            joint_map["mid"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{descriptive_prefix}MidLeg",
                location=location
            ),
        )

        joint_map["lower"] = mc.rename(
            joint_map["lower"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{descriptive_prefix}LowerLeg",
                location=location
            ),
        )

        joint_map["foot"] = mc.rename(
            joint_map["foot"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{descriptive_prefix}Foot",
                location=location
            ),
        )

        joint_map["toe"] = mc.rename(
            joint_map["toe"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{descriptive_prefix}Toe",
                location=location
            ),
        )

        self.input("Leg Root").set(joint_map["upper"])
        self.input("Toe").set(joint_map["toe"])

        all_joints = []

        if upper_twist_count:
            parent = joint_map["upper"]

            upper_increment = mc.getAttr(
                f"{joint_map['upper']}.translateX",
            ) / (upper_twist_count - 1)

            upper_twist_joints = list()

            for idx in range(upper_twist_count):
                twist_joint = aniseed_toolkit.run(
                    "Create Joint",
                    description=self.option(
                        "Descriptive Prefix").get() + "UpperLegTwist",
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
            parent = joint_map["lower"]

            lower_increment = mc.getAttr(
                f"{joint_map['foot']}.translateX",
            ) / (lower_twist_count - 1)

            lower_twist_joints = list()

            for idx in range(lower_twist_count):
                twist_joint = aniseed_toolkit.run(
                    "Create Joint",
                    description=self.option(
                        "Descriptive Prefix").get() + "LowerLegTwist",
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

        # -- After we have build the joints, immediately create the guide
        self.user_func_build_guide()

        # -- Mirror the guide markers
        if self.option("Location").get() == self.config.right:
            guide_data = self.option("GuideData")["markers"]
            markers = list()

            for _, data in guide_data.items():
                markers.append(data["node"])

            aniseed_toolkit.run(
                "Global Mirror",
                transforms=markers,
                across="YZ",
            )

    def user_func_build_guide(self):

        guide_org = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="gde",
            description="LegGuide",
            location=self.option("Location").get(),
            config=self.config,
            match_to=self.input("Toe").get(),
        )
        aniseed_toolkit.run(
            "Apply Shape",
            node=guide_org,
            data="core_circle",
            color=[0, 255, 0],
        )
        mc.xform(
            guide_org,
            rotation=[0, 0, 0],
            worldSpace=True,
        )
        ws_translation = mc.xform(
            guide_org,
            query=True,
            worldSpace=True,
            translation=True,
        )
        ws_translation[1] = 0
        mc.xform(
            guide_org,
            translation=ws_translation,
            worldSpace=True,
        )

        guide_data = self.option("GuideData").get()

        for marker_name, marker_matrix in guide_data["Markers"].items():
            marker = aniseed_toolkit.run(
                "Create Basic Transform",
                classification="gde",
                description=marker_name.title(),
                location=self.option("Location").get(),
                config=self.config,
                parent=guide_org,
            )
            mc.xform(
                marker,
                matrix=marker_matrix,
                worldSpace=True,
            )
            aniseed_toolkit.run(
                "Apply Shape",
                node=marker,
                data="core_symbol_rotator",
                color=[0, 255, 0],
            )
            aniseed_toolkit.run(
                "Tag Node",
                node=marker,
                tag=marker_name,
            )

        # -- Store the linked guide
        guide_data["LinkedGuide"] = guide_org
        self.option("GuideData").set(guide_data)

        return guide_org

    def user_func_remove_guide(self):

        guide_data = self.option("GuideData").get()
        linked_guide = guide_data["LinkedGuide"]

        if not linked_guide:
            return

        for marker_name, _ in guide_data["Markers"].items():
            marker = aniseed_toolkit.run(
                "Find First Child With Tag",
                node=linked_guide,
                tag=marker_name,
            )
            if not marker:
                continue

            guide_data["Markers"][marker_name] = mc.xform(
                marker,
                query=True,
                matrix=True,
                worldSpace=True,
            )

        guide_data["LinkedGuide"] = None
        self.option("GuideData").set(guide_data)

        mc.delete(linked_guide)
