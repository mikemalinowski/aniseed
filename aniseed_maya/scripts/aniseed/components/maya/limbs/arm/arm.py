"""
Provides the "Limb : Arm" component, which builds a shoulder control and a
blended two bone ik/fk arm (with optional soft ik) driven from shoulder and
hand joint inputs. It also adds ik/fk snapping, optional upper and lower twist
setups, world fk switches and space switches for the ik hand and upvector, and
can generate the arm skeleton when added to the stack.
"""
import os
import mref
import snappy
import typing
import aniseed
import functools
import collections
import aniseed_toolkit


# -- The twist joint inputs, with the options holding how many to generate
_ARM_TWISTS = [
    ("Upper Twist Joints", "Upper Twist Count"),
    ("Lower Twist Joints", "Lower Twist Count"),
]


class ArmComponent(aniseed.RigComponent, aniseed.mixins.MirrorMixin):

    identifier = "Limb : Arm"
    icon = os.path.join(
        os.path.dirname(__file__),
        "arm.png",
    )

    # noinspection PyUnresolvedReferences
    def __init__(self, *args, **kwargs):
        """
        Declares the parent, shoulder and hand inputs along with the optional
        upper and lower twist joint lists, the naming and behaviour options
        (alignment, soft ik, space switches) and the skeleton generation
        options. Outputs expose the blended arm joints, the ik hand,
        upvector and shoulder controls.
        """
        super(ArmComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Shoulder",
            description="The root of the spine",
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Hand",
            description="The tip of the spine",
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Upper Twist Joints",
            description="All upper twist joints",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_input(
            name="Lower Twist Joints",
            description="All lower twist joints",
            validate=False,
            group="Twist Configuration",
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
            name="Align Shoulder To World",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Hand To World",
            value=False,
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

        # -- Declare our options which make it easier and quicker to generate
        # -- a skeleton if needed
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Build Skeleton", value=True, pre_expose=True)

        # -- Declare our outputs so other components can access them
        self.declare_output(
            name="Blended Upper Arm",
        )

        self.declare_output(
            name="Blended Lower Arm",
        )

        self.declare_output(
            name="Blended Hand",
            is_default=True,
        )

        self.declare_output("Upvector")
        self.declare_output("Ik Hand")
        self.declare_output("Shoulder")

        # -- The build is broken up into functions, so these properties hold
        # -- the items which are shared between them
        self._clear_values()

    def _clear_values(self):
        """
        Resets the build properties (controls, joint lists, prefix, location
        etc) which are shared between the build functions, so that each run
        starts from a clean state.
        """
        self.prefix: str = ""
        self.location: str = ""
        self.org: str = ""
        self.arm_joints: list[str] = []
        self.shoulder_control: "Control" = None
        self.config_control: "Control" = None
        self.upvector_control: "Control" = None
        self.ik_hand_control: "Control" = None
        self.fk_upper_control: "Control" = None
        self.fk_lower_control: "Control" = None
        self.fk_hand_control: "Control" = None

        self.fk_controls: list[str] = []
        self.ik_controls: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [0, 0, 90]

    def on_enter_stack(self):
        """
        When this enters the stack we can build the skeleton structure
        automatically if requested.
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
            parent=aniseed_toolkit.core.selection.first_selected(),
            upper_twist_count=upper_twist_count.get(),
            lower_twist_count=lower_twist_count.get(),
        )

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent(tags=["fk tip", "chest", "tip"])

        if apply_spaceswitches.get():
            self.setup_spaceswitches()

    def option_widget(self, option_name: str):
        """
        This allows us to provide dedicate widgets for specific options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config, self.option(option_name).get())

    def input_widget(self, requirement_name):
        """
        This allows us to provide dedicate widgets for specific inputs
        """
        if requirement_name in ["Parent", "Shoulder", "Hand"]:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name in ["Upper Twist Joints", "Lower Twist Joints"]:
            return aniseed.widgets.ObjectList()

    def all_joints(self):
        """
        Returns all the joints this component affects: the shoulder to hand
        chain followed by the upper and lower twist joints.
        """
        return aniseed_toolkit.scene.joints.get_chain(
            self.input("Shoulder").get(),
            self.input("Hand").get(),
            extra_joints=(
                (self.input("Upper Twist Joints").get() or [])
                + (self.input("Lower Twist Joints").get() or [])
            ),
        )

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we remove its joints,
        re-parenting any children which do not belong to the component.
        """
        aniseed_toolkit.scene.joints.remove_chain(
            self.input("Shoulder").get(),
            self.all_joints(),
        )

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        These are functions that will be exposed to the user if they
        right click the component. Mirroring is offered by MirrorMixin.
        """
        menu = super(ArmComponent, self).user_functions()
        shoulder_joint = self.input("Shoulder").get()

        # -- If there is no shoulder joint we expose the option
        # -- to allow the user to have one generated
        if not shoulder_joint or not mref.objExists(shoulder_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)

        return menu

    def _mirror_arm_chain(self) -> list:
        """
        Returns the shoulder to hand joints, or an empty list if either is
        missing or the hand is not below the shoulder.
        """
        shoulder = self.input("Shoulder").get()
        hand = self.input("Hand").get()

        if not shoulder or not hand or not mref.objExists(shoulder) or not mref.objExists(hand):
            return []

        try:
            return aniseed_toolkit.scene.joints.get_between(shoulder, hand)
        except ValueError:
            return []

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the shoulder to hand chain followed by the upper and then the
        lower twist joints. Empty if the shoulder or hand is missing.
        """
        chain = self._mirror_arm_chain()
        if not chain:
            return []

        return chain + [
            joint
            for input_name in ["Upper Twist Joints", "Lower Twist Joints"]
            for joint in self.input(input_name).get() or []
            if joint
        ]

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the shoulder joint, which is where the twin's
        skeleton is generated. Empty if there is none.
        """
        shoulder = self.input("Shoulder").get()
        if not shoulder or not mref.objExists(shoulder):
            return ""

        parent = mref.get(shoulder).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare_twin(self, source) -> None:
        """
        If the other side already has its own (unused) arm joints, the twin
        uses them. Otherwise the twin generates its own skeleton, with twist
        counts matching the source. Either way the space switches are not
        created again, as the source's are mirrored with the subtree.
        """
        self.option("Apply Space Switches").set(False)

        if self.mirror_mixin_counterparts_exist(source.mirror_mixin_items_to_mirror()):
            self.option("Build Skeleton").set(False)
            return

        self.option("Build Skeleton").set(True)

        for input_name, option_name in _ARM_TWISTS:
            self.option(option_name).set(len(source.input(input_name).get() or []))
            self.input(input_name).set([])

        self.input("Shoulder").set("")
        self.input("Hand").set("")

    def mirror_mixin_post_mirror(self, source) -> None:
        """
        Restores the creation options the twin's on_enter_stack used to the
        source's values, so the twin's data matches the source.
        """
        option_names = ["Build Skeleton", "Apply Space Switches"]
        option_names += [option_name for _, option_name in _ARM_TWISTS]

        for option_name in option_names:
            self.option(option_name).set(source.option(option_name).get(resolved=False))

    def is_valid(self):
        """
        This gives us the chance to validate the skeleton
        before we commit to building.
        """
        arm_joints = aniseed_toolkit.scene.joints.get_between(
            self.input("Shoulder").get(),
            self.input("Hand").get(),
        )[1:]

        direction = aniseed_toolkit.scene.joints.get_chain_facing_direction(
            arm_joints[0],
            arm_joints[-1],
        )

        if direction != direction.PositiveX and direction != direction.NegativeX:
            print("Validation Warning : Chain is not failing Up/Down X")
            print(f"    Tested Chain : {arm_joints}")
            print(direction)
            return False

        return True

    def run(self):
        """
        This is triggered when the stack is executed
        """
        self._clear_values()
        self.prefix = self.option('Descriptive Prefix').get()
        self.location = self.option("Location").get()

        self.org = aniseed_toolkit.scene.transforms.create(
            classification=self.config.organisational,
            description=f"{self.prefix}Arm",
            location=self.location,
            config=self.config,
            parent=self.input("Parent").get(),
            match_to=self.input("Parent").get()
        )
        self.arm_joints = aniseed_toolkit.scene.joints.get_between(
            start=self.input('Shoulder').get(),
            end=self.input("Hand").get(),
        )
        self._create_controls()

        ikfk_setup = aniseed_toolkit.rigging.create_two_bone_ikfk(
            parent=self.shoulder_control.ctl,
            root_joint=self.arm_joints[1],
            end_joint=self.arm_joints[-1],
            attribute_host=self.config_control.ctl,
            attribute_name="ikfk",
            constrain=True,
            soft_ik=self.option("Apply Soft Ik").get(),
            soft_ik_host=self.ik_hand_control.ctl,
        )

        # -- Move the config control under the end of the blend chain
        config_org = mref.get(self.config_control.org)
        config_org.set_parent(ikfk_setup.blend_chain[-1])
        config_org.match_to(ikfk_setup.blend_chain[-1])
        mref.get(self.config_control.ctl).lock_transform_attributes(hide=True)

        # -- Create the guide line
        aniseed_toolkit.rig.guide.link(
            self.upvector_control.ctl,
            ikfk_setup.ik_chain[1].name(),
        )

        for node in ikfk_setup.all_nodes():
            node.rename(
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}Arm{node.name()}",
                    location=self.location,
                ),
            )

        mref.parentConstraint(
            self.ik_hand_control.ctl,
            ikfk_setup.ik_target,
            maintainOffset=True,
        )
        mref.parentConstraint(
            self.upvector_control.ctl,
            ikfk_setup.ik_upvector,
            maintainOffset=False,
        )

        for fk_control, fk_marker in zip(self.fk_controls, ikfk_setup.fk_chain):
            mref.parentConstraint(
                fk_control,
                fk_marker,
                maintainOffset=True,
            )

        aniseed_toolkit.rigging.ikfk.create_ikfk_visibility(
            f"{self.config_control.ctl}.ikfk",
            ik_controls=self.ik_controls,
            fk_controls=self.fk_controls,
        )

        # -- Set up the space switches on the fk controls
        if self.option("Apply World Fk Switches").get():
            aniseed.builders.setup_fk_worldspace_switches([self.shoulder_control.ctl] + self.fk_controls, rig=self.rig)

        self.nk_joints = ikfk_setup.blend_chain.names()
        self._create_snap()
        self._create_twist_setup()
        self._set_outputs()

    def _create_controls(self):
        """
        Here we create all the controls for the arm
        """
        self.shoulder_control = aniseed_toolkit.rig.control.create(
            description=f"{self.prefix}Shoulder",
            location=self.location,
            parent=self.org,
            shape="core_half_circle",
            config=self.config,
            match_to=self.arm_joints[0],
            shape_scale=5.0,
            rotate_shape=None,
        )

        if self.option("Align Shoulder To World").get():
            mref.get(self.shoulder_control.org).set_rotation([0, 0, 0], space="world")

        # -- Add the configuration control
        self.config_control = aniseed_toolkit.rig.control.create(
            description=f"{self.prefix}ArmConfig",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_floating_config",
            config=self.config,
            match_to=self.arm_joints[0],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        aniseed_toolkit.scene.constraints.parent_and_scale(
            self.shoulder_control.ctl,
            self.arm_joints[0],
        )

        # -- Create the fk controls, each one parented under the last
        fk_parent = self.shoulder_control.ctl
        fk_controls = []
        for label, joint in zip(["UpperArmFK", "LowerArmFK", "HandFK"], self.arm_joints[1:4]):
            fk_control = aniseed_toolkit.rig.control.create(
                description=f"{self.prefix}{label}",
                location=self.location,
                parent=fk_parent,
                shape="core_rounded_square",
                config=self.config,
                match_to=joint,
                shape_scale=20.0,
                rotate_shape=self.shape_rotation,
            )
            fk_controls.append(fk_control)
            fk_parent = fk_control.ctl

        self.fk_upper_control, self.fk_lower_control, self.fk_hand_control = fk_controls
        self.fk_controls = [fk_control.ctl for fk_control in fk_controls]

        # -- Now create the main IK control
        self.ik_hand_control = aniseed_toolkit.rig.control.create(
            description=f"{self.prefix}Hand",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_stumpy_cross",
            config=self.config,
            match_to=self.arm_joints[-1],
            shape_scale=20.0,
            rotate_shape=[-90, 0 ,0],
        )
        self.ik_controls.append(self.ik_hand_control.ctl)

        if self.option("Align Hand To World").get():
            mref.get(self.ik_hand_control.org).set_rotation([0, 0, 0], space="world")

        # -- Create the upvector control for the arm
        self.upvector_control = aniseed_toolkit.rig.control.create(
            description=f"{self.prefix}ArmUpvector",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_sphere",
            config=self.config,
            match_to=self.arm_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )
        self.ik_controls.append(self.upvector_control.ctl)

        upvector_org = mref.get(self.upvector_control.org)
        upvector_org.set_position(
            aniseed_toolkit.core.maths.calculate_upvector_position(
                point_a=self.arm_joints[1],
                point_b=self.arm_joints[2],
                point_c=self.arm_joints[3],
                length=1,
            ),
            space="world",
        )
        if self.option("Align Upvector To World").get():
            upvector_org.set_rotation([0, 0, 0], space="world")

    def _create_snap(self):
        """
        Creates the snappy ikfk, ik only and fk only snap groups for the arm.
        The ik hand and upvector controls snap to the blended joints, as do
        the fk controls, and each control set is added as empty members to
        the opposing "only" group.
        """
        ikfk_group, ikonly_group, fkonly_group = aniseed_toolkit.rigging.ikfk.create_snap_groups(
            label="Arm",
            prefix=self.prefix,
            location=self.location,
            ikfk_attribute=f"{self.config_control.ctl}.ikfk",
        )

        snappy.new(
            node=self.ik_hand_control.ctl,
            target=self.nk_joints[2],
            group=[ikfk_group, ikonly_group],
        )

        snappy.new(
            node=self.upvector_control.ctl,
            target=self.nk_joints[1],
            group=[ikfk_group, ikonly_group],
        )

        for fk_control, nk_joint in zip(self.fk_controls, self.nk_joints):
            snappy.new(
                node=fk_control,
                target=nk_joint,
                group=[ikfk_group, fkonly_group],
            )

        snappy.add_empty_members(
            nodes=self.fk_controls,
            group=ikonly_group,
        )
        snappy.add_empty_members(
            nodes=[
                self.ik_hand_control.ctl,
                self.upvector_control.ctl,
            ],
            group=fkonly_group,
        )

    def _create_twist_setup(self):
        """
        Creates a rotator half way between the upper and lower blended arm
        joints (to prevent flips when the elbow bends a lot) and then adds
        twisters for the upper and lower twist joints if any are given. The
        upper twist uses the rotator as its tip.
        """

        upper_twist_joints = self.input("Upper Twist Joints").get()
        lower_twist_joints = self.input("Lower Twist Joints").get()

        # -- To prevent flips as the elbow bends a lot, we blend the tip half way between the
        # -- two arm bones
        rotator = aniseed_toolkit.rigging.create_rotator(
            target_a=self.nk_joints[0],
            target_b=self.nk_joints[1],
            match_to=self.nk_joints[1],
            parent=self.nk_joints[1],
            description="foo",
            location=self.location,
            config=self.config,
        )

        if upper_twist_joints:
            aniseed.builders.add_twister(
                rig=self.rig,
                joints=upper_twist_joints,
                parent=self.shoulder_control.ctl,
                root=self.nk_joints[0],
                tip=rotator,
                prefix="UpperTwist",
                location=self.location,
                shape_rotation=self.shape_rotation,
            )

        if lower_twist_joints:
            aniseed.builders.add_twister(
                rig=self.rig,
                joints=lower_twist_joints,
                parent=self.nk_joints[1],
                root=self.nk_joints[1],
                tip=self.nk_joints[2],
                prefix="LowerTwist",
                location=self.location,
                shape_rotation=self.shape_rotation,
            )

    def _set_outputs(self):
        """
        Sets the upvector, ik hand and shoulder control outputs along with
        the blended upper arm, lower arm and hand joint outputs.
        """

        self.output("Upvector").set(self.upvector_control.ctl)
        self.output("Ik Hand").set(self.ik_hand_control.ctl)

        self.output("Blended Upper Arm").set(self.nk_joints[0])
        self.output("Blended Lower Arm").set(self.nk_joints[1])
        self.output("Blended Hand").set(self.nk_joints[2])
        self.output("Shoulder").set(self.shoulder_control.ctl)

    def user_func_create_skeleton(self, parent=None, upper_twist_count=None, lower_twist_count=None):
        """
        This will create a skeleton structure automatically
        """
        if not parent:
            parent = aniseed_toolkit.core.selection.first_selected()

        upper_twist_count = aniseed.dialogs.request_count(
            upper_twist_count,
            title="Upper Twist Count",
            message="How many twist joints do you want on the upper arm?",
        )
        lower_twist_count = aniseed.dialogs.request_count(
            lower_twist_count,
            title="Upper Twist Count",
            message="How many twist joints do you want on the lower arm?",
        )

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Joint transform attributes
        joint_data = collections.OrderedDict()
        joint_data["shoulder"] = {}
        joint_data["upperarm"] = {"tx": aniseed_toolkit.core.units.to_cm(9), "jointOrientX": 7, "jointOrientZ": -50}
        joint_data["lowerarm"] = {"tx": aniseed_toolkit.core.units.to_cm(24), "jointOrientY": -20,}
        joint_data["hand"] = {"tx": aniseed_toolkit.core.units.to_cm(24)}

        all_joints = aniseed_toolkit.scene.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=location,
            config=self.config,
            parent=parent,
            prefix=prefix,
        )

        self.input("Shoulder").set(all_joints[0])
        self.input("Hand").set(all_joints[-1])

        if upper_twist_count:
            upper_twists = aniseed_toolkit.scene.joints.create_twist_joints(
                all_joints[1],
                all_joints[2],
                upper_twist_count,
                description=prefix + "ArmUpperTwist",
                location=location,
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Upper Twist Joints").set(upper_twists)

        if lower_twist_count:
            lower_twists = aniseed_toolkit.scene.joints.create_twist_joints(
                all_joints[2],
                all_joints[3],
                lower_twist_count,
                description=prefix + "ArmLowerTwist",
                location=location,
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Lower Twist Joints").set(lower_twists)

    def setup_spaceswitches(self):
        """
        Adds space switch components for the ik hand (World, Component Parent,
        Shoulder - defaulting to World) and the upvector (World, Parent,
        Shoulder, Hand - defaulting to Hand). Does nothing if the stack has no
        "Core : Global Control Root" component.
        """
        global_srt_component = self.stack.get_component_by_type("Core : Global Control Root")

        if not global_srt_component:
            print("No global srt found, skipping spaceswitch setup")
            return

        world = global_srt_component.output("Main Control").address()

        aniseed.builders.add_space_switch(
            component=self,
            label=self.label() + " Hand Space Switch",
            driven=self.output("Ik Hand").address(),
            default_space="World",
            spaces=[
                ("World", world),
                ("Component Parent", self.input("Parent").address()),
                ("Shoulder", self.input("Shoulder").address()),
            ],
        )

        aniseed.builders.add_space_switch(
            component=self,
            label=self.label() + " Upvector Space Switch",
            driven=self.output("Upvector").address(),
            default_space="Hand",
            spaces=[
                ("World", world),
                ("Parent", self.input("Parent").address()),
                ("Shoulder", self.input("Shoulder").address()),
                ("Hand", self.output("Ik Hand").address()),
            ],
        )
