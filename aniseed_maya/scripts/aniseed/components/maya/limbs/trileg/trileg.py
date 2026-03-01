import os
import typing
import aniseed
import qtility
import functools
import collections
import aniseed_toolkit
import mref
from maya import cmds
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
            value=self.default_guide_data(),
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

        # -- These options are hidden and for intialisation only
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Build Skeleton", value=True, pre_expose=True)

        self.declare_output("Blended Upper Leg")
        self.declare_output("Blended Mid Leg")
        self.declare_output("Blended Lower Leg")
        self.declare_output("Blended Foot")
        self.declare_output("Blended Toe")

    def on_enter_stack(self):

        # -- Read our options
        build_skeleton = self.option("Build Skeleton")
        upper_twist_count = self.option("Upper Twist Count")
        lower_twist_count = self.option("Lower Twist Count")

        # -- To reach here, we have not - so lets mark this as being processed
        # -- regardless of whether or not we need to build the skeleton
        build_skeleton.set_hidden(True)
        upper_twist_count.set_hidden(True)
        lower_twist_count.set_hidden(True)

        # -- If we do not need to build the skeleton, we can exit
        if not build_skeleton.get():
            return

        # -- To reach here we need to build the skeleton
        parent = aniseed_toolkit.mutils.first_selected()

        self.user_func_create_skeleton(
            parent=parent,
            upper_twist_count=upper_twist_count.get(),
            lower_twist_count=lower_twist_count.get(),
        )

    def on_build_started(self) -> None:
        # -- Remove the guide if there is one

        guide_data = self.option("GuideData").get()
        linked_guide = guide_data["LinkedGuide"]

        if linked_guide and cmds.objExists(linked_guide):
            self.user_func_remove_guide()

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we need to remove the
        guide and bones too.
        """
        # -- Remove the guide
        self.user_func_remove_guide()

        # -- Remove the joints (re-parenting any children)
        new_parent = mref.get(self.input("Leg Root").get()).parent()
        aniseed_toolkit.joints.reparent_unknown_children(self.all_joints(), new_parent)

        # -- Now delete our leg chain and joints
        cmds.delete(self.input("Leg Root").get())

    def input_widget(self, requirement_name: str):
        """
        Return bespoke widgets for certain input types
        """
        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name: str):
        """
        Return bespoke widgets for options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

    def user_functions(self) -> typing.Dict[str, callable]:
        menu = collections.OrderedDict()

        # -- Only show the skeleton creation tools if we dont have a skeleton
        leg_joint = self.input("Leg Root").get()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        if not leg_joint or not cmds.objExists(leg_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)
            return menu

        # -- Check if we have a guide
        guide_data = self.option("GuideData").get()
        linked_guide = guide_data["LinkedGuide"]

        if linked_guide and cmds.objExists(linked_guide):
            # -- Depending on whether we have a guide or not, change what we show
            # -- in the actions menu
            menu["Remove Guide"] = functools.partial(self.user_func_remove_guide)
            menu["Toggle Joint Selectability"] = functools.partial(self.user_func_toggle_joint_selectability)
            menu["Create Mirrored Component"] = functools.partial(self.user_func_create_mirror)
        else:
            menu["Create Guide"] = functools.partial(self.user_func_create_guide)

        return menu

    def is_valid(self) -> bool:
        """
        Before building, lets check that we have all the information we require
        for building.
        """
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
        parent = aniseed_toolkit.transforms.create(
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

        config_control = aniseed_toolkit.control.create(
            description=f"{prefix}Config",
            location=location,
            parent=parent,
            shape="core_lollipop",
            config=self.config,
            match_to=leg_root,
            shape_scale=20.0,
            rotate_shape=[0, 0, 0],
        )

        cmds.addAttr(
            config_control.ctl,
            shortName="show_ik",
            attributeType='float',
            minValue=0,
            maxValue=1,
            defaultValue=1,
            keyable=True,
        )
        cmds.addAttr(
            config_control.ctl,
            shortName="show_fk",
            attributeType='float',
            minValue=0,
            maxValue=1,
            defaultValue=0,
            keyable=True,
        )
        ik_visibility_attribute = f"{config_control.ctl}.show_ik"
        fk_visibility_attribute = f"{config_control.ctl}.show_fk"

        for ik_control in ik_data["controls"]:
            ik_control = aniseed_toolkit.control.get(ik_control)
            cmds.connectAttr(
                f"{config_control.ctl}.show_ik",
                f"{ik_control.off}.visibility",
                force=True,
            )

        for fk_control in fk_data["controls"]:
            fk_control = aniseed_toolkit.control.get(fk_control)
            cmds.connectAttr(
                f"{config_control.ctl}.show_fk",
                f"{fk_control.off}.visibility",
                force=True,
            )

        deformation_joints = aniseed_toolkit.joints.get_between(
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
                cmds.rename(
                    blend_joint,
                    self.config.generate_name(
                        classification="mech",
                        description=f"{prefix}LegNK",
                        location=location,
                    )
                ),
            )
            cmds.parentConstraint(
                nk_joints[-1],
                deformation_joints[idx],
                maintainOffset=True,
            )

            cmds.scaleConstraint(
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
        joint_chain = aniseed_toolkit.joints.get_between(
            start=root_joint,
            end=tip_joint,
        )

        reference_scale = aniseed_toolkit.joints.chain_length(
            joint_chain[self.INDEX_LOWER_LEG],
            joint_chain[self.INDEX_FOOT],
        )

        fk_parent = parent

        for idx, joint in enumerate(joint_chain):
            fk_control = aniseed_toolkit.control.create(
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
        joint_chain = aniseed_toolkit.joints.get_between(
            start=root_joint,
            end=tip_joint,
        )

        # -- Create the ik spring chain that will span the whole leg
        upper_to_foot_chain = aniseed_toolkit.joints.replicate_chain(
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=parent,
        )
        upper_to_foot_chain = self._apply_mechanism_name(
            upper_to_foot_chain,
            description="FullSolve"
        )
        aniseed_toolkit.joints.move_rotations_to_orients(upper_to_foot_chain)

        upper_to_foot_ikh, _ = cmds.ikHandle(
            startJoint=upper_to_foot_chain[0],
            endEffector=upper_to_foot_chain[-1],
            solver="ikRPsolver",
            priority=1,
        )
        upper_to_foot_ikh = cmds.rename(
            self.config.generate_name(
                classification="ikh",
                description=f"{prefix}SpringSolveHandle",
                location=location,
            ),
        )
        cmds.connectAttr(
            "ikSpringSolver.message",
            f"{upper_to_foot_ikh}.ikSolver",
            force=True,
        )
        cmds.ikSpringSolverRestPose(upper_to_foot_ikh)

        # -- Create the reverse ankle chain which allows for
        # -- ankle rotation adjustment, which will follow the
        # -- movement of the three bone chain
        reverse_ankle_chain = aniseed_toolkit.joints.replicate_chain(
            from_this=joint_chain[self.INDEX_LOWER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=parent,
        )
        reverse_ankle_chain = self._apply_mechanism_name(
            reverse_ankle_chain,
            description="ReverseAnkle"
        )
        reverse_ankle_chain = aniseed_toolkit.joints.reverse_chain(reverse_ankle_chain)
        aniseed_toolkit.joints.move_rotations_to_orients(reverse_ankle_chain)

        cmds.parent(
            reverse_ankle_chain[0],
            upper_to_foot_chain[self.INDEX_LOWER_LEG],
        )

        # -- Create the upper leg two bone ik - which will follow
        # -- the ankle.
        upper_two_bone_ik = aniseed_toolkit.joints.replicate_chain(
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_LOWER_LEG],
            parent=parent,
        )
        upper_two_bone_ik = self._apply_mechanism_name(
            upper_two_bone_ik,
            description="UpperSolve"
        )
        aniseed_toolkit.joints.move_rotations_to_orients(upper_two_bone_ik)

        upper_chain_ik, _ = cmds.ikHandle(
            startJoint=upper_two_bone_ik[0],
            endEffector=upper_two_bone_ik[-1],
            solver="ikRPsolver",
            priority=1,
        )
        cmds.parent(
            upper_chain_ik,
            reverse_ankle_chain[-1],
        )

        # -- Now create the controls we will use to manipulate it all
        reference_scale = aniseed_toolkit.joints.chain_length(
            upper_to_foot_chain[self.INDEX_LOWER_LEG],
            upper_to_foot_chain[self.INDEX_FOOT],
        )

        # -- Create our main controls
        foot_control = aniseed_toolkit.control.create(
            description=prefix + "IKFoot",
            location=location,
            parent=parent,
            shape="core_paddle",
            shape_scale=reference_scale,
            rotate_shape=[0, 90, 180],
            config=self.config,
        )
        cmds.xform(
            foot_control.org,
            matrix=guide_data["Markers"]["ball"],
            worldSpace=True,
        )
        if self.option("Align Foot To World").get():
            cmds.xform(
                foot_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- Create the foot pivot setup
        foot_pivot_tip, pivot_controls = self._setup_ik_pivot_behaviour(
            foot_control=foot_control,
        )

        # -- Add the toe control
        heel_control = aniseed_toolkit.control.create(
            description=f"{prefix}Heel",
            location=location,
            parent=foot_pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=joint_chain[self.INDEX_TOE],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[90, 0, 0],
        )
        cmds.xform(
            heel_control.org,
            rotation=cmds.xform(
                foot_control.ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        # -- Add the toe control
        toe_control = aniseed_toolkit.control.create(
            description=f"{prefix}Toe",
            location=location,
            parent=foot_pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=joint_chain[self.INDEX_TOE],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[180, 0, 0],
        )
        cmds.xform(
            toe_control.org,
            rotation=cmds.xform(
                foot_control.ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        # -- Create the ankle control
        ankle_control = aniseed_toolkit.control.create(
            description=prefix + "Ankle",
            location=location,
            parent=upper_to_foot_chain[self.INDEX_LOWER_LEG],  # heel_control.ctl,
            shape="core_paddle",
            shape_scale=reference_scale,
            match_to=upper_to_foot_chain[self.INDEX_LOWER_LEG],
            config=self.config,
        )
        cmds.xform(
            ankle_control.org,
            worldSpace=True,
            translation=cmds.xform(
                upper_to_foot_chain[self.INDEX_FOOT],
                query=True,
                translation=True,
                worldSpace=True,
            ),
        )

        # -- Now we have our controls we can start to parent the IK
        # -- accordingly.
        ankle_addition_zero = self._apply_mechanism_name(
            nodes=[cmds.createNode("transform")],
            description="AnkleAdditionZero",
        )[0]
        cmds.xform(
            ankle_addition_zero,
            worldSpace=True,
            matrix=cmds.xform(
                ankle_control.ctl,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
        )
        cmds.parent(ankle_addition_zero, upper_to_foot_chain[self.INDEX_LOWER_LEG])

        ankle_addition = self._apply_mechanism_name(
            nodes=[cmds.createNode("transform")],
            description="AnkleAdditionBlend",
        )[0]
        cmds.xform(
            ankle_addition,
            worldSpace=True,
            matrix=cmds.xform(
                ankle_control.ctl,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
        )
        cmds.parent(ankle_addition, ankle_addition_zero)
        cmds.connectAttr(f"{ankle_control.ctl}.rotate", f"{ankle_addition}.rotate")
        cmds.parent(reverse_ankle_chain[0], ankle_addition)
        cmds.parent(upper_to_foot_ikh, heel_control.ctl)

        # -- Setup the polevector
        full_chain_upv = aniseed_toolkit.control.create(
            description=prefix + "Upvector",
            location=location,
            parent=foot_control.ctl,
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
        )
        cmds.xform(
            full_chain_upv.org,
            translation=aniseed_toolkit.transformation.calculate_upvector_position(
                length=1,
                *upper_two_bone_ik
            ),
            rotation=(0, 0, 0),
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
        foot_to_toe_chain = aniseed_toolkit.joints.replicate_chain(
            from_this=joint_chain[self.INDEX_FOOT],
            to_this=joint_chain[self.INDEX_TOE],
            parent=parent,
        )
        foot_to_toe_chain = self._apply_mechanism_name(
            nodes=foot_to_toe_chain,
            description="IKFootChain",
        )
        aniseed_toolkit.joints.move_rotations_to_orients(foot_to_toe_chain)

        cmds.parentConstraint(
            heel_control.ctl,
            foot_to_toe_chain[0],
            maintainOffset=True,
        )
        cmds.parentConstraint(
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

        pre_position = cmds.xform(
            check_node,
            query=True,
            translation=True,
            worldSpace=True,
        )

        cmds.poleVectorConstraint(
            polevector_target,
            ik_handle,
            weight=1,
        )

        post_position = cmds.xform(
            check_node,
            query=True,
            translation=True,
            worldSpace=True,
        )

        for idx, axis in enumerate(["X", "Y", "Z"]):
            if abs(pre_position[idx] - post_position[idx]) > 0.1:
                cmds.setAttr(f"{ik_handle}.twist", 180)
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

            pivot_control = aniseed_toolkit.control.create(
                description=f"{prefix}{description}",
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
            )

            cmds.xform(
                pivot_control.org,
                matrix=guide_data["Markers"][pivot_label],
                worldSpace=True,
            )

            parameter_pivot = aniseed_toolkit.transforms.create(
                classification="piv",
                location=self.option("Location").get(),
                description=description,
                config=self.config,
                parent=pivot_control.ctl,
                match_to=pivot_control.ctl,
            )

            # -- Add the parameter to the foot control
            cmds.addAttr(
                foot_control.ctl,
                shortName=description,
                attributeType="float",
                defaultValue=0,
                keyable=True,
            )

            cmds.connectAttr(
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
                cmds.rename(
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

        # -- Resovle the parent. The parent variable will change throughout
        # -- the course of the function but the component parent will
        # -- remain the same.
        parent = aniseed_toolkit.mutils.first_selected()
        component_parent = parent

        # -- Read our option data
        location = self.option("Location").get()

        # -- Determine if we need to build twists
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

        # -- Joint transform attributes
        joint_data = collections.OrderedDict()
        joint_data["upper"] = {"jointOrientX": 90, "jointOrientY": -20, "jointOrientZ": -90}
        joint_data["mid"] = {"tx": 42, "jointOrientZ": -50}
        joint_data["lower"] = {"tx": 42, "jointOrientZ": 50}
        joint_data["Foot"] = {"tx": 22, "jointOrientZ": 70}
        joint_data["Toe"] = {"tx": 10}

        all_joints = aniseed_toolkit.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=location,
            config=self.config,
            parent=parent,
        )
        
        # -- Set our inputs
        self.input("Leg Root").set(all_joints[0])
        self.input("Toe").set(all_joints[-1])
        upper_twists = []
        lower_twists = []

        if upper_twist_count:
            upper_twists = aniseed_toolkit.joints.create_twist_joints(
                all_joints[0],
                all_joints[1],
                upper_twist_count,
                description=self.option("Descriptive Prefix").get() + "UpperLegTwist",
                location=self.option("Location").get(),
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Upper Twist Joints").set(upper_twists)

        if lower_twist_count:
            lower_twists = aniseed_toolkit.joints.create_twist_joints(
                all_joints[1],
                all_joints[2],
                lower_twist_count,
                description=self.option("Descriptive Prefix").get() + "LowerLegTwist",
                location=self.option("Location").get(),
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Lower Twist Joints").set(lower_twists)

        # -- Immediately enter guide mode
        guides = self.user_func_create_guide()

        # -- If we have a parent, then match the translation to it, this
        # -- just makes the riggers life a little easier as the component
        # -- will show in a contextually relevant locaiton.
        aniseed_toolkit.transformation.snap_position(guides[0], component_parent)

        # -- Add our joints to a deformers set. If we're given twists, then we
        # -- use them + the foot. Otherwise we use the arm joints themselves.
        deformers = all_joints
        if upper_twist_count:
            deformers = upper_twists + lower_twists + [all_joints[-2]]
        aniseed_toolkit.sets.add_to(deformers, set_name="deformers")

    def user_func_toggle_joint_selectability(self):
        joints = self.all_joints()
        if aniseed_toolkit.joints.is_referenced(joints[0]):
            aniseed_toolkit.joints.unreference(joints)
        else:
            aniseed_toolkit.joints.make_referenced(joints)

    def user_func_create_mirror(self):
        """
        This will create a mirrored version of the component
        """
        location = self.option("Location").get()

        if location not in [self.config.left, self.config.right]:
            print("You can only mirror if the component is left or right")
            return

        # -- Get the opposite location
        location = self.config.left if location == self.config.right else self.config.right

        # -- Select the parent joint and duplicate ourselves (setting hte label so
        # -- we know its mirrored. Note that we clear the root bone as this will
        # -- trigger the duplcated component to generate the skeleton too.
        cmds.select(cmds.listRelatives(self.input("Leg Root").get(), parent=True)[0])
        mirrored_component = self.duplicate(
            input_overrides={"Leg Root": ""},
            option_overrides={"Location": location, "GuideData": self.default_guide_data()},
        )
        mirrored_component.set_label(f"{self.label()} (Mirrored)")

        # -- Get the two guides, as we need to match them
        this_guide = self.option("GuideData").get().get("LinkedGuide")
        mirrored_guide = mirrored_component.option("GuideData").get().get("LinkedGuide")

        # -- Get all the guide elements
        guides_from_this_component = aniseed_toolkit.tagging.all_children(this_guide, "guide")
        guides_from_mirrored_component = aniseed_toolkit.tagging.all_children(mirrored_guide, "guide")

        # -- Perform the match
        for guide, mirrored_guide in zip(guides_from_this_component, guides_from_mirrored_component):
            print("matching : %s to %s" % (mirrored_guide, guide))
            mref.get(mirrored_guide).match_to(mref.get(guide))

        # -- Now we do an in-place mirror
        aniseed_toolkit.mirror.global_mirror(
            transforms=guides_from_mirrored_component,
            name_replacement={},
        )

    def all_joints(self):

        # -- Get the start and end point
        root_joint = self.input("Leg Root").get()
        toe_joint = self.input("Toe").get()

        if not cmds.objExists(root_joint) or not cmds.objExists(toe_joint):
            return []

        # -- Resolve the whole chain betweenm
        leg_joints = aniseed_toolkit.joints.get_between(root_joint, toe_joint)

        # -- Include the twisters
        upper_twists = self.input("Upper Twist Joints").get()
        lower_twists = self.input("Lower Twist Joints").get()
        all_joints = leg_joints + upper_twists + lower_twists

        return [joint for joint in all_joints if joint]
    
    def user_func_create_guide(self):

        if self.has_guide():
            return []

        guide_org = mref.create("transform", name="leg_guide", parent=None)

        # -- Create the guides for the joints (replicate chain and apply ik?)
        root_joint = self.input("Leg Root").get()
        toe_joint = self.input("Toe").get()
        leg_joints = aniseed_toolkit.joints.get_between(root_joint, toe_joint)

        # -- Create the guide setup for the ik
        ik_org, guides = aniseed_toolkit.guide.create_ik_guide(
            start=leg_joints[0],
            end=leg_joints[2],
            parent=guide_org.full_name(),
            constrain_end_orientation=True,
        )

        # -- Scale the shape of the first guide (its always easier for the rigger
        # -- if the first guide of a component is larger)
        aniseed_toolkit.shapes.scale(guides[0], scale_by=1.5)

        # -- Create the foot guide
        # -- Now we need to create a guide for the foot
        foot_guide = aniseed_toolkit.guide.create(
            joint=leg_joints[-2],
            parent=guides[-1],
            link_to=guides[-1],
        )

        # -- Now we need to create a guide for the foot
        toe_guide = aniseed_toolkit.guide.create(
            joint=leg_joints[-1],
            parent=foot_guide,
            link_to=foot_guide,
        )

        # -- Ensure the twisters are tweened
        if self.input("Upper Twist Joints").get():
            aniseed_toolkit.guide.create_tweens(
                drive_these=self.input("Upper Twist Joints").get(),
                from_this=guides[0],
                to_this=guides[1],
                parent=guide_org.full_name(),
            )

        if self.input("Lower Twist Joints").get():
            aniseed_toolkit.guide.create_tweens(
                drive_these=self.input("Lower Twist Joints").get(),
                from_this=guides[1],
                to_this=guides[2],
                parent=guide_org.full_name(),
            )

        # -- Now create the guide for the foot roll pivots
        guide_base = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="gde",
            description="LegGuide",
            location=self.option("Location").get(),
            config=self.config,
            match_to=self.input("Toe").get(),
            parent=guide_org.full_name(),
        )

        # -- Constrain the position of the base in Z and X
        cmds.pointConstraint(
            foot_guide,
            guide_base,
            skip=["y"],
        )
        cmds.xform(
            guide_base,
            rotation=(0, 0, 0),
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
                parent=guide_base,
            )
            aniseed_toolkit.tagging.tag(marker, "guide")

            cmds.xform(
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
            guides.append(marker)

        # -- Store the linked guide
        guide_data["LinkedGuide"] = guide_org.name()
        self.option("GuideData").set(guide_data)

        # -- Finally make the joints unselectable
        aniseed_toolkit.joints.make_referenced(self.all_joints())

        # -- If there is a parent of the root then we constrain our
        # -- setup to that
        root_joint = mref.get(root_joint)
        if root_joint.parent():
            cmds.parentConstraint(
                root_joint.parent().full_name(),
                guide_org.full_name(),
                maintainOffset=True,
            )

        return guides

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

            guide_data["Markers"][marker_name] = cmds.xform(
                marker,
                query=True,
                matrix=True,
                worldSpace=True,
            )

        guide_data["LinkedGuide"] = None
        self.option("GuideData").set(guide_data)

        cmds.delete(linked_guide)

    @classmethod
    def default_guide_data(cls):
        return dict(
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
        )

    def has_guide(self):
        """
        Checks whether this has a valid guide or not
        """
        # -- Check if the guide already exists first
        guide_data = self.option("GuideData").get()
        guide = guide_data.get("LinkedGuide")
        if guide and cmds.objExists(guide):
            return True
        return False
