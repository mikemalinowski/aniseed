"""
Provides the "Limb : Flexi Arm" component, an ik/fk spring limb arm whose ik
is driven by a dynamic pivot on the hand, with optional soft ik and multi
chain twists, fk fingers (with metacarpals, except on the thumb), optional
blend rotators at the knuckles and optional multi chain twists along each
digit for bendy, squashy fingers (see aniseed_cartoon.rigging.flexi_arm). A
Transform Mixer can be attached beneath it, for hand poses such as a fist.
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
from maya.api import OpenMaya as om
from aniseed_cartoon.rigging import flexi_arm
from aniseed_cartoon.rigging import multi_chain_twists

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

# -- The twist joint inputs, with the label of the bone each set runs along
# -- and the joint inputs it runs between
_TWISTS = [
    ("Upper Twist Joints", "Upper", "Upper Arm Joint", "Mid Arm Joint"),
    ("Lower Twist Joints", "Lower", "Mid Arm Joint", "Hand Joint"),
]

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
_JOINT_LISTS = [name for name, *_ in _TWISTS] + ["Blend Rotator Joints", "Finger Twist Joints"]

# -- The guide inputs, which may both be given the same node
_GUIDES = ["Pivot Guide Curve", "IK Target Guide"]

# -- The outputs the Transform Mixer's poses are proxied onto
_PROXY_HOSTS = ["Root", "IK Target", "FK Hand"]

_MIXER_TYPE = "Utility : Transform Mixer"


def _part(digit: str, idx: int) -> str:
    """
    Returns the name of the given joint of a digit, used in its output and
    pose mixer deformer names: "Metacarpal" for the first joint of a finger,
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
    fingers. The ik is a spring ik whose handle follows a dynamic pivot under
    the IK Target control, so the Pivot control rocks the hand over the
    Pivot Guide Curve (which lies around the knuckles). In fk the FK controls
    drive the arm and hand.

    The ikfk attribute is on the Root control (0 is ik, 1 is fk), and every
    other control carries it as a proxy. Soft ik attributes are on the IK
    Target control. Twist joints given to the "Upper Twist Joints" and
    "Lower Twist Joints" inputs are driven by multi chain twists running from
    the upper arm to the hand.

    Each digit is given by its tip joint and runs from the joint below the
    hand joint to the tip. The tip is an end joint, so every digit joint but
    the tip gets a control. The fingers start with a metacarpal; the thumb
    does not. Blend rotator joints sit at the knuckles (parented under the
    digit joint before the knuckle) and are driven between the digit joints
    either side of it. Finger twist joints (parented under any digit joint
    but the tip) are driven by multi chain twists running from the digit's
    first joint to its tip, for bendy and squashy fingers. Their controls are
    shown by the bendyVisibility attribute on the digit's first control.

    A Transform Mixer is added beneath the component when it enters the
    stack, driving the offsets of the finger controls, with no poses. Add
    poses such as a fist or spread to it once the rig is built; they are
    proxied onto the Root, IK Target and FK Hand controls.
    """

    identifier = "Limb : Flexi Arm"
    icon = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "flexi_two_bone_ik",
        "flexi_two_bone_ik.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, joint, digit, twist, blend rotator and guide
        inputs, the naming and behaviour options and an output per control.
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
            name="Pivot Guide Curve",
            description="The curve the hand pivot slides along, lying in its own xz plane (the plane of the palm) around the knuckles",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="Upper Twist Joints",
            description="Joints between the upper and mid arm joints, driven by the multi chain twists",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_input(
            name="Lower Twist Joints",
            description="Joints between the mid arm and hand joints, driven by the multi chain twists",
            validate=False,
            group="Twist Configuration",
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
            name="Rotation Multiplier",
            description="Multiplies the Pivot control's rotation before it drives anything",
            value=2.0,
            group="Behaviour",
        )

        self.declare_option(
            name="Rotation Limit",
            description="The Pivot control's x and z rotation is limited to plus and minus this value",
            value=45.0,
            group="Behaviour",
        )

        self.declare_option(
            name="CVs Per Segment",
            description="How many cvs each twist curve (upper and lower arm) has, including the cvs at the arm joints",
            value=4,
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

        self.declare_option(
            name="Debug",
            description="If True, a sphere is created which sits at the hand pivot point",
            value=False,
            group="Behaviour",
        )

        # -- Only used when entering the stack
        self.declare_option(name="Create Joints", value=True, pre_expose=True)
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Blend Rotators Per Knuckle", value=1, pre_expose=True)
        self.declare_option(name="Finger Twist Count", value=3, pre_expose=True)
        self.declare_option(name="Create Pose Mixer", value=True, pre_expose=True)

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

        # -- An output for each finger control and its offset (which the
        # -- Transform Mixer drives). The twist and blend rotator outputs are
        # -- declared by run, as they depend on the joints given.
        for digit in _DIGITS:
            for part in _parts(digit, _default_joint_count(digit)):
                self.declare_output(f"{digit} {part}")
                self.declare_output(f"{digit} {part} Offset")

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output,
        creates the joints and pivot guide if the Create Joints option is
        set, and adds the Transform Mixer if the Create Pose Mixer option is
        set.
        """
        create_joints = self.option("Create Joints")
        create_pose_mixer = self.option("Create Pose Mixer")
        counts = [
            self.option(name)
            for name in ["Upper Twist Count", "Lower Twist Count", "Blend Rotators Per Knuckle", "Finger Twist Count"]
        ]

        for option in [create_joints, create_pose_mixer] + counts:
            option.set_hidden(True)

        self.input("Parent").hook_to_parent()

        if create_joints.get():
            upper_twist_count, lower_twist_count, blend_count, finger_twist_count = [option.get() for option in counts]
            self._create_joints(
                parent=au.core.selection.first_selected(),
                upper_twist_count=upper_twist_count,
                lower_twist_count=lower_twist_count,
                blend_count=blend_count,
                finger_twist_count=finger_twist_count,
            )

        if create_pose_mixer.get():
            self.user_func_add_pose_mixer()

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
        if requirement_name in ["Upper Twist Joints", "Lower Twist Joints", "Blend Rotator Joints", "Finger Twist Joints"]:
            return aniseed.widgets.ObjectList()

        return aniseed.widgets.ObjectSelector(component=self)

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Offers to create the twist joints for whichever twist input is empty,
        the blend rotator joints, finger twist joints and pivot guide if they
        are not set, and the Transform Mixer if there is not one. Mirroring is
        offered by au.mixins.MirrorMixin.
        """
        menu = super().user_functions()

        if self._joints_exist():
            if any(not self.input(input_name).get() for input_name, *_ in _TWISTS):
                menu["Create Twist Joints"] = functools.partial(self.user_func_create_twist_joints)

            if self._digits() and not self.input("Blend Rotator Joints").get():
                menu["Create Blend Rotator Joints"] = functools.partial(self.user_func_create_blend_rotator_joints)

            if self._digits() and not self.input("Finger Twist Joints").get():
                menu["Create Finger Twist Joints"] = functools.partial(self.user_func_create_finger_twist_joints)

            if not self.input("Pivot Guide Curve").get():
                menu["Create Pivot Guide"] = functools.partial(self.user_func_create_pivot_guide)

        if not self._pose_mixers():
            menu["Add Pose Mixer"] = functools.partial(self.user_func_add_pose_mixer)

        return menu

    def user_func_create_twist_joints(self, upper_twist_count: int = None, lower_twist_count: int = None):
        """
        Creates the twist joints for each twist input which is empty, and sets
        the input to them. Any count which is not given is asked for.
        """
        if not self._joints_exist():
            log.warning(f"{self.label()}: Set the arm joints before creating twist joints")
            return

        for (input_name, label, start, end), count in zip(_TWISTS, [upper_twist_count, lower_twist_count]):
            if self.input(input_name).get():
                continue

            count = aniseed.dialogs.request_count(
                count,
                title=f"{label} Twist Count",
                message=f"How many twist joints do you want on the {label.lower()} arm?",
            )
            if count is None:
                return

            if count < 1:
                continue

            self.input(input_name).set(
                multi_chain_twists.create_twist_joints(
                    start_joint=self.input(start).get(),
                    end_joint=self.input(end).get(),
                    count=count,
                    config=self.config,
                    prefix=f"{self.option('Descriptive Prefix').get()}{label}",
                    location=self.option("Location").get(),
                ),
            )

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

    def user_func_create_pivot_guide(self):
        """
        Creates a flat circle around the knuckles (the joints after the
        finger metacarpals), lying in the hand joint's xz plane, and sets the
        Pivot Guide Curve input to it. Reshape it to the area the hand should
        rock over.
        """
        if not self._joints_exist():
            log.warning(f"{self.label()}: Set the arm joints before creating the pivot guide")
            return

        hand = self.input("Hand Joint").get()
        knuckles = [
            om.MVector(cmds.xform(joints[1], query=True, translation=True, worldSpace=True))
            for digit, joints in self._digits().items()
            if digit != _THUMB and len(joints) > 1
        ]

        if knuckles:
            centre = om.MVector()
            for knuckle in knuckles:
                centre += knuckle
            centre /= len(knuckles)
            radius = max((knuckle - centre).length() for knuckle in knuckles) * 1.5
        else:
            centre = om.MVector(cmds.xform(hand, query=True, translation=True, worldSpace=True))
            radius = 0.0

        # -- Fall back to a size relative to the arm if the knuckles are too close
        if radius < 1e-3:
            radius = au.scene.joints.chain_length(
                self.input("Upper Arm Joint").get(),
                hand,
                log_result=False,
            ) / 20.0

        guide = cmds.circle(
            name=self.config.generate_name(
                classification="gde",
                description=f"{self.option('Descriptive Prefix').get()}HandPivot",
                location=self.option("Location").get(),
            ),
            normal=[0, 1, 0],
            radius=radius,
            constructionHistory=False,
        )[0]

        # -- Oriented as the hand joint (without its scale), at the knuckles.
        # -- The pivot lifts the side of the curve its local y points to, so
        # -- for a hand mirrored by behaviour (running down negative x, with
        # -- its y on the palm side) the x and y are turned around, giving the
        # -- same frame as mirroring a guide (see _mirror_guide_matrix).
        hand_matrix = om.MMatrix(cmds.xform(hand, query=True, matrix=True, worldSpace=True))
        rotation = list(om.MTransformationMatrix(hand_matrix).rotation(asQuaternion=True).asMatrix())

        facing = au.scene.joints.get_chain_facing_direction(self.input("Mid Arm Joint").get(), hand)
        if facing == facing.NegativeX:
            rotation = [-value for value in rotation[:8]] + rotation[8:]

        cmds.xform(guide, matrix=rotation[:12] + [centre.x, centre.y, centre.z, 1], worldSpace=True)

        self.input("Pivot Guide Curve").set(mref.get(guide).name())
        cmds.select(clear=True)

    def user_func_add_pose_mixer(self):
        """
        Adds a Transform Mixer beneath this component, with no poses, whose
        deformers drive the offsets of the finger controls. Its poses are
        proxied onto the Root, IK Target and FK Hand controls.
        """
        digits = self._digits()
        layout = [(digit, len(joints) - 1) for digit, joints in digits.items()]
        if not layout:
            layout = [(digit, _default_joint_count(digit)) for digit in _DIGITS]

        mapping = [
            (f"{digit}{part}", self.output(f"{digit} {part} Offset").address())
            for digit, count in layout
            for part in _parts(digit, count)
            if self.output(f"{digit} {part} Offset")
        ]

        self.rig.component_library.request(_MIXER_TYPE).add_to(
            component=self,
            label=f"{self.label()} Hand Poses",
            parent=self.output("Blended Hand").address(),
            mapping=mapping,
            proxy_hosts=[self.output(name).address() for name in _PROXY_HOSTS],
            prefix=f"{self.option('Descriptive Prefix').get()}Hand",
            location=self.option("Location").get(),
        )

    def _create_joints(
            self,
            parent,
            upper_twist_count: int,
            lower_twist_count: int,
            blend_count: int,
            finger_twist_count: int = 0,
    ):
        """
        Creates an upper arm, mid arm and hand chain (shaped as the biped
        example's, see _ARM_JOINTS) in world space, then places it under, and
        at the position of, the parent. The digits (each ending in a tip
        joint) are created under the hand, then the twist joints, blend
        rotator joints, finger twist joints and pivot guide.
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

        self.user_func_create_twist_joints(
            upper_twist_count=upper_twist_count,
            lower_twist_count=lower_twist_count,
        )

        if blend_count:
            self.user_func_create_blend_rotator_joints(count=blend_count)

        if finger_twist_count:
            self.user_func_create_finger_twist_joints(count=finger_twist_count)

        self.user_func_create_pivot_guide()

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
        phalanx and a tip, and a finger also a metacarpal), that the guide is
        a nurbs curve, that every twist, blend rotator and finger twist joint
        exists (and is used once), that each blend rotator joint is parented
        under a controlled digit joint with another after it and each finger
        twist joint under a digit joint other than the tip, and that the ik
        target guide exists if it is given.
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

        # -- The arm and digit joints are driven by the limb, and each twist
        # -- and blend rotator joint by its own setup, so no joint may be used twice
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

        guide = self.input("Pivot Guide Curve").get()
        if not guide or not mref.objExists(guide):
            log.warning(f"{self.label()}: The Pivot Guide Curve must be set to an existing curve")
            return False

        if not mref.listRelatives(guide, shapes=True, type="nurbsCurve", noIntermediate=True):
            log.warning(f"{self.label()}: The Pivot Guide Curve ({guide}) is not a nurbs curve")
            return False

        for option_name in ["CVs Per Segment", "Finger CVs Per Segment"]:
            if self.option(option_name).get() < 2:
                log.warning(f"{self.label()}: {option_name} must be at least 2")
                return False

        # -- A guide connected to another component's output may only be
        # -- created as that component builds, so only a given guide is checked
        ik_target_guide = self.input("IK Target Guide")
        if ik_target_guide.get() and not ik_target_guide.is_address() and not mref.objExists(ik_target_guide.get()):
            log.warning(f"{self.label()}: The IK Target Guide ({ik_target_guide.get()}) does not exist")
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
                        f"{used[full_name]}. Twist and blend rotator joints must be separate joints."
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
        Builds the flexi arm and sets the outputs to its controls.
        """
        digits = self._digits()

        arm = flexi_arm.FlexiArm(
            upper_joint=self.input("Upper Arm Joint").get(),
            hand_joint=self.input("Hand Joint").get(),
            guide_curve=self.input("Pivot Guide Curve").get(),
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=self.input("Parent").get(),
            ik_target_transform=self.input("IK Target Guide").get() or None,
            shape_scale=self.option("Shape Scale").get() or None,
            soft_ik=self.option("Apply Soft Ik").get(),
            upper_twist_joints=self.input("Upper Twist Joints").get() or [],
            lower_twist_joints=self.input("Lower Twist Joints").get() or [],
            cvs_per_segment=self.option("CVs Per Segment").get(),
            rotation_multiplier=self.option("Rotation Multiplier").get(),
            rotation_limit=self.option("Rotation Limit").get(),
            digits=digits,
            blend_rotator_joints=self.input("Blend Rotator Joints").get() or [],
            finger_shape_scale=self.option("Finger Shape Scale").get() or None,
            finger_twist_joints=self.input("Finger Twist Joints").get() or [],
            finger_cvs_per_segment=self.option("Finger CVs Per Segment").get(),
            debug=self.option("Debug").get(),
        ).build()

        for output_name, node in [
            ("Root", arm.root_control.ctl),
            ("IK Target", arm.ik_target_control.ctl),
            ("Pole Vector", arm.pole_vector_control.ctl),
            ("Pivot", arm.pivot.control.ctl),
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

        # -- Remove the twist and blend rotator outputs declared by any
        # -- previous build, as the cv count or joints may have changed since then
        for prefix in ["Key Control ", "Segment ", "Blend Rotator "]:
            au.rig.component_outputs.clear_outputs(self, prefix)

        if arm.twisters:
            for idx, control in enumerate(arm.twisters.key_controls):
                self.declare_output(f"Key Control {idx + 1}")
                self.output(f"Key Control {idx + 1}").set(control.ctl)

            for segment, controls in enumerate(arm.twisters.cv_controls):
                for idx, control in enumerate(controls):
                    self.declare_output(f"Segment {segment + 1} Cv {idx + 1}")
                    self.output(f"Segment {segment + 1} Cv {idx + 1}").set(control.ctl)

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
        Returns the Transform Mixer components beneath this component
        """
        return [child for child in self.children if child.identifier == _MIXER_TYPE]

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the arm joints, then the joints of each digit (in digit order),
        the upper and lower twist joints, the blend rotator joints and the
        finger twist joints, then the guides. Empty if any arm joint is
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
        Returns the pivot guide curve and the IK Target Guide (when given),
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
        and no Transform Mixer is added, as the original's is mirrored with
        this component.
        """
        self.option("Create Joints").set(False)
        self.option("Create Pose Mixer").set(False)

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

        # -- A guide used by both inputs was only copied once
        guide_copies = dict(zip(mirrored_from._guides(), copies))
        for input_name in _GUIDES:
            guide = mirrored_from.input(input_name).get()
            if guide:
                self.input(input_name).set(guide_copies[guide])

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        Restores the Create Joints and Create Pose Mixer options so this
        component's data matches the original, and mirrors the pivot guide
        curve. The mirror pass mirrors the curve's transform as it would a
        joint, which turns its y to the other side of the curve (the pivot
        lifts the side its y points to) and turns its shape around. So its
        transform is set to the original's reflection with only its z turned
        around (see _mirror_guide_matrix), and its cvs to the reflection of
        the original's (in world space, across the YZ plane).
        """
        for option_name in ["Create Joints", "Create Pose Mixer"]:
            self.option(option_name).set(mirrored_from.option(option_name).get(resolved=False))

        original = mirrored_from.input("Pivot Guide Curve").get()
        mirrored = self.input("Pivot Guide Curve").get()

        if not original or not mirrored or original == mirrored:
            return

        if not mref.objExists(original) or not mref.objExists(mirrored):
            return

        positions = cmds.xform(f"{original}.cv[*]", query=True, translation=True, worldSpace=True)
        if len(positions) != len(cmds.xform(f"{mirrored}.cv[*]", query=True, translation=True, worldSpace=True)):
            log.warning(f"{self.label()}: {mirrored} does not have the same cvs as {original}, so it is not reflected")
            return

        cmds.xform(
            mirrored,
            matrix=_mirror_guide_matrix(cmds.xform(original, query=True, matrix=True, worldSpace=True)),
            worldSpace=True,
        )

        for idx in range(len(positions) // 3):
            x, y, z = positions[idx * 3:idx * 3 + 3]
            cmds.xform(f"{mirrored}.cv[{idx}]", translation=[-x, y, z], worldSpace=True)


def _mirror_guide_matrix(matrix: typing.List[float]) -> typing.List[float]:
    """
    Returns the given world matrix reflected across the YZ plane, with its z
    axis then turned around so it is not flipped (inside out). Its x and y
    are the reflections of the given x and y, so the side of the guide its y
    points to (which the pivot lifts) mirrors the original's. As the z is
    turned around, the Pivot control's z rotation mirrors the original's with
    the same value, while its x rotation mirrors it with the opposite value.
    """
    rows = [list(matrix[idx:idx + 4]) for idx in range(0, 16, 4)]
    for row in rows:
        row[0] = -row[0]

    rows[2] = [-value for value in rows[2][:3]] + [rows[2][3]]
    return [value for row in rows for value in row]
