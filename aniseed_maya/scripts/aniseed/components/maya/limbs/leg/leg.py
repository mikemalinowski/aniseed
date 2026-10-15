"""
Provides the "Limb : Leg" component, an ik/fk leg rig for a four joint chain
(upper leg, lower leg, foot, toe). It builds a two bone ik with optional soft ik,
a reverse foot pivot setup with a single roll attribute, an fk chain, an nk
blend chain which drives the skeleton, ik/fk snapping and optional twist joints.
When added to the stack it can create the skeleton, foot guides and space switches.
"""
import os
import mref
import snappy
import aniseed
import functools
import collections
import aniseed_toolkit

foot = aniseed_toolkit.rigging.foot


class LegComponent(aniseed_toolkit.component.JointChainMixin, aniseed.RigComponent):
    """
    This is some documentation that the user will see. You should adjust the guides...
    """
    identifier = "Limb : Leg"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    _LABELS = [
        "Upper",
        "Lower",
        "Foot",
        "Toe",
    ]

    chain_root_input = "Leg Root"
    chain_tip_input = "Toe"
    guide_tags = foot.PIVOT_TAGS
    delete_guides_on_removal = True
    mirror_guides = True

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, leg root/toe, twist joint and foot guide inputs,
        the naming, behaviour and foot roll options (plus hidden initialisation
        options) and the blended joint, ik foot and upvector outputs.
        """
        super(LegComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Leg Root",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Toe",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Upper Twist Joints",
            description="All upper twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_input(
            name="Lower Twist Joints",
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
            value="",
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
            name="Align Paddles To Foot",
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

        self.declare_option(
            name="Upvector Distance Multiplier",
            value=1,
            group="Behaviour",
        )

        self.declare_option(
            name="Apply World Fk Switches",
            value=True,
            group="Behaviour",
        )
        self.declare_option(
            name="Apply Space Switches",
            value=True,
            group="Behaviour",
            pre_expose=True,
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

        self.declare_output(name="Blended Upper Leg")
        self.declare_output(name="Blended Lower Leg")
        self.declare_output(name="Blended Foot")
        self.declare_output(name="Blended Toe")
        self.declare_output(name="Ik Foot")
        self.declare_output(name="Upvector")

        # -- The build is broken up into functions, so these properties hold
        # -- the items which are shared between them
        self._clear_values()

    def _clear_values(self):
        """
        Resets the properties shared between the build functions to their
        empty defaults.
        """
        self.prefix: str = ""
        self.location: str = ""
        self.leg_joints: list[str] = []
        self.org: str = ""
        self.config_control = None
        self.upvector_control = None
        self.ik_root_control = None
        self.ik_foot_control = None
        self.ik_heel_control = None
        self.ik_toe_control = None
        self.ik_pivot_endpoint = ""
        self.pivot_controls = []
        self.pivot_parameters: dict[str, str] = {}

        self.fk_controls: list = []
        self.ik_controls: list = []
        self.ik_bindings: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []

        # -- Note that whilst building, the config control and twist control
        # -- shapes are rotated by this (zero) rotation
        self.shape_rotation = [0, 0, 0]

    def on_enter_stack(self):
        """
        Hides the initialisation-only options and, if Build Skeleton is set,
        creates the leg skeleton and foot guides, hooks the Parent input to a
        likely parent output and optionally sets up the space switches.
        """

        # -- Read our options
        build_skeleton = self.option("Build Skeleton")
        upper_twist_count = self.option("Upper Twist Count")
        lower_twist_count = self.option("Lower Twist Count")
        apply_spaceswitches = self.option("Apply Space Switches")

        # -- These options are only used when entering the stack, so we
        # -- hide them regardless of whether we build the skeleton
        build_skeleton.set_hidden(True)
        upper_twist_count.set_hidden(True)
        lower_twist_count.set_hidden(True)
        apply_spaceswitches.set_hidden(True)

        # -- If we do not need to build the skeleton, we can exit
        if not build_skeleton.get():
            return

        self.user_func_create_skeleton(
            upper_twist_count=upper_twist_count.get(),
            lower_twist_count=lower_twist_count.get(),
        )

        # -- Create the guides
        guides = foot.create_guides(
            description_prefix="",
            location=self.option("Location").get(),
            config=self.config,
        )
        for guide_tag, guide in guides.items():
            self.input(f"{guide_tag} Guide").set(guide)

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent(tags=["fk root", "fk hip", "hip"])

        if apply_spaceswitches.get():
            self.setup_spaceswitches()

    def input_widget(self, requirement_name):
        """
        Return bespoke widgets for certain input types
        """
        if requirement_name.endswith(" Guide"):
            return aniseed.widgets.ObjectSelector()

        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name in ["Upper Twist Joints", "Lower Twist Joints"]:
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name: str):
        """
        Return bespoke widgets for options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

        if option_name in foot.ROLL_AXIS_OPTIONS:
            return aniseed.widgets.ItemSelector(
                list(foot.ROLL_AXES),
                self.option(option_name).get(),
            )

    def run(self):
        """
        Builds the leg under a new org node: controls, foot roll, ik, the nk
        blend chain (driving the skeleton), ik/fk snapping, twists and outputs.
        """

        # -- Ensure our properties are cleared
        self._clear_values()

        # -- Determine the options we're building with
        self.prefix = self.option('Descriptive Prefix').get()
        self.location = self.option("Location").get()

        self.leg_joints = aniseed_toolkit.joints.get_between(
            start=self.input("Leg Root").get(),
            end=self.input("Toe").get(),
        )

        self.org = aniseed_toolkit.transforms.create(
            classification=self.config.organisational,
            description=f"{self.prefix}Leg",
            location=self.location,
            config=self.config,
            parent=self.input("Parent").get()
        )

        self.create_controls()
        self.create_foot_roll()
        self.create_ik()
        self.create_nk()
        self.create_snap()
        self.create_twists()
        self.set_outputs()

    def user_functions(self):
        """
        This is where we define what functionality we want to actually
        expose to the user
        """
        menu = super(LegComponent, self).user_functions()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        leg_joint = self.input("Leg Root").get()
        if not leg_joint or not mref.objExists(leg_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)
            return menu

        menu["Create Mirror"] = functools.partial(self.user_func_create_mirror)
        return menu

    def is_valid(self) -> bool:
        """
        Before building, lets check that we have all the information we require
        for building.
        """
        # -- To be valid we expect there to be specifically four joints
        all_joints = self.all_joints()

        if len(all_joints) < 4:
            print("Expected four joints for leg")
            return False

        # -- We also expect that the bones to be facing down X - at least
        # -- between the upper leg and the foot
        facing_dir = aniseed_toolkit.direction.get_chain_facing_direction(
            all_joints[0],
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

    def create_controls(self):
        """
        This function will create all the controls for the leg
        """
        # -- Add the configuration control
        self.config_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}LegConfig",
            location=self.location,
            parent=self.org,
            shape="core_floating_config",
            config=self.config,
            match_to=self.leg_joints[0],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        # -- Create the upvector control for the leg
        self.upvector_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}LegUpvector",
            location=self.location,
            parent=self.org,
            shape="core_sphere",
            config=self.config,
            match_to=self.leg_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )
        self.ik_controls.append(self.upvector_control.ctl)

        upvector_org = mref.get(self.upvector_control.org)
        upvector_org.set_position(
            aniseed_toolkit.transformation.calculate_upvector_position(
                point_a=self.leg_joints[0],
                point_b=self.leg_joints[1],
                point_c=self.leg_joints[2],
                length=self.option("Upvector Distance Multiplier").get(),
            ),
            space="world",
        )

        if self.option("Align Upvector To World").get():
            upvector_org.set_rotation([0, 0, 0], space="world")

        # -- Now create the main IK control
        self.ik_foot_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}Foot",
            location=self.location,
            parent=self.org,
            shape="core_foot_paddle",
            config=self.config,
            shape_scale=40.0,
            match_to=self.input("Ball Guide").get()
        )
        self.ik_controls.append(self.ik_foot_control.ctl)

        if self.option("Align Foot To World").get():
            mref.get(self.ik_foot_control.org).set_rotation([0, 0, 0], space="world")

        # -- Create the pivot control setup
        self.ik_pivot_endpoint, self.pivot_controls, self.pivot_parameters = foot.create_pivots(
            foot_control=self.ik_foot_control,
            guides={tag: self.input(f"{tag} Guide").get() for tag in self.guide_tags},
            prefix=self.prefix,
            location=self.location,
            config=self.config,
            prefix_separator="_",
            prefix_pivot_transforms=True,
            add_separator=True,
            match_controls_on_creation=True,
        )

        # -- Add the heel and toe controls
        self.ik_heel_control = self._create_paddle_control("Heel")
        self.ik_toe_control = self._create_paddle_control("Toe")

        fk_parent = self.org
        self.fk_controls = []

        for label, joint in zip(self._LABELS, self.leg_joints):

            fk_control = aniseed_toolkit.control.create(
                description=f"{self.prefix}{label}FK",
                location=self.location,
                parent=fk_parent,
                shape="core_rounded_square",
                config=self.config,
                match_to=joint,
                shape_scale=20.0,
                rotate_shape=[0, 0, 90],
            )
            self.fk_controls.append(fk_control.ctl)
            fk_parent = fk_control.ctl

        # -- Set up the space switches on the fk controls
        if self.option("Apply World Fk Switches").get():
            aniseed_toolkit.space.setup_fk_worldspace_switches(self.fk_controls, rig=self.rig)

    def _create_paddle_control(self, label: str):
        """
        Creates a heel or toe control at the end of the pivot chain,
        optionally aligned to the foot control
        """
        control = aniseed_toolkit.control.create(
            description=f"{self.prefix}{label}",
            location=self.location,
            parent=self.ik_pivot_endpoint,
            shape="core_half_circle",
            config=self.config,
            match_to=self.leg_joints[-1],
            shape_scale=10,
            rotate_shape=[0, 90, 0],
        )
        self.ik_controls.append(control.ctl)

        if self.option("Align Paddles To Foot").get():
            mref.get(control.org).set_rotation(
                mref.get(self.ik_foot_control.ctl).get_rotation(space="world"),
                space="world",
            )

        return control

    def create_ik(self):
        """
        This creates the IK solving for the leg
        """

        # -- Create the ik root control
        self.ik_root_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}LegIKRoot",
            location=self.location,
            shape="core_cube",
            parent=self.org,
            match_to=self.leg_joints[0],
            config=self.config,
        )

        self.ik_joints = aniseed_toolkit.rigging.ik.create_ik_chain(
            from_joint=self.leg_joints[0],
            to_joint=self.leg_joints[2],
            parent=self.ik_root_control.ctl,
            name=lambda _: self._mechanical_name("LegIK"),
        )

        # -- Create the ik handle, which moves with the heel control
        aniseed_toolkit.rigging.ik.create_rp_handle(
            start_joint=self.ik_joints[0],
            end_joint=self.ik_joints[-1],
            parent=self.ik_heel_control.ctl,
            pole_vector=self.upvector_control.ctl,
            parent_before_pole_vector=False,
        )

        # -- Create the guide line
        aniseed_toolkit.guide.link(
            self.upvector_control.ctl,
            self.ik_joints[1],
        )

        if self.option("Apply Soft Ik").get():

            root_marker = aniseed_toolkit.transforms.create(
                classification="mech",
                description=f"{self.prefix}LegIKMarker",
                location=self.location,
                config=self.config,
                parent=self.ik_root_control.ctl,
                match_to=self.ik_joints[0],
            )

            # -- Note that the tip marker retains maya's default name
            tip_marker = mref.create("transform")
            tip_marker.set_parent(self.ik_heel_control.ctl)
            tip_marker.match_to(self.ik_joints[-1])

            aniseed_toolkit.rigging.create_two_bone_soft_ik(
                root=root_marker,
                target=tip_marker.name(),
                second_joint=self.ik_joints[-2],
                third_joint=self.ik_joints[-1],
                host=self.ik_foot_control.ctl,
            )

        # -- We need to constrain the end joint in rotation to the
        # -- foot pivots, because the ik does not do that.
        mref.parentConstraint(
            self.ik_pivot_endpoint,
            self.ik_joints[-1],
            skipTranslate=['x', 'y', 'z'],
        )

        # -- These are essentially what the nk chain should map to
        self.ik_bindings = [
            self.ik_joints[0],
            self.ik_joints[1],
            self.ik_heel_control.ctl,
            self.ik_toe_control.ctl,
        ]

    def _mechanical_name(self, description: str) -> str:
        """
        Generates a mech classified name using the leg prefix and location.

        Args:
            description: Description to append to the descriptive prefix.

        Returns:
            The generated node name.
        """
        return self.config.generate_name(
            classification="mech",
            description=f"{self.prefix}{description}",
            location=self.location,
        )

    def create_nk(self):
        """
        NK is the chain that is constrained between the IK and the FK
        """
        blend_chain_setup = aniseed_toolkit.rigging.create_blend_chain(
            parent=self.org,
            transforms_a=self.ik_bindings,
            transforms_b=self.fk_controls,
            attribute_host=self.config_control.ctl,
            attribute_name="ikfk",
            match_transforms=self.leg_joints,
        )
        for blend_joint, leg_joint in zip(blend_chain_setup.blend_joints, self.leg_joints):
            blend_joint.rename(self._mechanical_name("LegNK"))
            self.nk_joints.append(blend_joint.name())

            aniseed_toolkit.constraints.parent_and_scale(
                blend_joint.name(),
                leg_joint,
            )

        aniseed_toolkit.rigging.ikfk.create_ikfk_visibility(
            f"{self.config_control.ctl}.ikfk",
            ik_controls=self.ik_controls,
            fk_controls=self.fk_controls,
        )

        # -- Move the config control under the foot nk
        config_org = mref.get(self.config_control.org)
        config_org.set_parent(self.nk_joints[-2])
        config_org.match_to(self.nk_joints[-2])
        mref.get(self.config_control.ctl).lock_attributes(["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"])

    def create_snap(self):
        """
        Snap is the mechanism for IK/FK snapping
        """
        ikfk_group, ikonly_group, fkonly_group = aniseed_toolkit.rigging.ikfk.create_snap_groups(
            label="Leg",
            prefix=self.prefix,
            location=self.location,
            ikfk_attribute=f"{self.config_control.ctl}.ikfk",
        )

        snappy.new(
            node=self.ik_foot_control.ctl,
            target=self.nk_joints[2],
            group=[ikfk_group, ikonly_group],
        )

        snappy.new(
            node=self.upvector_control.ctl,
            target=self.nk_joints[1],
            group=[ikfk_group, ikonly_group],
        )

        # -- We leave the target blank for these - which means the
        # -- controls will just get zero'd
        for pivot_control in self.pivot_controls + [self.ik_heel_control.ctl]:
            snappy.new(
                node=pivot_control,
                target=None,
                group=[ikfk_group, ikonly_group],
            )

        snappy.add_empty_members(
            nodes=[
                self.ik_foot_control.ctl,
                self.upvector_control.ctl,
                self.ik_heel_control.ctl,
                self.ik_toe_control.ctl,
            ] + self.pivot_controls,
            group=fkonly_group,
        )

        for fk_control, nk_joint in zip(self.fk_controls, self.nk_joints):
            snappy.new(
                node=fk_control,
                target=nk_joint,
                group=[ikfk_group, fkonly_group],
            )
            snappy.add_empty_members(
                nodes=[fk_control],
                group=ikonly_group,
            )

        for attribute_name in [f"{tag.lower()}_roll" for tag in self.guide_tags] + ["roll"]:
            snappy.new_forced_attribute(
                node=self.ik_foot_control.ctl,
                attribute_name=attribute_name,
                attribute_value=0,
                group=[ikfk_group, ikonly_group],
            )

    def create_foot_roll(self):
        """
        Adds a "roll" attribute to the ik foot control. Positive roll first
        rotates the heel control (lifting the heel) up to the Roll Heel Angle,
        after which the remaining roll rotates the toe pivot. Negative roll
        rocks the foot back on the heel pivot.
        """
        foot.create_roll(
            foot_control=self.ik_foot_control,
            heel_control=self.ik_heel_control,
            pivots=self.pivot_parameters,
            heel_angle=self.option("Roll Heel Angle").get(),
            heel_control_axis=self.option("Roll Heel Control Axis").get(),
            toe_pivot_axis=self.option("Roll Toe Pivot Axis").get(),
            heel_pivot_axis=self.option("Roll Heel Pivot Axis").get(),
        )

    def create_twists(self):
        """
        Adds twister setups for any upper and lower twist joints given as
        inputs, driven between the nk joints of the respective bone.
        """

        upper_twist_joints = self.input("Upper Twist Joints").get()
        lower_twist_joints = self.input("Lower Twist Joints").get()

        if upper_twist_joints:
            aniseed_toolkit.component.add_twister(
                rig=self.rig,
                joints=upper_twist_joints,
                parent=self.ik_root_control.ctl,
                root=self.nk_joints[0],
                tip=self.nk_joints[1],
                prefix=self.prefix + "LegUpperTwist",
                location=self.location,
                shape_rotation=self.shape_rotation,
            )

        if lower_twist_joints:
            aniseed_toolkit.component.add_twister(
                rig=self.rig,
                joints=lower_twist_joints,
                parent=self.nk_joints[1],
                root=self.nk_joints[1],
                tip=self.nk_joints[2],
                prefix=self.prefix + "LegLowerTwist",
                location=self.location,
                shape_rotation=self.shape_rotation,
            )

    def set_outputs(self):
        """
        Sets the Upvector and Ik Foot outputs to their controls, and the
        blended outputs to the four nk joints.
        """

        self.output("Upvector").set(self.upvector_control.ctl)
        self.output("Ik Foot").set(self.ik_foot_control.ctl)
        self.output("Blended Upper Leg").set(self.nk_joints[0])
        self.output("Blended Lower Leg").set(self.nk_joints[1])
        self.output("Blended Foot").set(self.nk_joints[2])
        self.output("Blended Toe").set(self.nk_joints[3])

    def user_func_create_skeleton(self, parent=None, upper_twist_count=None, lower_twist_count=None):
        """
        Creates a default four joint leg chain (upper leg, lower leg, foot, toe)
        plus optional upper and lower twist joints, and sets the Leg Root, Toe
        and twist joint inputs to them.

        The parent argument is ignored - the chain is always parented to (and
        positioned at) the first selected object, if any.

        Args:
            parent: Unused, overridden by the current selection.
            upper_twist_count: Number of upper leg twist joints. If None the
                user is prompted.
            lower_twist_count: Number of lower leg twist joints. If None the
                user is prompted.
        """

        # -- The skeleton is always parented to the current selection
        parent = aniseed_toolkit.mutils.first_selected()

        upper_twist_count = aniseed_toolkit.component.request_count(
            upper_twist_count,
            title="Upper Twist Count",
            message="How many twist joints do you want on the upper leg?",
        )
        lower_twist_count = aniseed_toolkit.component.request_count(
            lower_twist_count,
            title="Upper Twist Count",
            message="How many twist joints do you want on the lower leg?",
        )

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Joint transform attributes
        joint_data = collections.OrderedDict()
        joint_data["UpperLeg"] = {"jointOrientX": 90, "jointOrientY": -4, "jointOrientZ": -90}
        joint_data["LowerLeg"] = {"tx": aniseed_toolkit.units.to_cm(42), "jointOrientZ": -11}
        joint_data["Foot"] = {"tx": aniseed_toolkit.units.to_cm(42), "jointOrientZ": 55}
        joint_data["Toe"] = {"tx": aniseed_toolkit.units.to_cm(10), "jointOrientZ": 42}

        all_joints = aniseed_toolkit.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=location,
            config=self.config,
            parent=None,
            prefix=prefix,
        )

        # -- Place the leg under, and at the position of, the parent
        if parent:
            root_joint = mref.get(all_joints[0])
            root_joint.set_parent(parent)
            root_joint.set_position(
                mref.get(parent).get_position(space="world"),
                space="world",
            )

        self.input("Leg Root").set(all_joints[0])
        self.input("Toe").set(all_joints[-1])

        if upper_twist_count:
            upper_twists = aniseed_toolkit.joints.create_twist_joints(
                all_joints[0],
                all_joints[1],
                upper_twist_count,
                description=prefix + "LegUpperTwist",
                location=location,
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Upper Twist Joints").set(upper_twists)

        if lower_twist_count:
            lower_twists = aniseed_toolkit.joints.create_twist_joints(
                all_joints[1],
                all_joints[2],
                lower_twist_count,
                description=prefix + "LegLowerTwist",
                location=location,
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Lower Twist Joints").set(lower_twists)

    def setup_spaceswitches(self):
        """
        Adds space switch components for the ik foot (World/Parent, defaulting to
        World) and the upvector (World/Parent/Foot, defaulting to Foot). Skipped
        with a printed message if no "Core : Global Control Root" component is in
        the stack.
        """
        global_srt_component = self.stack.get_component_by_type("Core : Global Control Root")

        if not global_srt_component:
            print("No global srt found, skipping spaceswitch setup")
            return

        world = global_srt_component.output("Main Control").address()

        aniseed_toolkit.space.add_space_switch(
            component=self,
            label=self.label() + " Foot Space Switch",
            driven=self.output("Ik Foot").address(),
            default_space="World",
            spaces=[
                ("World", world),
                ("Parent", self.input("Parent").address()),
            ],
        )

        aniseed_toolkit.space.add_space_switch(
            component=self,
            label=self.label() + " Upvector Space Switch",
            driven=self.output("Upvector").address(),
            default_space="Foot",
            spaces=[
                ("World", world),
                ("Parent", self.input("Parent").address()),
                ("Foot", self.output("Ik Foot").address()),
            ],
        )
