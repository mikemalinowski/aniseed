"""
Provides the "Limb : Arm (Multi Pivot)" component, an ik/fk spring limb arm whose ik
is driven by a pivot control on the hand, with optional soft ik, fk fingers
(with metacarpals, except on the thumb), optional blend rotators at the
knuckles and optional multi chain twists along each digit for bendy, squashy
fingers (see aniseed_experimental.rigging.flexi_arm). Arm twists are added as
an "Augment : Multi Chain Twists" child component, and a Matrix Mixer can be
attached beneath it, for hand poses such as a fist.
"""
import os
import mref
import typing
import logging
import collections
import aniseed
import functools
import aniseed_utilities as au
from maya import cmds
from aniseed_experimental.rigging import flexi_arm
from aniseed_experimental.rigging import multi_chain_twists

log = logging.getLogger(__name__)


# -- The arm joint inputs, in chain order
_JOINTS = ["Upper Arm Joint", "Mid Arm Joint", "Hand Joint"]

# -- The digits, each given by a "<digit> Tip" input (an end joint at the end
# -- of the digit, which has no control). Every digit but the thumb starts
# -- with a metacarpal.
_THUMB = "Thumb"
_DIGITS = [_THUMB, "Index", "Middle", "Ring", "Pinky"]

# -- The number of phalanges each digit is created with (before its tip), and
# -- declared outputs for (a longer digit has its extra outputs declared as
# -- it builds)
_PHALANX_COUNT = 3

# -- The bones twist joints are created along: the label of each, the joint
# -- inputs it runs between, and the option giving how many it gets
_TWISTS = [
    ("Upper", "Upper Arm Joint", "Mid Arm Joint", "Upper Twist Count"),
    ("Lower", "Mid Arm Joint", "Hand Joint", "Lower Twist Count"),
]

_TWISTS_TYPE = "Augment : Multi Chain Twists"

# -- The transforms the arm and digits are created with, taken from the
# -- left arm of aniseed_standard/examples/BipedRig.ma (its bind pose, with
# -- each joint's rotation in its orient). The upper arm's orient is its
# -- world orientation, as the arm is built in world space before being
# -- placed. The tips are not in the biped, so they extend the last bone.
# -- The labels follow the Descriptive Prefix (so "Arm" gives ArmUpper, ArmMid
# -- and ArmHand)
_ARM_JOINTS = [
    ("Upper", {"jointOrientX": 0.402, "jointOrientY": 14.26, "jointOrientZ": -45.036}),
    ("Mid", {"tx": 31.113, "jointOrientX": 0.143, "jointOrientY": -27.611, "jointOrientZ": -0.013}),
    ("Hand", {"tx": 22.956, "jointOrientX": 5.213, "jointOrientY": -6.66, "jointOrientZ": -6.849}),
]


def _finger(metacarpal: tuple, first: tuple, lengths: typing.List[float]) -> typing.List[typing.Tuple[str, dict]]:
    """
    Returns the joint transforms of a finger: its metacarpal (given its
    translate, the orient is shared by every finger), its first phalanx
    (given its translate and orient), then the given lengths for the
    remaining phalanges and the tip
    """
    orient = {"jointOrientX": -7.667, "jointOrientY": 6.634, "jointOrientZ": 7.48}
    tx, ty, tz = metacarpal
    joints = [("Metacarpal", dict(orient, tx=tx, ty=ty, tz=tz))]

    (tx, ty, tz), (ox, oy, oz) = first
    joints.append(("01", {"tx": tx, "ty": ty, "tz": tz, "jointOrientX": ox, "jointOrientY": oy, "jointOrientZ": oz}))

    for suffix, length in zip(["02", "03", "Tip"], lengths):
        joints.append((suffix, {"tx": length}))
    return joints


_DIGIT_JOINTS = collections.OrderedDict([
    ("Index", _finger((1.025, 0.191, 0.295), ((12.456, -1.113, 3.391), (0.153, -5.914, -1.484)), [3.871, 3.845, 3.1])),
    ("Middle", _finger((0.945, 0.068, -0.526), ((12.517, -0.783, 1.093), (3.874, 0, 0)), [3.962, 4.479, 3.6])),
    ("Ring", _finger((0.865, -0.055, -1.346), ((11.459, -1.243, -0.391), (7.177, 7.136, -0.463)), [4.05, 4.02, 3.2])),
    ("Pinky", _finger((0.785, -0.177, -2.166), ((10.742, -0.855, -2.32), (2.883, 13.02, -2.743)), [2.899, 2.618, 2.1])),
    (_THUMB, [
        ("01", {"tx": 3.243, "ty": -0.716, "tz": 1.365, "jointOrientX": 115.289, "jointOrientY": -31.15, "jointOrientZ": -24.393}),
        ("02", {"tx": 5.0, "jointOrientZ": -6.765}),
        ("03", {"tx": 3.666, "jointOrientZ": -7.72}),
        ("Tip", {"tx": 2.9}),
    ]),
])

# -- The inputs which hold lists of joints, in the order they are mirrored
_JOINT_LISTS = ["Blend Rotator Joints", "Finger Twist Joints"]

# -- The guide inputs, which may be given the same node
_GUIDES = ["IK Target Guide", "Pivot Control Transform"]

# -- The outputs the Matrix Mixer's poses are proxied onto
_PROXY_HOSTS = ["Root", "IK Target", "FK Hand"]

_MIXER_TYPE = "Utility : Matrix Mixer"


def _part(digit: str, idx: int) -> str:
    """
    Returns the name of the given joint of a digit, used in its output and
    names: "Metacarpal" for the first joint of a finger,
    otherwise the number of the phalanx (from 1)
    """
    if digit == _THUMB:
        return str(idx + 1)
    return "Metacarpal" if idx == 0 else str(idx)


def _parts(digit: str, count: int) -> typing.List[str]:
    """
    Returns the part names of a digit with the given number of joints
    """
    return [_part(digit, idx) for idx in range(count)]


def _default_joint_count(digit: str) -> int:
    """
    Returns the number of controlled joints (all but the tip) the digit is
    created with
    """
    return _PHALANX_COUNT if digit == _THUMB else _PHALANX_COUNT + 1


class FlexiArmComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    """
    Builds an ik/fk arm on an upper arm, mid arm and hand joint, with fk
    fingers. The ik is a spring ik whose handle sits under the Pivot control,
    which is under the IK Target control at the Pivot Control Transform (or
    the IK Target if not given), so the Pivot control turns the hand about
    that point. In fk the FK controls drive the arm and hand.

    The ikfk attribute is on the Root control (0 is ik, 1 is fk), and every
    other control carries it as a proxy. Soft ik attributes are on the IK
    Target control.

    When it enters the stack and creates its joints, twist joints are created
    along the upper and lower arm (as many as the Upper and Lower Twist Count
    options give) and, if there are any, an "Augment : Multi Chain Twists"
    component is added beneath it to drive them, which manages them from then
    on. While it has a twists child, the arm adds a ShowDetailedControls
    attribute to the Root control (proxied to the ik, fk and pivot controls),
    which a "Utility : Connect Attribute (Multi)" under the twists connects to
    the visibility of the twist control shapes.

    Each digit is given by its tip joint and runs from the joint below the
    hand joint to the tip. The tip is an end joint, so every digit joint but
    the tip gets a control. The fingers start with a metacarpal; the thumb
    does not. Blend rotator joints sit at the knuckles (parented under the
    digit joint before the knuckle) and are driven between the digit joints
    either side of it. Finger twist joints (parented under any digit joint
    but the tip) are driven by multi chain twists running from the digit's
    first joint to its tip, for bendy and squashy fingers. Their controls are
    shown by the ShowDetailedFingerControls attribute on the digit's first
    control, which every other control of the digit carries as a proxy.

    A Matrix Mixer is added beneath the component when it enters the
    stack, driving the finger controls (through their offsetParentMatrix),
    with no poses. Add
    poses such as a fist or spread to it once the rig is built; they are
    proxied onto the Root, IK Target and FK Hand controls.
    """

    identifier = "Limb : Arm (Multi Pivot)"
    deprecated_names = ["Limb : Flexi Arm"]
    icon = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "flexi_two_bone_ik",
        "flexi_two_bone_ik.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, joint, digit, blend rotator, finger twist and
        guide inputs, the naming and behaviour options and an output per control.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        for input_name, description in zip(
            _JOINTS,
            [
                "The upper arm joint",
                "The mid arm (elbow) joint, directly below the upper arm joint",
                "The hand joint, directly below the mid arm joint",
            ],
        ):
            self.declare_input(
                name=input_name,
                description=description,
                validate=True,
                group="Required Joints",
            )

        for digit in _DIGITS:
            self.declare_input(
                name=f"{digit} Tip",
                description=(
                    f"The end joint at the tip of the {digit.lower()}, below the hand joint. "
                    f"If not given there is no {digit.lower()}."
                ),
                validate=False,
                group="Digit Joints",
            )

        self.declare_input(
            name="Blend Rotator Joints",
            description=(
                "Joints at the knuckles, each parented under the digit joint before its knuckle, "
                "driven between that digit joint and the next"
            ),
            validate=False,
            group="Digit Joints",
        )

        self.declare_input(
            name="Finger Twist Joints",
            description=(
                "Joints along the digits, each parented under a digit joint other than the tip, driven by "
                "multi chain twists along the digit for bendy, squashy fingers"
            ),
            validate=False,
            group="Digit Joints",
        )

        self.declare_input(
            name="IK Target Guide",
            description="Optional transform to place the IK Target control at. If not given, it matches the Hand Joint.",
            validate=False,
            group="Optional Nodes",
        )

        self.declare_input(
            name="Pivot Control Transform",
            description=(
                "Optional transform to place the Pivot control at (position and rotation), which the ik handle "
                "sits under. If not given, it matches the IK Target control."
            ),
            validate=False,
            group="Optional Nodes",
        )

        self.declare_option(
            name="Descriptive Prefix",
            description=(
                "Prefix used when naming the joints, controls and mechanical nodes. The finger nodes are "
                "named with their digit (such as Index) instead."
            ),
            value="Arm",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            description="Location token (e.g. md/lf/rt) applied to generated node names",
            value=self.config.left,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Apply Soft Ik",
            description="If enabled, soft ik (with stretch) is applied to the ik chain, with its attributes on the IK Target control",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Finger CVs Per Segment",
            description="How many cvs each finger twist curve (one per finger bone) has, including the cvs at the digit joints",
            value=3,
            group="Behaviour",
        )

        self.declare_option(
            name="Shape Scale",
            description="The scale of the arm control shapes. If zero, it is worked out from the length of the chain.",
            value=0.0,
            group="Behaviour",
        )

        self.declare_option(
            name="Finger Shape Scale",
            description="The scale of the finger control shapes. If zero, it is worked out from the length of the digits.",
            value=0.0,
            group="Behaviour",
        )

        # -- Only used when entering the stack
        self.declare_option(name="Create Joints", value=True, pre_expose=True)
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Blend Rotators Per Knuckle", value=1, pre_expose=True)
        self.declare_option(name="Finger Twist Count", value=3, pre_expose=True)
        self.declare_option(name="Create Pose Mixer", value=True, pre_expose=True)
        self.declare_option(name="Apply Space Switches", value=True, pre_expose=True)

        for output_name in [
            "Root",
            "IK Target",
            "Pole Vector",
            "Pivot",
            "FK Upper",
            "FK Mid",
            "FK Hand",
        ]:
            self.declare_output(output_name)

        self.declare_output(
            name="Blended Hand",
            description="The blend chain's hand, which the Hand Joint and the fingers follow",
            is_default=True,
        )

        # -- An output for each finger control (which the Matrix Mixer
        # -- drives) and its offset. The finger twist and blend rotator
        # -- outputs are declared by run, as they depend on the joints given.
        for digit in _DIGITS:
            for part in _parts(digit, _default_joint_count(digit)):
                self.declare_output(f"{digit} {part}")
                self.declare_output(f"{digit} {part} Offset")

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output,
        creates the joints and twists if the Create Joints option is set,
        adds the Matrix Mixer if the Create Pose Mixer option is set, and adds
        the space switches if the Apply Space Switches option is set.
        """
        create_joints = self.option("Create Joints")
        create_pose_mixer = self.option("Create Pose Mixer")
        apply_space_switches = self.option("Apply Space Switches")
        counts = [
            self.option(name)
            for name in ["Upper Twist Count", "Lower Twist Count", "Blend Rotators Per Knuckle", "Finger Twist Count"]
        ]

        for option in [create_joints, create_pose_mixer, apply_space_switches] + counts:
            option.set_hidden(True)

        self.input("Parent").hook_to_parent()

        if create_joints.get():
            _, _, blend_count, finger_twist_count = [option.get() for option in counts]
            self._create_joints(
                parent=au.core.selection.first_selected(),
                blend_count=blend_count,
                finger_twist_count=finger_twist_count,
            )
            self._add_twists()

        if create_pose_mixer.get():
            self.user_func_add_pose_mixer()

        if apply_space_switches.get():
            self._create_space_switches()

    def _create_space_switches(self):
        """
        Adds space switch components beneath this one for the IK Target
        control (Parent and World, defaulting to World) and the Pole Vector
        control (Parent, Hand and World, defaulting to Hand). Parent is the
        Root control, Hand the IK Target control and World the Global
        Control Root's main control. Skipped with a logged message if there
        is no "Core : Global Control Root" component in the stack.
        """
        global_srt_component = self.stack.get_component_by_type("Core : Global Control Root")
        if not global_srt_component:
            log.info(f"{self.label()}: No Global Control Root found, so no space switches are added")
            return

        world = global_srt_component.output("Main Control").address()
        root = self.output("Root").address()
        ik_target = self.output("IK Target").address()

        space_switch = self.rig.component_library.request("Augment : Space Switch")

        space_switch.add_to(
            component=self,
            label=f"{self.label()} IK Space Switch",
            driven=ik_target,
            default_space="World",
            spaces=[
                ("Parent", root),
                ("World", world),
            ],
        )

        space_switch.add_to(
            component=self,
            label=f"{self.label()} Pole Vector Space Switch",
            driven=self.output("Pole Vector").address(),
            default_space="Hand",
            spaces=[
                ("Parent", root),
                ("Hand", ik_target),
                ("World", world),
            ],
        )

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
        if requirement_name in ["Blend Rotator Joints", "Finger Twist Joints"]:
            return aniseed.widgets.ObjectList()

        return aniseed.widgets.ObjectSelector(component=self)

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Offers to create the blend rotator joints and finger twist joints if
        they are not set, and the Matrix Mixer if there is not one. Mirroring
        is offered by au.mixins.MirrorMixin.
        """
        menu = super().user_functions()

        if self._joints_exist():
            if self._digits() and not self.input("Blend Rotator Joints").get():
                menu["Create Blend Rotator Joints"] = functools.partial(self.user_func_create_blend_rotator_joints)

            if self._digits() and not self.input("Finger Twist Joints").get():
                menu["Create Finger Twist Joints"] = functools.partial(self.user_func_create_finger_twist_joints)

        if not self._pose_mixers():
            menu["Add Pose Mixer"] = functools.partial(self.user_func_add_pose_mixer)

        return menu

    def _add_twists(self):
        """
        Creates the twist joints along the upper and lower arm (as many as the
        Upper and Lower Twist Count options give) and, if there are any, adds
        an "Augment : Multi Chain Twists" component beneath this one to drive
        them, from the upper arm to the hand. Its controls sit under the Root
        control, whose roll the upper arm's twist holds, and their visibility
        is driven by the Root control's ShowDetailedControls attribute. From
        then on the twists are managed by that component alone.
        """
        twist_joints = []

        for label, start, end, option_name in _TWISTS:
            count = self.option(option_name).get()
            if count < 1:
                continue

            twist_joints.extend(
                multi_chain_twists.create_twist_joints(
                    start_joint=self.input(start).get(),
                    end_joint=self.input(end).get(),
                    count=count,
                    config=self.config,
                    prefix=f"{self.option('Descriptive Prefix').get()}{label}",
                    location=self.option("Location").get(),
                ),
            )

        if not twist_joints:
            return

        root = self.output("Root").address()
        self.rig.component_library.request(_TWISTS_TYPE).add_to(
            component=self,
            label=f"{self.label()} Twists",
            parent=root,
            start_joint=self.input("Upper Arm Joint").get(),
            end_joint=self.input("Hand Joint").get(),
            twist_joints=twist_joints,
            root_twist_node=root,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            visibility_source=(root, flexi_arm.FlexiArm.SHOW_DETAILED_CONTROLS),
        )

    def _twists(self) -> list:
        """
        Returns the Multi Chain Twists components beneath this component
        """
        return [child for child in self.children if child.identifier == _TWISTS_TYPE]

    def user_func_create_blend_rotator_joints(self, count: int = None):
        """
        Creates the given number of blend rotator joints (asked for if not
        given) at every knuckle - between each pair of controlled digit joints
        (so not at the tip) - and sets the Blend Rotator Joints input to them. Each is parented under
        the digit joint before its knuckle, matched to the one after it, and
        carries a blendRotatorWeight attribute (spread evenly between the
        joints at the knuckle) which its Blend starts at.
        """
        digits = self._digits()
        if not digits:
            log.warning(f"{self.label()}: Set the digit tips before creating blend rotator joints")
            return

        count = aniseed.dialogs.request_count(
            count,
            title="Blend Rotators Per Knuckle",
            message="How many blend rotator joints do you want at each knuckle (0 to 2)?",
        )
        if not count:
            return

        location = self.option("Location").get()
        created = []

        for digit, joints in digits.items():
            controlled = joints[:-1]
            for idx, (joint, next_joint) in enumerate(zip(controlled, controlled[1:])):
                for blend_idx in range(count):
                    blend_joint = au.scene.joints.create(
                        description=f"{digit}{_part(digit, idx + 1)}Blend",
                        location=location,
                        parent=joint,
                        config=self.config,
                        match_to=next_joint,
                    )
                    au.scene.joints.move_rotations_to_orients([blend_joint])

                    weight = mref.get(blend_joint).add_attribute(
                        flexi_arm.BLEND_WEIGHT_ATTRIBUTE,
                        value=(blend_idx + 1.0) / (count + 1.0),
                        attribute_type="float",
                        keyable=False,
                        min=0,
                        max=1,
                    )
                    weight.set(channelBox=True)
                    created.append(mref.get(blend_joint).name())

        self.input("Blend Rotator Joints").set(created)
        cmds.select(clear=True)

    def user_func_create_finger_twist_joints(self, count: int = None):
        """
        Creates the given number of twist joints (asked for if not given)
        along every bone of every digit, from its first joint to its tip,
        under the digit joint at the start of each bone, and sets the Finger
        Twist Joints input to them
        """
        digits = self._digits()
        if not digits:
            log.warning(f"{self.label()}: Set the digit tips before creating finger twist joints")
            return

        count = aniseed.dialogs.request_count(
            count,
            title="Finger Twist Count",
            message="How many twist joints do you want on each finger bone?",
        )
        if not count:
            return

        created = []
        for digit, joints in digits.items():
            created.extend(
                mref.get(joint).name()
                for joint in multi_chain_twists.create_twist_joints(
                    start_joint=joints[0],
                    end_joint=joints[-1],
                    count=count,
                    config=self.config,
                    prefix=digit,
                    location=self.option("Location").get(),
                )
            )

        self.input("Finger Twist Joints").set(created)

    def user_func_add_pose_mixer(self):
        """
        Adds a Matrix Mixer beneath this component, with no poses, driving
        the finger controls. Its poses are proxied onto the Root, IK Target
        and FK Hand controls.
        """
        digits = self._digits()
        layout = [(digit, len(joints) - 1) for digit, joints in digits.items()]
        if not layout:
            layout = [(digit, _default_joint_count(digit)) for digit in _DIGITS]

        driven = [
            self.output(f"{digit} {part}").address()
            for digit, count in layout
            for part in _parts(digit, count)
            if self.output(f"{digit} {part}")
        ]

        self.rig.component_library.request(_MIXER_TYPE).add_to(
            component=self,
            label=f"{self.label()} Hand Poses",
            parent=self.output("Blended Hand").address(),
            driven=driven,
            proxy_hosts=[self.output(name).address() for name in _PROXY_HOSTS],
            prefix=f"{self.option('Descriptive Prefix').get()}Hand",
            location=self.option("Location").get(),
        )

    def _create_joints(self, parent, blend_count: int, finger_twist_count: int = 0):
        """
        Creates an upper arm, mid arm and hand chain (shaped as the biped
        example's, see _ARM_JOINTS) in world space, then places it under, and
        at the position of, the parent. The digits (each ending in a tip
        joint) are created under the hand, then the blend rotator joints and
        finger twist joints.
        """
        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        joints = au.scene.joints.chain_from_ordered_dict(
            joint_data=collections.OrderedDict(_ARM_JOINTS),
            location=location,
            config=self.config,
            parent=None,
            prefix=prefix,
        )

        if parent:
            root_joint = mref.get(joints[0])
            root_joint.set_parent(parent)
            root_joint.set_position(mref.get(parent).get_position(space="world"), space="world")

        for input_name, joint in zip(_JOINTS, joints):
            self.input(input_name).set(joint)

        # -- The digits run down the hand's x, spread in z, with the thumb
        # -- on the positive z side (by the index finger) and the palm facing
        # -- negative y
        for digit in _DIGITS:
            digit_data = collections.OrderedDict(
                (f"{digit}{suffix}", attributes)
                for suffix, attributes in _DIGIT_JOINTS[digit]
            )
            self._create_digit(digit, digit_data, joints[-1])

        if blend_count:
            self.user_func_create_blend_rotator_joints(count=blend_count)

        if finger_twist_count:
            self.user_func_create_finger_twist_joints(count=finger_twist_count)

    def _create_digit(self, digit: str, joint_data: collections.OrderedDict, hand: str):
        """
        Creates a digit's chain under the hand (named for the digit, without
        the prefix) and sets its tip input
        """
        joints = au.scene.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=self.option("Location").get(),
            config=self.config,
            parent=hand,
        )
        self.input(f"{digit} Tip").set(joints[-1])

    def is_valid(self) -> bool:
        """
        Checks the upper arm to hand joints form a chain of exactly three
        joints, that each given digit is below the hand (with at least one
        phalanx and a tip, and a finger also a metacarpal), that every blend rotator and finger twist joint
        exists (and is used once), that each blend rotator joint is parented
        under a controlled digit joint with another after it and each finger
        twist joint under a digit joint other than the tip, and that the ik
        target guide and pivot control transform exist if they are given.
        """
        for input_name in _JOINTS:
            joint = self.input(input_name).get()
            if not joint or not mref.objExists(joint):
                log.warning(f"{self.label()}: The {input_name} must be set to an existing joint")
                return False

        upper, mid, hand = [mref.get(self.input(name).get()).full_name() for name in _JOINTS]

        if self._chain() != [upper, mid, hand]:
            log.warning(
                f"{self.label()}: The Mid Arm Joint must be directly below the Upper Arm Joint, "
                f"and the Hand Joint directly below the Mid Arm Joint"
            )
            return False

        # -- The arm and digit joints are driven by the limb, and each finger
        # -- twist and blend rotator joint by its own setup, so no joint may be used twice
        used = {joint: "arm joints" for joint in [upper, mid, hand]}

        for digit in _DIGITS:
            tip = self.input(f"{digit} Tip").get()
            if not tip:
                continue

            if not mref.objExists(tip):
                log.warning(f"{self.label()}: The {digit} Tip ({tip}) does not exist")
                return False

            joints = self._digit_chain(digit)
            if not joints:
                log.warning(f"{self.label()}: The {digit} Tip ({tip}) must be below the Hand Joint")
                return False

            minimum = 2 if digit == _THUMB else 3
            if len(joints) < minimum:
                needs = "a phalanx and a tip" if digit == _THUMB else "a metacarpal, a phalanx and a tip"
                log.warning(f"{self.label()}: The {digit.lower()} needs {needs} below the Hand Joint")
                return False

            for joint in joints:
                if joint in used:
                    log.warning(f"{self.label()}: {joint} is in the {digit.lower()} but is already one of the {used[joint]}")
                    return False
                used[joint] = f"{digit.lower()} joints"

        if self.option("Finger CVs Per Segment").get() < 2:
            log.warning(f"{self.label()}: Finger CVs Per Segment must be at least 2")
            return False

        # -- A guide connected to another component's output may only be
        # -- created as that component builds, so only a given guide is checked
        for input_name in ["IK Target Guide", "Pivot Control Transform"]:
            optional_guide = self.input(input_name)
            if optional_guide.get() and not optional_guide.is_address() and not mref.objExists(optional_guide.get()):
                log.warning(f"{self.label()}: The {input_name} ({optional_guide.get()}) does not exist")
                return False

        # -- The joints a blend rotator joint may be parented under (every
        # -- controlled digit joint with another after it) and those a finger
        # -- twist joint may be (every digit joint but the tip)
        digits = self._digits().values()
        allowed_parents = {
            "Blend Rotator Joints": (
                {joint for joints in digits for joint in joints[:-2]},
                "a controlled digit joint which has another controlled digit joint after it",
            ),
            "Finger Twist Joints": (
                {joint for joints in digits for joint in joints[:-1]},
                "a digit joint other than the tip",
            ),
        }

        for input_name in _JOINT_LISTS:
            for joint in self.input(input_name).get() or []:
                if not mref.objExists(joint):
                    log.warning(f"{self.label()}: The {input_name} joint {joint} does not exist")
                    return False

                full_name = mref.get(joint).full_name()
                if full_name in used:
                    log.warning(
                        f"{self.label()}: {joint} is in the {input_name} but is already one of the "
                        f"{used[full_name]}. Finger twist and blend rotator joints must be separate joints."
                    )
                    return False
                used[full_name] = input_name

                if input_name in allowed_parents:
                    parents, description = allowed_parents[input_name]
                    parent = mref.get(joint).parent()
                    if not parent or parent.full_name() not in parents:
                        log.warning(f"{self.label()}: The {input_name} joint {joint} must be parented under {description}")
                        return False

        return True

    def run(self) -> bool:
        """
        Builds the flexi arm and sets the outputs to its controls. The
        ShowDetailedControls attribute is added if there is a twists child.
        """
        digits = self._digits()

        arm = flexi_arm.FlexiArm(
            upper_joint=self.input("Upper Arm Joint").get(),
            hand_joint=self.input("Hand Joint").get(),
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=self.input("Parent").get(),
            ik_target_transform=self.input("IK Target Guide").get() or None,
            shape_scale=self.option("Shape Scale").get() or None,
            soft_ik=self.option("Apply Soft Ik").get(),
            show_detailed_controls=bool(self._twists()),
            digits=digits,
            blend_rotator_joints=self.input("Blend Rotator Joints").get() or [],
            finger_shape_scale=self.option("Finger Shape Scale").get() or None,
            finger_twist_joints=self.input("Finger Twist Joints").get() or [],
            finger_cvs_per_segment=self.option("Finger CVs Per Segment").get(),
            pivot_control_transform=self.input("Pivot Control Transform").get() or None,
        ).build()

        for output_name, node in [
            ("Root", arm.root_control.ctl),
            ("IK Target", arm.ik_target_control.ctl),
            ("Pole Vector", arm.pole_vector_control.ctl),
            ("Pivot", arm.pivot_control.ctl),
            ("FK Upper", arm.fk_controls[0].ctl),
            ("FK Mid", arm.fk_controls[1].ctl),
            ("FK Hand", arm.fk_controls[2].ctl),
            ("Blended Hand", arm.blend_chain[-1]),
        ]:
            self.output(output_name).set(node)

        # -- Remove the finger twist outputs declared by any previous build,
        # -- and clear the other digit outputs, as a digit may have been
        # -- removed since then
        for digit in _DIGITS:
            for prefix in [f"{digit} Key Control ", f"{digit} Segment "]:
                au.rig.component_outputs.clear_outputs(self, prefix)

        for output in self.outputs():
            if output.name().split(" ")[0] in _DIGITS:
                output.set("")

        for digit, controls in arm.fingers.items():
            for part, control in zip(_parts(digit, len(controls)), controls):
                for output_name, node in [(f"{digit} {part}", control.ctl), (f"{digit} {part} Offset", control.off)]:
                    if not self.output(output_name):
                        self.declare_output(output_name)
                    self.output(output_name).set(node)

        # -- Remove the blend rotator outputs declared by any previous build,
        # -- as the joints may have changed since then
        au.rig.component_outputs.clear_outputs(self, "Blend Rotator ")

        for idx, control in enumerate(arm.blend_rotators):
            self.declare_output(f"Blend Rotator {idx + 1}")
            self.output(f"Blend Rotator {idx + 1}").set(control.ctl)

        for digit, twisters in arm.finger_twisters.items():
            for idx, control in enumerate(twisters.key_controls):
                self.declare_output(f"{digit} Key Control {idx + 1}")
                self.output(f"{digit} Key Control {idx + 1}").set(control.ctl)

            for segment, controls in enumerate(twisters.cv_controls):
                for idx, control in enumerate(controls):
                    self.declare_output(f"{digit} Segment {segment + 1} Cv {idx + 1}")
                    self.output(f"{digit} Segment {segment + 1} Cv {idx + 1}").set(control.ctl)

        return True

    def _joints_exist(self) -> bool:
        """
        Returns True if every arm joint input is set and exists
        """
        return all(
            self.input(name).get() and mref.objExists(self.input(name).get())
            for name in _JOINTS
        )

    def _chain(self) -> typing.List[str]:
        """
        Returns the joints from the upper arm joint to the hand joint, or an
        empty list if either is missing or the hand is not below the upper arm
        """
        upper = self.input("Upper Arm Joint").get()
        hand = self.input("Hand Joint").get()

        if not all(joint and mref.objExists(joint) for joint in [upper, hand]):
            return []

        upper = mref.get(upper).full_name()
        hand = mref.get(hand).full_name()
        if not hand.startswith(f"{upper}|"):
            return []

        return [mref.get(joint).full_name() for joint in au.scene.joints.get_between(start=upper, end=hand)]

    def _digit_chain(self, digit: str) -> typing.List[str]:
        """
        Returns the joints of the digit, from the joint below the hand joint
        to its tip, or an empty list if the digit is not given, or its tip is
        not below the hand joint
        """
        hand = self.input("Hand Joint").get()
        tip = self.input(f"{digit} Tip").get()

        if not all(joint and mref.objExists(joint) for joint in [hand, tip]):
            return []

        hand = mref.get(hand).full_name()
        tip = mref.get(tip).full_name()
        if not tip.startswith(f"{hand}|"):
            return []

        return [mref.get(joint).full_name() for joint in au.scene.joints.get_between(start=hand, end=tip)[1:]]

    def _digits(self) -> typing.Dict[str, typing.List[str]]:
        """
        Returns the joints of every given digit, in digit order
        """
        digits = collections.OrderedDict()
        for digit in _DIGITS:
            joints = self._digit_chain(digit)
            if joints:
                digits[digit] = joints
        return digits

    def _pose_mixers(self) -> list:
        """
        Returns the Matrix Mixer components beneath this component
        """
        return [child for child in self.children if child.identifier == _MIXER_TYPE]

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the arm joints, then the joints of each digit (in digit order),
        the blend rotator joints and the finger twist joints, then the guides. Empty if any arm joint is
        missing.
        """
        if not self._joints_exist():
            return []

        items = [self.input(name).get() for name in _JOINTS]

        # -- Names rather than full paths, as the mirrored copies are named
        # -- from these
        for joints in self._digits().values():
            items.extend(mref.get(joint).name() for joint in joints)

        for input_name in _JOINT_LISTS:
            items.extend(joint for joint in self.input(input_name).get() or [] if joint)

        return items + self._guides()

    def _guides(self) -> typing.List[str]:
        """
        Returns the IK Target Guide and Pivot Control Transform (when given),
        listing a node used by both only once
        """
        guides = []
        for input_name in _GUIDES:
            guide = self.input(input_name).get()
            if guide and guide not in guides:
                guides.append(guide)
        return guides

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the upper arm joint. Empty if there is no upper
        arm joint or it has no parent.
        """
        upper = self.input("Upper Arm Joint").get()
        if not upper or not mref.objExists(upper):
            return ""

        parent = mref.get(upper).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's joints and guides if they already exist (the
        search and replaced names), otherwise copies the original's into the
        mirrored hierarchy for this component to drive. Either way no joints
        are created on entering the stack, as this component already has them,
        and no twists, Matrix Mixer or space switches are added, as the
        original's are mirrored with this component.
        """
        self.option("Create Joints").set(False)
        self.option("Create Pose Mixer").set(False)
        self.option("Apply Space Switches").set(False)

        original_items = mirrored_from.mirror_mixin_items_to_mirror()
        if not original_items:
            return

        if self.mirror_mixin_counterparts_exist(original_items, self.mirror_mixin_items_to_mirror()):
            return

        copies = self.mirror_mixin_copy_nodes(original_items)

        for input_name in _JOINTS:
            self.input(input_name).set(copies.pop(0))

        original_digits = mirrored_from._digits()
        for digit in _DIGITS:
            joints = original_digits.get(digit, [])
            self.input(f"{digit} Tip").set(copies[len(joints) - 1] if joints else "")
            copies = copies[len(joints):]

        for input_name in _JOINT_LISTS:
            count = len([joint for joint in mirrored_from.input(input_name).get() or [] if joint])
            self.input(input_name).set(copies[:count])
            copies = copies[count:]

        # -- A guide used by more than one input was only copied once
        guide_copies = dict(zip(mirrored_from._guides(), copies))
        for input_name in _GUIDES:
            guide = mirrored_from.input(input_name).get()
            if guide:
                self.input(input_name).set(guide_copies[guide])

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        Restores the Create Joints, Create Pose Mixer and Apply Space Switches
        options so this component's data matches the original.
        """
        for option_name in ["Create Joints", "Create Pose Mixer", "Apply Space Switches"]:
            self.option(option_name).set(mirrored_from.option(option_name).get(resolved=False))
