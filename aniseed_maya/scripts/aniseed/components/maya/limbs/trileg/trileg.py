"""
Provides the "Limb : Tri Leg" component, an ik/fk rig for a five joint
(three bone) leg such as a digitigrade or animal leg. The ik uses Maya's
spring solver with an ik bias, an adjustable ankle and a reverse foot pivot
setup with a roll attribute, and is blended with an fk chain into an nk chain
that drives the skeleton, with ik/fk snapping and optional twist joints.
"""
import os
import mref
import snappy
import typing
import aniseed
import functools
import collections
import aniseed_toolkit
from maya import mel

foot = aniseed_toolkit.rigging.foot

# -- The twist joint inputs which the skeleton generation creates, with the
# -- options holding how many to generate
_TRILEG_TWISTS = [
    ("Upper Twist Joints", "Upper Twist Count"),
    ("Lower Twist Joints", "Lower Twist Count"),
]

# -- The twist joint inputs which the skeleton generation never creates
_TRILEG_UNGENERATED_TWISTS = ["Mid Twist Joints", "Foot Twist Joints"]


class TriLegComponent(aniseed.RigComponent, aniseed.mixins.MirrorMixin):
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

    # -- The tags of the foot guides, each held in a "<tag> Guide" input
    guide_tags = foot.PIVOT_TAGS

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, leg root/toe, twist joint and foot guide inputs,
        the naming, behaviour and foot roll options (plus hidden initialisation
        options) and the five blended joint outputs (Blended Foot is default).
        """
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

        # -- Note that this input is not currently used in the build
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
            pre_expose=True,
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

        self.declare_option(
            name="Apply World Fk Switches",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Roll Heel Angle",
            value=30.0,
            group="Foot Roll",
            description=(
                "Degrees of positive roll applied to the heel control before "
                "the toe pivot starts to rotate. This is the starting value of "
                "the roll_heel_angle attribute on the foot control, which the "
                "animator can adjust"
            ),
        )

        self.declare_option(
            name="Roll Heel Control Axis",
            value="Positive X",
            group="Foot Roll",
            description=(
                "The axis (and direction) of the heel control which positive "
                "roll rotates first, lifting the heel"
            ),
        )

        self.declare_option(
            name="Roll Toe Pivot Axis",
            value="Positive Y",
            group="Foot Roll",
            description=(
                "The axis (and direction) of the toe pivot which positive roll "
                "rotates once the heel angle has been reached"
            ),
        )

        self.declare_option(
            name="Roll Heel Pivot Axis",
            value="Positive Y",
            group="Foot Roll",
            description=(
                "The axis (and direction) of the heel pivot which negative roll "
                "rotates, rocking the foot back onto the heel"
            ),
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
        """
        Hides the initialisation-only options and, if Build Skeleton is set,
        creates the leg skeleton and foot guides and hooks the Parent input to
        a likely parent output.
        """

        # -- Read our options
        build_skeleton = self.option("Build Skeleton")
        upper_twist_count = self.option("Upper Twist Count")
        lower_twist_count = self.option("Lower Twist Count")

        # -- These options are only used when entering the stack, so we
        # -- hide them regardless of whether we build the skeleton
        build_skeleton.set_hidden(True)
        upper_twist_count.set_hidden(True)
        lower_twist_count.set_hidden(True)

        # -- If we do not need to build the skeleton, we can exit
        if not build_skeleton.get():
            return

        self.user_func_create_skeleton(
            upper_twist_count=upper_twist_count.get(),
            lower_twist_count=lower_twist_count.get(),
        )

        # -- Create the guides
        guides = foot.create_guides(
            description_prefix="leg_",
            location=self.option("Location").get(),
            config=self.config,
        )
        for guide_tag, guide in guides.items():
            self.input(f"{guide_tag} Guide").set(guide)

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent(tags=["fk root", "fk hip", "hip"])

    def input_widget(self, requirement_name: str):
        """
        Return bespoke widgets for certain input types
        """
        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name in ["Upper Twist Joints", "Lower Twist Joints", "Mid Twist Joints"]:
            return aniseed.widgets.ObjectList()

        if requirement_name.endswith(" Guide"):
            return aniseed.widgets.ObjectSelector()

    def option_widget(self, option_name: str):
        """
        Return bespoke widgets for options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name in foot.ROLL_AXIS_OPTIONS:
            return aniseed.widgets.ItemSelector(
                list(foot.ROLL_AXES),
                self.option(option_name).get(),
            )

    def all_joints(self):
        """
        Returns all the joints this component affects: the leg root to toe
        chain followed by the upper and lower twist joints. Note that the mid
        and foot twist joints are not included.
        """
        return aniseed_toolkit.scene.joints.get_chain(
            self.input("Leg Root").get(),
            self.input("Toe").get(),
            extra_joints=(
                (self.input("Upper Twist Joints").get() or [])
                + (self.input("Lower Twist Joints").get() or [])
            ),
        )

    def all_guides(self):
        """
        Returns the foot guide transforms for this component
        """
        return [
            self.input(f"{guide_tag} Guide").get()
            for guide_tag in self.guide_tags
        ]

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we remove its joints,
        re-parenting any children which do not belong to the component. The
        foot guides are left in place.
        """
        aniseed_toolkit.scene.joints.remove_chain(
            self.input("Leg Root").get(),
            self.all_joints(),
        )

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Exposes "Create Joints" when the leg root joint is missing. Base class
        menu entries are not included. Mirroring is offered by MirrorMixin.
        """
        menu = collections.OrderedDict()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        leg_joint = self.input("Leg Root").get()
        if not leg_joint or not mref.objExists(leg_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)

        return menu

    def _mirror_joints(self) -> list:
        """
        Returns the leg root to toe chain followed by the upper, lower, mid
        and foot twist joints. Empty if the leg root or toe is missing, or the
        toe is not below the leg root.
        """
        leg_root = self.input("Leg Root").get()
        toe = self.input("Toe").get()

        if not leg_root or not toe or not mref.objExists(leg_root) or not mref.objExists(toe):
            return []

        try:
            chain = aniseed_toolkit.scene.joints.get_between(leg_root, toe)
        except ValueError:
            return []

        twist_inputs = [input_name for input_name, _ in _TRILEG_TWISTS] + _TRILEG_UNGENERATED_TWISTS

        return chain + [
            joint
            for input_name in twist_inputs
            for joint in self.input(input_name).get() or []
            if joint
        ]

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the foot guides (in guide tag order) followed by the leg root
        to toe chain and the upper, lower, mid and foot twist joints. The mid
        and foot twists come last, as the twin cannot generate them. Empty if
        there are no guides or joints.
        """
        guides = self.all_guides()
        joints = self._mirror_joints()

        if not any(guides) and not joints:
            return []

        return guides + joints

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the leg root, which is where the twin's skeleton
        is generated. Empty if there is none.
        """
        leg_root = self.input("Leg Root").get()
        if not leg_root or not mref.objExists(leg_root):
            return ""

        parent = mref.get(leg_root).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare_twin(self, source) -> None:
        """
        If the other side already has its own (unused) leg joints, the twin
        uses them, and gets foot guides of its own unless the other side has
        those too. Otherwise the twin generates its own skeleton and guides,
        with upper and lower twist counts matching the source. The skeleton
        generation does not create mid or foot twist joints, so those are
        cleared with a warning.
        """
        if self.mirror_mixin_counterparts_exist(source._mirror_joints()):
            self.option("Build Skeleton").set(False)

            if not self.mirror_mixin_counterparts_exist(source.all_guides()):
                guides = foot.create_guides(
                    description_prefix="leg_",
                    location=self.option("Location").get(),
                    config=self.config,
                )
                for guide_tag, guide in guides.items():
                    self.input(f"{guide_tag} Guide").set(guide)
            return

        self.option("Build Skeleton").set(True)

        for input_name, option_name in _TRILEG_TWISTS:
            self.option(option_name).set(len(source.input(input_name).get() or []))
            self.input(input_name).set([])

        for input_name in _TRILEG_UNGENERATED_TWISTS:
            if source.input(input_name).get():
                print(
                    f"Mirror : {source.label()} has {input_name} but they cannot be "
                    f"generated for {self.label()}. Add them to {self.label()} by hand."
                )
            self.input(input_name).set([])

        self.input("Leg Root").set("")
        self.input("Toe").set("")

        for guide_tag in self.guide_tags:
            self.input(f"{guide_tag} Guide").set("")

    def mirror_mixin_post_mirror(self, source) -> None:
        """
        Restores the creation options the twin's on_enter_stack used to the
        source's values, so the twin's data matches the source.
        """
        option_names = ["Build Skeleton"] + [option_name for _, option_name in _TRILEG_TWISTS]

        for option_name in option_names:
            self.option(option_name).set(source.option(option_name).get(resolved=False))

    def is_valid(self) -> bool:
        """
        Before building, lets check that we have all the information we require
        for building.
        """
        leg_root = self.input("Leg Root").get()
        toe_tip = self.input("Toe").get()

        all_joints = aniseed_toolkit.scene.joints.get_between(
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

        facing_dir = aniseed_toolkit.scene.joints.get_chain_facing_direction(
            leg_root,
            all_joints[2],
        )

        if facing_dir != facing_dir.NegativeX and facing_dir != facing_dir.PositiveX:
            print("The leg must be aligned to the X axis")
            return False

        for option_name in foot.ROLL_AXIS_OPTIONS:
            if self.option(option_name).get() not in foot.ROLL_AXES:
                print(f"{option_name} must be one of: {', '.join(foot.ROLL_AXES)}")
                return False

        return True

    def run(self):
        """
        Builds the tri leg under a new org node: the ik (spring solver based)
        and fk setups, the nk blend chain driving the skeleton, twists and
        ik/fk snapping. Ensures the ikSpringSolver is loaded first.
        """

        # -- Ensure the spring solver is enabled (there is no mref or cmds
        # -- equivalent of this mel procedure)
        mel.eval("ikSpringSolver()")

        # -- To encapsulate the entire rig segment, create a
        # -- parent node
        parent = aniseed_toolkit.scene.transforms.create(
            classification=self.config.organisational,
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            config=self.config,
            parent=self.input("Parent").get(),
        )

        # -- Create the IK and FK setups
        ik_data = self.create_ik_setup(parent=parent)
        fk_data = self.create_fk_setup(parent=parent)

        # -- Using the data from the ik and fk setups we
        # -- can now construct the blend setup
        nk_chain, ikfk_attribute = self.create_nk_setup(
            parent=parent,
            ik_data=ik_data,
            fk_data=fk_data,
        )
        self.create_twists(
            nk_chain=nk_chain,
            parent=parent,
        )

        self.create_snap(
            ik_data["controls"],
            fk_data["controls"],
            nk_chain,
            ikfk_attribute,
        )

    def create_nk_setup(self, parent, ik_data, fk_data):
        """
        Creates the config control and an nk blend chain between the ik and fk
        blend points (driven by the config control's ikfk attribute), constrains
        the skeleton to it, sets up ik/fk visibility and optional fk world space
        switches, and sets the blended outputs. The config control is moved
        under the foot nk joint and locked.

        Args:
            parent: The component org to build under.
            ik_data: The dict returned by create_ik_setup.
            fk_data: The dict returned by create_fk_setup.

        Returns:
            A tuple of the nk joint names and the ikfk attribute.
        """

        prefix = self.option('Descriptive Prefix').get()
        location = self.option("Location").get()

        config_control = aniseed_toolkit.rig.control.create(
            description=f"{prefix}Config",
            location=location,
            parent=parent,
            shape="core_floating_config",
            config=self.config,
            match_to=self.input("Leg Root").get(),
            shape_scale=20.0,
            rotate_shape=[0, 0, 0],
        )

        deformation_joints = aniseed_toolkit.scene.joints.get_between(
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
        for blend_joint, deformation_joint in zip(blend_chain_setup.blend_joints, deformation_joints):
            blend_joint.rename(self._mechanical_name("LegNK"))
            nk_joints.append(blend_joint.name())

            aniseed_toolkit.scene.constraints.parent_and_scale(
                blend_joint.name(),
                deformation_joint,
            )

        ikfk_attribute = mref.get(config_control.ctl).ikfk

        aniseed_toolkit.rigging.ikfk.create_ikfk_visibility(
            ikfk_attribute,
            ik_controls=ik_data["controls"],
            fk_controls=fk_data["controls"],
        )

        # -- Move the config control under the foot nk
        config_org = mref.get(config_control.org)
        config_org.set_parent(nk_joints[-2])
        config_org.match_to(nk_joints[-2])
        mref.get(config_control.ctl).lock_attributes(["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"])

        # -- Set up the space switches on the fk controls
        if self.option("Apply World Fk Switches").get():
            aniseed.builders.setup_fk_worldspace_switches(fk_data["controls"], rig=self.rig)

        self.output("Blended Upper Leg").set(nk_joints[self.INDEX_UPPER_LEG])
        self.output("Blended Mid Leg").set(nk_joints[self.INDEX_MID_LEG])
        self.output("Blended Lower Leg").set(nk_joints[self.INDEX_LOWER_LEG])
        self.output("Blended Foot").set(nk_joints[self.INDEX_FOOT])
        self.output("Blended Toe").set(nk_joints[self.INDEX_TOE])

        return nk_joints, ikfk_attribute

    def create_fk_setup(self, parent):
        """
        Creates a hierarchy of fk controls, one per leg joint, scaled relative
        to the lower leg length.

        Args:
            parent: The component org to build under.

        Returns:
            A dict with "controls" and "blend_points", both being the fk
            control list.
        """

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        fk_controls = []

        # -- Get the chain we're to drive
        joint_chain = aniseed_toolkit.scene.joints.get_between(
            start=self.input("Leg Root").get(),
            end=self.input("Toe").get(),
        )

        reference_scale = aniseed_toolkit.scene.joints.chain_length(
            joint_chain[self.INDEX_LOWER_LEG],
            joint_chain[self.INDEX_FOOT],
        )

        fk_parent = parent

        for label, joint in zip(self.LABELS, joint_chain):
            fk_control = aniseed_toolkit.rig.control.create(
                description=f"{prefix}{label}FK",
                location=location,
                parent=fk_parent,
                shape="core_rounded_square",
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
        """
        Builds the ik side of the leg: a spring solver chain spanning upper leg
        to foot, a reverse ankle chain and an upper two bone ik that follows the
        ankle, plus the foot (with ik_bias and lock_ankle_rotation attributes),
        foot pivot, heel, toe, ankle and upvector controls, the foot roll and
        optional multi-bone soft ik.

        Args:
            parent: The component org to build under.

        Returns:
            A dict with "controls" (the pivot controls followed by the foot,
            ankle, toe, heel and upvector controls - create_snap relies on
            this order) and "blend_points" (the five transforms the nk chain
            blends to).
        """

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Get the chain we're to drive
        joint_chain = aniseed_toolkit.scene.joints.get_between(
            start=self.input("Leg Root").get(),
            end=self.input("Toe").get(),
        )

        # -- Create the ik root control
        ik_root_control = aniseed_toolkit.rig.control.create(
            description=f"{prefix}IKRoot",
            location=location,
            shape="core_cube",
            parent=parent,
            match_to=joint_chain[0],
            config=self.config,
        )

        # -- Create the ik spring chain that will span the whole leg
        upper_to_foot_chain = aniseed_toolkit.rigging.ik.create_ik_chain(
            from_joint=joint_chain[self.INDEX_UPPER_LEG],
            to_joint=joint_chain[self.INDEX_FOOT],
            parent=ik_root_control.ctl,
            name=lambda _: self._mechanical_name("FullSolve"),
            root_ignores_parent=True,
        )

        upper_to_foot_ikh = aniseed_toolkit.rigging.ik.create_rp_handle(
            start_joint=upper_to_foot_chain[0],
            end_joint=upper_to_foot_chain[-1],
            hide=False,
        )
        upper_to_foot_ikh.rename(
            self.config.generate_name(
                classification="ikh",
                description=f"{prefix}SpringSolveHandle",
                location=location,
            ),
        )
        upper_to_foot_ikh = upper_to_foot_ikh.name()

        mref.get("ikSpringSolver").attr("message").connect(f"{upper_to_foot_ikh}.ikSolver", force=True)
        mref.ikSpringSolverRestPose(upper_to_foot_ikh)

        # -- Create the reverse ankle chain which allows for
        # -- ankle rotation adjustment, which will follow the
        # -- movement of the three bone chain
        reverse_ankle_chain = aniseed_toolkit.rigging.ik.create_ik_chain(
            from_joint=joint_chain[self.INDEX_LOWER_LEG],
            to_joint=joint_chain[self.INDEX_FOOT],
            parent=parent,
            name=lambda _: self._mechanical_name("ReverseAnkle"),
            move_rotations_to_orients=False,
        )
        reverse_ankle_chain = aniseed_toolkit.scene.joints.reverse_chain(reverse_ankle_chain)
        aniseed_toolkit.scene.joints.move_rotations_to_orients(reverse_ankle_chain)

        mref.get(reverse_ankle_chain[0]).set_parent(upper_to_foot_chain[self.INDEX_LOWER_LEG])

        # -- Create the upper leg two bone ik - which will follow
        # -- the ankle.
        upper_two_bone_ik = aniseed_toolkit.rigging.ik.create_ik_chain(
            from_joint=joint_chain[self.INDEX_UPPER_LEG],
            to_joint=joint_chain[self.INDEX_LOWER_LEG],
            parent=ik_root_control.ctl,
            name=lambda _: self._mechanical_name("UpperSolve"),
        )

        upper_chain_ik = aniseed_toolkit.rigging.ik.create_rp_handle(
            start_joint=upper_two_bone_ik[0],
            end_joint=upper_two_bone_ik[-1],
            parent=reverse_ankle_chain[-1],
            hide=False,
        ).name()

        # -- Now create the controls we will use to manipulate it all
        reference_scale = aniseed_toolkit.scene.joints.chain_length(
            upper_to_foot_chain[self.INDEX_LOWER_LEG],
            upper_to_foot_chain[self.INDEX_FOOT],
        )

        # -- Create our main controls. Note that controls which are not given
        # -- a match_to are left where they are created
        foot_control = aniseed_toolkit.rig.control.create(
            description=prefix + "IKFoot",
            location=location,
            parent=parent,
            shape="core_foot_paddle",
            shape_scale=reference_scale,
            rotate_shape=[0, 90, 180],
            config=self.config,
        )
        foot_org = mref.get(foot_control.org)
        foot_org.set_matrix(
            mref.get(self.input("Ball Guide").get()).get_matrix(space="world"),
            space="world",
        )
        if self.option("Align Foot To World").get():
            foot_org.set_rotation([0, 0, 0], space="world")

        foot_ctl = mref.get(foot_control.ctl)
        lock_ankle_rotation_attr = foot_ctl.add_attribute(
            "lock_ankle_rotation",
            attribute_type="float",
            value=0,
            keyable=True,
            minValue=0,
            maxValue=1,
        )

        # -- Apply the spring solve ik bias
        for index in [0, 1]:
            mref.get(f"{upper_to_foot_ikh}.springAngleBias[{index}].springAngleBias_Position").unlock()

        ik_bias_attr = foot_ctl.add_attribute(
            "ik_bias",
            value=0.5,
            attribute_type="float",
            keyable=True,
            min=0,
            max=1,
            defaultValue=0.5,
        )
        inverse_node = mref.create("reverse")
        ik_bias_attr.connect(inverse_node.inputX)
        ik_bias_attr.connect(f"{upper_to_foot_ikh}.springAngleBias[0].springAngleBias_FloatValue")
        inverse_node.outputX.connect(f"{upper_to_foot_ikh}.springAngleBias[1].springAngleBias_FloatValue")

        # -- Create the foot pivot setup
        foot_pivot_tip, pivot_controls, pivot_parameters = foot.create_pivots(
            foot_control=foot_control,
            guides={tag: self.input(f"{tag} Guide").get() for tag in self.guide_tags},
            prefix=prefix,
            location=location,
            config=self.config,
        )

        # -- Add the heel and toe controls
        heel_control = self._create_paddle_control(
            label="Heel",
            parent=foot_pivot_tip,
            match_to=joint_chain[self.INDEX_TOE],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[90, 0, 0],
            foot_control=foot_control,
        )
        toe_control = self._create_paddle_control(
            label="Toe",
            parent=foot_pivot_tip,
            match_to=joint_chain[self.INDEX_TOE],
            shape_scale=reference_scale / 3.0,
            rotate_shape=[180, 0, 0],
            foot_control=foot_control,
        )

        # -- Drive the heel control and the toe / heel pivots from a
        # -- single roll attribute on the foot control
        foot.create_roll(
            foot_control=foot_control,
            heel_control=heel_control,
            pivots=pivot_parameters,
            heel_angle=self.option("Roll Heel Angle").get(),
            heel_control_axis=self.option("Roll Heel Control Axis").get(),
            toe_pivot_axis=self.option("Roll Toe Pivot Axis").get(),
            heel_pivot_axis=self.option("Roll Heel Pivot Axis").get(),
        )

        # -- Create the ankle control
        ankle_control = aniseed_toolkit.rig.control.create(
            description=prefix + "Ankle",
            location=location,
            parent=heel_control.ctl,
            shape="core_circle",
            shape_scale=reference_scale,
            match_to=upper_to_foot_chain[self.INDEX_LOWER_LEG],
            config=self.config,
        )
        mref.get(ankle_control.org).set_position(
            mref.get(upper_to_foot_chain[self.INDEX_FOOT]).get_position(space="world"),
            space="world",
        )

        # -- The ankle addition zero optionally follows the foot control
        # -- or the ankle of the spring solve, based on the lock ankle
        # -- rotation attribute
        ankle_addition_zero = self._create_mechanical_transform(
            description="AnkleAdditionZero",
            matrix=mref.get(ankle_control.ctl).get_matrix(space="world"),
        )
        ankle_addition_zero.set_parent(heel_control.ctl)

        mref.parentConstraint(
            foot_control.ctl,
            ankle_addition_zero,
            maintainOffset=True,
        )
        constraint = mref.parentConstraint(
            upper_to_foot_chain[self.INDEX_LOWER_LEG],
            ankle_addition_zero,
            maintainOffset=True,
        )[0]
        constraint.attr("interpType").set(2)  # -- Shortest

        reverse = mref.create("reverse")
        lock_ankle_rotation_attr.connect(reverse.inputX)
        reverse.outputX.connect(constraint.weight_attributes()[-1])
        lock_ankle_rotation_attr.connect(constraint.weight_attributes()[0])

        # -- Only the rotation is constrained
        for axis in ["X", "Y", "Z"]:
            translate = ankle_addition_zero.attr(f"translate{axis}")
            translate.inputs()[0].disconnect(translate)

        ankle_addition = self._create_mechanical_transform(
            description="AnkleAdditionBlend",
            matrix=mref.get(ankle_control.ctl).get_matrix(space="world"),
        )
        ankle_addition.set_parent(ankle_addition_zero)
        mref.get(ankle_control.ctl).attr("rotate").connect(ankle_addition.attr("rotate"))
        mref.get(reverse_ankle_chain[0]).set_parent(ankle_addition)
        mref.get(upper_to_foot_ikh).set_parent(heel_control.ctl)

        # -- Setup the polevector
        full_chain_upv = aniseed_toolkit.rig.control.create(
            description=prefix + "Upvector",
            location=location,
            parent=foot_control.ctl,
            shape="core_sphere",
            shape_scale=reference_scale / 10.0,
            config=self.config,
        )
        mref.xform(
            full_chain_upv.org,
            translation=aniseed_toolkit.core.maths.calculate_upvector_position(
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
        aniseed_toolkit.rig.guide.link(
            full_chain_upv.ctl,
            upper_to_foot_chain[1],
        )

        # -- Create the foot/toe chain
        foot_to_toe_chain = aniseed_toolkit.rigging.ik.create_ik_chain(
            from_joint=joint_chain[self.INDEX_FOOT],
            to_joint=joint_chain[self.INDEX_TOE],
            parent=parent,
            name=lambda _: self._mechanical_name("IKFootChain"),
        )

        mref.parentConstraint(
            heel_control.ctl,
            foot_to_toe_chain[0],
            maintainOffset=True,
        )
        mref.parentConstraint(
            toe_control.ctl,
            foot_to_toe_chain[-1],
            maintainOffset=True,
        )

        if self.option("Apply Soft Ik").get():
            root_marker = aniseed_toolkit.scene.transforms.create(
                classification="mech",
                description=f"{prefix}LegIKRootMarker",
                location=location,
                config=self.config,
                parent=ik_root_control.ctl,
                match_to=upper_to_foot_chain[0],
            )

            tip_marker = aniseed_toolkit.scene.transforms.create(
                classification="mech",
                description=f"{prefix}LegIKTipMarker",
                location=location,
                config=self.config,
                parent=foot_pivot_tip,
                match_to=upper_to_foot_chain[-1],
            )

            aniseed_toolkit.rigging.create_multi_bone_soft_ik(
                root_target=root_marker,
                end_target=tip_marker,
                root_joint=upper_to_foot_chain[0],
                end_joint=upper_to_foot_chain[-1],
                host=foot_control.ctl,
            )

            # -- The upper solve follows the lengths of the soft ik chain
            for i in [1, 2]:
                mref.get(upper_to_foot_chain[i]).translateX.connect(
                    f"{upper_two_bone_ik[i]}.translateX",
                )

        ik_controls = pivot_controls[:]
        ik_controls.append(foot_control.ctl)
        ik_controls.append(ankle_control.ctl)
        ik_controls.append(toe_control.ctl)
        ik_controls.append(heel_control.ctl)
        ik_controls.append(full_chain_upv.ctl)

        mref.pointConstraint(
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

    def _create_paddle_control(self, label, parent, match_to, shape_scale, rotate_shape, foot_control):
        """
        Creates a heel or toe control at the end of the pivot chain,
        optionally aligned to the foot control
        """
        control = aniseed_toolkit.rig.control.create(
            description=f"{self.option('Descriptive Prefix').get()}{label}",
            location=self.option("Location").get(),
            parent=parent,
            shape="core_half_circle",
            config=self.config,
            match_to=match_to,
            shape_scale=shape_scale,
            rotate_shape=rotate_shape,
        )
        if self.option("Align Heel And Toe To Foot").get():
            mref.get(control.org).set_rotation(
                mref.get(foot_control.ctl).get_rotation(space="world"),
                space="world",
            )
        return control

    def _create_mechanical_transform(self, description, matrix) -> mref.ReferencedItem:
        """
        Creates a mechanical transform (at the world root) with the given
        world matrix
        """
        node = mref.create("transform")
        node.rename(self._mechanical_name(description))
        node.set_matrix(matrix, space="world")
        return node

    def _mechanical_name(self, description: str) -> str:
        """
        Generates a mech classified name using the descriptive prefix and
        location options.

        Args:
            description: Description to append to the descriptive prefix.

        Returns:
            The generated node name.
        """
        return self.config.generate_name(
            classification="mech",
            description=f"{self.option('Descriptive Prefix').get()}{description}",
            location=self.option("Location").get(),
        )

    @staticmethod
    def non_flip_polevector(ik_handle, polevector_target, check_node):
        """
        Applies a pole vector constraint, and if doing so moves the check
        node then the ik handle is twisted by 180 degrees to counter it.
        """
        pre_distance = aniseed_toolkit.core.maths.distance_between(
            check_node,
            polevector_target,
        )

        mref.poleVectorConstraint(
            polevector_target,
            ik_handle,
            weight=1,
        )

        post_distance = aniseed_toolkit.core.maths.distance_between(
            check_node,
            polevector_target,
        )

        if abs(post_distance - pre_distance) > 0.1:
            mref.get(ik_handle).attr("twist").set(180)

    def create_twists(self, nk_chain, parent):
        """
        Adds twister setups for any upper, mid and lower twist joints given as
        inputs, each driven between consecutive nk joints. The Foot Twist
        Joints input is not used.

        Args:
            nk_chain: The nk (blended) joints of the leg.
            parent: The component org, used as the parent of the upper twist.
        """

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        twist_setups = [
            ("Upper Twist Joints", parent, nk_chain[0], nk_chain[1], "LegUpperTwist"),
            ("Mid Twist Joints", nk_chain[1], nk_chain[1], nk_chain[2], "LegMidTwist"),
            ("Lower Twist Joints", nk_chain[2], nk_chain[2], nk_chain[3], "LegLowerTwist"),
        ]

        for input_name, twist_parent, root, tip, description in twist_setups:
            twist_joints = self.input(input_name).get()
            if not twist_joints:
                continue

            aniseed.builders.add_twister(
                rig=self.rig,
                joints=twist_joints,
                parent=twist_parent,
                root=root,
                tip=tip,
                prefix=prefix + description,
                location=location,
            )

    def user_func_create_skeleton(
            self,
            parent=None,
            upper_twist_count=None,
            lower_twist_count=None,
    ):
        """
        Creates a default five joint leg chain (upper, mid, lower, foot, toe)
        plus optional twist joints, and sets the Leg Root, Toe and twist joint
        inputs to them. Note that the lower twist joints are created between
        the mid and lower joints.

        The parent argument is ignored - the chain is always parented to the
        first selected object (if any), and the root is then snapped to it
        (the snap is called even when nothing is selected).

        Args:
            parent: Unused, overridden by the current selection.
            upper_twist_count: Number of upper leg twist joints. If None the
                user is prompted.
            lower_twist_count: Number of lower leg twist joints. If None the
                user is prompted.
        """

        # -- The skeleton is always placed under the current selection
        parent = aniseed_toolkit.core.selection.first_selected()

        # -- Read our option data
        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Determine if we need to build twists
        upper_twist_count = aniseed.dialogs.request_count(
            upper_twist_count,
            title="Upper Twist Count",
            message="How many twist joints do you want on the upper leg?",
        )
        lower_twist_count = aniseed.dialogs.request_count(
            lower_twist_count,
            title="Upper Twist Count",
            message="How many twist joints do you want on the lower leg?",
        )

        # -- Joint transform attributes
        joint_data = collections.OrderedDict()
        joint_data["upper"] = {"jointOrientX": 90, "jointOrientY": -20, "jointOrientZ": -90}
        joint_data["mid"] = {"tx": aniseed_toolkit.core.units.from_cm(42), "jointOrientZ": -50}
        joint_data["lower"] = {"tx": aniseed_toolkit.core.units.from_cm(42), "jointOrientZ": 50}
        joint_data["Foot"] = {"tx": aniseed_toolkit.core.units.from_cm(22), "jointOrientZ": 70}
        joint_data["Toe"] = {"tx": aniseed_toolkit.core.units.from_cm(10)}

        all_joints = aniseed_toolkit.scene.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=location,
            config=self.config,
            parent=None,
            prefix=prefix,
        )
        if parent:
            mref.get(all_joints[0]).set_parent(parent)

        # -- Set our inputs
        self.input("Leg Root").set(all_joints[0])
        self.input("Toe").set(all_joints[-1])

        if upper_twist_count:
            upper_twists = aniseed_toolkit.scene.joints.create_twist_joints(
                all_joints[0],
                all_joints[1],
                upper_twist_count,
                description=prefix + "UpperLegTwist",
                location=location,
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Upper Twist Joints").set(upper_twists)

        if lower_twist_count:
            lower_twists = aniseed_toolkit.scene.joints.create_twist_joints(
                all_joints[1],
                all_joints[2],
                lower_twist_count,
                description=prefix + "LowerLegTwist",
                location=location,
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Lower Twist Joints").set(lower_twists)

        # -- If we have a parent, then match the translation to it, this
        # -- just makes the riggers life a little easier as the component
        # -- will show in a contextually relevant location.
        aniseed_toolkit.scene.transforms.snap_position(all_joints[0], parent)

    def create_snap(self, ik_controls, fk_controls, nk_joints, ikfk_attribute):
        """
        Snap is the mechanism for IK/FK snapping
        """
        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        ik_foot_control = ik_controls[-5]
        ankle_control = ik_controls[-4]
        toe_control = ik_controls[-3]
        heel_control = ik_controls[-2]
        upvector_control = ik_controls[-1]

        # -- Note that this slice includes the foot control
        pivot_controls = ik_controls[:-4]

        ankle_marker = mref.create("transform", parent=nk_joints[-3], name="ankle_marker")
        ankle_marker.set_matrix(mref.get(ankle_control).get_matrix(space="world"), space="world")

        ikfk_group, ikonly_group, fkonly_group = aniseed_toolkit.rigging.ikfk.create_snap_groups(
            label="TriLeg",
            prefix=prefix,
            location=location,
            ikfk_attribute=ikfk_attribute.name(include_node=True),
        )

        snappy.new(
            node=ik_foot_control,
            target=nk_joints[-2],
            group=[ikfk_group, ikonly_group],
        )

        snappy.new(
            node=upvector_control,
            target=nk_joints[1],
            group=[ikfk_group, ikonly_group],
        )

        snappy.new(
            node=ankle_control,
            target=ankle_marker.name(),
            group=[ikfk_group, ikonly_group],
        )

        snappy.new(
            node=toe_control,
            target=nk_joints[-1],
            group=[ikfk_group, ikonly_group],
        )

        # -- We leave the target blank for these - which means the
        # -- controls will just get zero'd
        for control in [heel_control] + pivot_controls:
            snappy.new(
                node=control,
                target=None,
                group=[ikfk_group, ikonly_group],
            )

        for fk_control, nk_joint in zip(fk_controls, nk_joints):
            snappy.new(
                node=fk_control,
                target=nk_joint,
                group=[ikfk_group, fkonly_group],
            )
            snappy.add_empty_members(
                nodes=[fk_control],
                group=ikonly_group,
            )

        forced_attributes = [(f"{tag.lower()}_roll", 0) for tag in self.guide_tags]
        forced_attributes += [("roll", 0), ("lock_ankle_rotation", 1)]
        forced_attributes += [(f"Joint{i}Addition", 0) for i in range(3)]

        for attribute_name, attribute_value in forced_attributes:
            snappy.new_forced_attribute(
                node=ik_foot_control,
                attribute_name=attribute_name,
                attribute_value=attribute_value,
                group=[ikfk_group, ikonly_group],
            )

        for nodes in [ik_controls, fk_controls]:
            for group in [ikonly_group, fkonly_group]:
                snappy.add_empty_members(
                    nodes=nodes,
                    group=group,
                )
