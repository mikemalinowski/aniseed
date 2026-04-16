import os
import mref
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

    guide_tags = [
        "Ball",
        "Heel",
        "Toe",
        "Inner",
        "Outer",
    ]

    default_guide_transforms = {
        "Ball": {},
        "Heel": {"tz": -2, "rz": 90},
        "Toe": {"tz": 2, "rx": 180, "rz": 90},
        "Inner": {"tx": -2, "rx": 90, "rz": 90},
        "Outer": {"tx": 2, "rx": -90, "rz": 90},
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

        for guide in self.guide_tags:
            self.declare_input(
                name=f"{guide} Guide",
                description=f"Transform for the {guide} Control",
                value="",
                group="Guides",
            )

        self.declare_option(
            name="Descriptive Prefix",
            value="Leg",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value=self.config.left,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Align Foot To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Upvector Position Multiplier",
            value=1.0,
            group="Behaviour",
        )
        self.declare_option(
            name="Apply Soft Ik",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Heel And Toe To Foot",
            value=True,
            group="Behaviour",
        )

        # -- These options are hidden and for intialisation only
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Build Skeleton", value=True, pre_expose=True)

        self.declare_output("Blended Upper Leg")
        self.declare_output("Blended Mid Leg")
        self.declare_output("Blended Lower Leg")
        self.declare_output("Blended Foot", is_default=True)
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
        
        location = self.option("Location").get()

        # -- Create the guides
        for guide_tag in self.guide_tags:
            guide = cmds.createNode(
                "transform",
                name=self.config.generate_name(
                    classification="gde",
                    description=f"leg_{guide_tag}",
                    location=location,
                )
            )
            aniseed_toolkit.shapes.load_shape(guide, "core_rotator")
            self.input(f"{guide_tag} Guide").set(guide)

            # -- Set the guides default transforms
            for attribute, value in self.default_guide_transforms[guide_tag].items():
                cmds.setAttr(f"{guide}.{attribute}", value)

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent(tags=["fk root", "fk hip", "hip"])

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we need to remove the
        guide and bones too.
        """
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

        if requirement_name == "Mid Twist Joints":
            return aniseed.widgets.ObjectList()

        if requirement_name.endswith(" Guide"):
            return aniseed.widgets.ObjectSelector()

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

        menu["Create Mirror"] = self.user_func_create_mirror
        return menu

    def is_valid(self) -> bool:
        """
        Before building, lets check that we have all the information we require
        for building.
        """
        leg_root = self.input("Leg Root").get()
        toe_tip = self.input("Toe").get()

        all_joints = aniseed_toolkit.joints.get_between(
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

        facing_dir = aniseed_toolkit.direction.get_chain_facing_direction(
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
        nk_chian = self.create_nk_setup(
            parent=parent,
            ik_data=ik_data,
            fk_data=fk_data,
        )
        self.create_twists(
            nk_chain=nk_chian,
            parent=parent,
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

        blend_chain_setup = aniseed_toolkit.rigging.create_blend_chain(
            parent=parent,
            transforms_a=ik_data["blend_points"],
            transforms_b=fk_data["blend_points"],
            attribute_host=config_control.ctl,
            attribute_name="ikfk",
            match_transforms=deformation_joints,
        )

        nk_joints = []
        for idx, blend_joint in enumerate(blend_chain_setup.blend_joints):
            nk_joints.append(
                cmds.rename(
                    blend_joint.name(),
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

        return nk_joints

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

        # -- Get the chain we"re to drive
        joint_chain = aniseed_toolkit.joints.get_between(
            start=root_joint,
            end=tip_joint,
        )

        # -- Create the ik root control
        ik_root_control = aniseed_toolkit.control.create(
            description=f"{prefix}IKRoot",
            location=location,
            shape="core_cube",
            parent=parent,
            match_to=joint_chain[0],
            config=self.config,
        )

        # -- Create the ik spring chain that will span the whole leg
        upper_to_foot_chain = aniseed_toolkit.joints.replicate_chain(
            from_this=joint_chain[self.INDEX_UPPER_LEG],
            to_this=joint_chain[self.INDEX_FOOT],
            parent=ik_root_control.ctl,
        )
        n = mref.get(upper_to_foot_chain[0])
        m = n.get_matrix(space="world")
        cmds.setAttr(f"{upper_to_foot_chain[0]}.inheritsTransform", 0)
        n.set_matrix(m, space="world")

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
            parent=ik_root_control.ctl,
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
            matrix=mref.get(self.input("Ball Guide").get()).get_matrix(space="world"),
            worldSpace=True,
        )
        if self.option("Align Foot To World").get():
            cmds.xform(
                foot_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )
        lock_ankle_rotation_attr = mref.get(foot_control.ctl).add_attribute(
            "lock_ankle_rotation",
            attribute_type="float",
            value=0,
            keyable=True,
            minValue=0,
            maxValue=1,
        )

        # -- Apply the spring solve ik bias
        cmds.setAttr(f"{upper_to_foot_ikh}.springAngleBias[0].springAngleBias_Position", lock=False)
        cmds.setAttr(f"{upper_to_foot_ikh}.springAngleBias[1].springAngleBias_Position", lock=False)
        mref_control = mref.get(foot_control.ctl)
        mref_control.add_attribute(
            "ik_bias",
            value=0.5,
            attribute_type="float",
            keyable=True,
            min=0,
            max=1,
            defaultValue=0.5,
        )
        inverse_node = mref.create("reverse")
        mref_control.attr("ik_bias").connect(inverse_node.attr("inputX"))
        mref_control.attr("ik_bias").connect(f"{upper_to_foot_ikh}.springAngleBias[0].springAngleBias_FloatValue")
        inverse_node.attr("outputX").connect(f"{upper_to_foot_ikh}.springAngleBias[1].springAngleBias_FloatValue")

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
        if self.option("Align Heel And Toe To Foot").get():
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
        if self.option("Align Heel And Toe To Foot").get():
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
        cns = mref.get(
                cmds.parentConstraint(
                foot_control.ctl,
                ankle_control.ctl,
                skipRotate=["x", "y", "z"],
                maintainOffset=True,
            )[0]
        )
        cns.attr("interpType").set(0)
        controller = mref.get(ankle_control.ctl)
        for axis in ["X", "Y", "Z"]:
            controller.attr(f"translate{axis}").set(lock=True, keyable=False, channelBox=False)

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

        # -- Add a constraint on the ankle addition to optionally follow the foot control
        cmds.parentConstraint(
            foot_control.ctl,
            ankle_addition_zero,
            maintainOffset=True,
        )
        cns = mref.get(
            cmds.parentConstraint(
                upper_to_foot_chain[self.INDEX_LOWER_LEG],
                ankle_addition_zero,
                maintainOffset=True,
            )[0],
        )
        cns.attr("interpType").set(0)  # -- No Flip

        # -- Now set the blend
        reverse = mref.create("reverse")
        lock_ankle_rotation_attr.connect(reverse.attr("inputX"))
        reverse.attr("outputX").connect(cns.weight_attributes()[-1])
        lock_ankle_rotation_attr.connect(cns.weight_attributes()[0])

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
                length=self.option("Upvector Position Multiplier").get(),
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
        # -- Create the guide line
        aniseed_toolkit.guide.link(
            full_chain_upv.ctl,
            upper_to_foot_chain[1],
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


        if self.option("Apply Soft Ik").get():
            print("applying soft ik")
            root_marker = cmds.createNode(
                "transform",
                name=self.config.generate_name(
                    classification="mech",
                    description=f"{prefix}LegIKRootMarker",
                    location=location,
                )
            )

            cmds.parent(
                root_marker,
                ik_root_control.ctl,
            )

            cmds.xform(
                root_marker,
                matrix=cmds.xform(
                    upper_to_foot_chain[0],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            tip_marker = cmds.createNode(
                "transform",
                name=self.config.generate_name(
                    classification="mech",
                    description=f"{prefix}LegIKTipMarker",
                    location=location,
                )
            )

            cmds.parent(
                tip_marker,
                foot_pivot_tip,
            )

            cmds.xform(
                tip_marker,
                matrix=cmds.xform(
                    upper_to_foot_chain[-1],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )
            aniseed_toolkit.rigging.create_multi_bone_soft_ik(
                root_target=root_marker,
                end_target=tip_marker,
                root_joint=upper_to_foot_chain[0],
                end_joint=upper_to_foot_chain[-1],
                host=foot_control.ctl,
            )
            for i in [1, 2]:
                cmds.connectAttr(
                    f"{upper_to_foot_chain[i]}.translateX",
                    f"{upper_two_bone_ik[i]}.translateX",
                )

        ik_controls = pivot_controls[:]
        ik_controls.append(foot_control.ctl)
        ik_controls.append(ankle_control.ctl)
        ik_controls.append(toe_control.ctl)
        ik_controls.append(full_chain_upv.ctl)

        cmds.pointConstraint(
            ik_root_control.ctl,
            upper_to_foot_chain[0],
            maintainOffset=True,
        )
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
        pre_distance = aniseed_toolkit.transformation.distance_between(
            check_node,
            polevector_target,
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
        post_distance = aniseed_toolkit.transformation.distance_between(
            check_node,
            polevector_target,
        )

        if abs(post_distance - pre_distance) > 0.1:
            cmds.setAttr(f"{ik_handle}.twist", 180)
            print("preventing flip")

    def create_twists(self, nk_chain, parent):

        upper_twist_joints = self.input("Upper Twist Joints").get()
        mid_twist_joints = self.input("Mid Twist Joints").get()
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


        if mid_twist_joints:
            twist_component = self.rig.component_library.request("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(mid_twist_joints)
            twist_component.input("Parent").set(nk_chain[1])
            twist_component.input("Root").set(nk_chain[1])
            twist_component.input("Tip").set(nk_chain[2])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("LowerTwist")
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

        prefix = self.option("Descriptive Prefix").get()
        controls = list()

        last_parent = foot_control.ctl

        for pivot_label in self.guide_tags:
            description = f"{pivot_label.lower()}_roll"

            pivot_control = aniseed_toolkit.control.create(
                description=f"{prefix}{description}",
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",
                shape_scale=4,
                config=self.config,
            )

            cmds.xform(
                pivot_control.org,
                matrix=mref.get(self.input(f"{pivot_label} Guide").get()).get_matrix(space="world"),
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
            parent=None,
        )
        cmds.parent(all_joints[0], parent)
        
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

        # # -- If we have a parent, then match the translation to it, this
        # # -- just makes the riggers life a little easier as the component
        # # -- will show in a contextually relevant locaiton.
        aniseed_toolkit.transformation.snap_position(all_joints[0], component_parent)

    def user_func_create_mirror(self):
        aniseed_toolkit.component.mirror(
            component_instance=self,
            transforms=self.all_guides() + self.all_joints(),
            location_label="Location",
            config=self.config,
            joint_parent=mref.get(self.input("Leg Root").get()).parent().name(),
            input_overrides={"Leg Root": ""},
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
        upper_twists = self.input("Upper Twist Joints").get() or []
        lower_twists = self.input("Lower Twist Joints").get() or []
        all_joints = leg_joints + upper_twists + lower_twists

        return [joint for joint in all_joints if joint]

    def all_guides(self):
        results = []
        for guide_tag in self.guide_tags:
            results.append(self.input(f"{guide_tag} Guide").get())
        return results
