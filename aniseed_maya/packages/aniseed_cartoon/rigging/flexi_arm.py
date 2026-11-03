"""
Provides the FlexiArm class, an IkfkSpringLimb from the upper arm to the hand
with a DynamicPivot on the hand driving its ik, optional soft ik and multi
chain twists, and fk fingers with optional blend rotators at the knuckles.

The dynamic pivot sits under the ik target control, aligned to its guide
curve (which lies around the knuckles, in the plane of the palm), and the
spring ik handle follows the pivot's result, so rocking the pivot rolls the
hand over its knuckles and carries the arm with it. The ik chain's hand joint
takes its rotation from the pivot's result and its position from the ik
chain, so the given hand joint follows the spring limb's blend chain like the
upper and mid joints, whether in ik or fk.

Every node is named with the prefix, except the finger nodes (controls,
blend rotators and twists), which are named with their digit (such as
"Index") instead.

The fingers are fk only. They sit under the blend chain's hand, so they
follow the hand in both ik and fk, and each digit joint but the last (the
tip, an end joint at the end of the digit) is driven by its own control. A
blend rotator joint at a knuckle (parented under the digit before the
knuckle) is driven between the controls of the digits either side of it.

A digit with twist joints also gets a MultiChainTwisters setup from its first
joint to its tip, so its twist joints bend, twist and squash along each of
its bones. Its controls are hidden unless the bendyVisibility attribute on
the digit's first control is on.

Added to the IkfkSpringLimb structure:

    SpringRoot
        IkHand (the ik target control)
            PivotSetup (the DynamicPivot, aligned to the guide curve)
                ... DynamicPivotResult
                    SpringIkHandleTransform (moved here from the ik target)
        SpringIkChain
            ... hand (rotation from the DynamicPivotResult)
        SpringBlendChain
            ... hand
                Fingers (org)
                    <Digit> controls, each under the previous one
                    BlendRotators (org, visibility from the root control)
                        <Digit>Blend controls
                    <Digit>MultiChainTwisters (per digit with twist joints,
                        visibility from the digit's first control)
        MultiChainTwisters (upper arm to hand, if twist joints are given)
"""
import typing
import collections

from maya import cmds

import mref
import aniseed_utilities as au
from aniseed_cartoon.rigging import dynamic_pivot
from aniseed_cartoon.rigging import ikfk_spring_limb
from aniseed_cartoon.rigging import multi_chain_twists
from aniseed_cartoon.rigging import soft_ik_connection

if typing.TYPE_CHECKING:
    import aniseed


# -- An attribute a blend rotator joint can carry to give the starting value
# -- of its control's Blend attribute, so a tuned value survives a rebuild
BLEND_WEIGHT_ATTRIBUTE = "blendRotatorWeight"


class FlexiArm(ikfk_spring_limb.IkfkSpringLimb):
    """
    Builds the flexi arm on an upper arm, mid arm and hand joint, plus any
    digits under the hand.

    Args:
        upper_joint: The upper arm joint
        hand_joint: The hand joint, which must be below the upper joint with
            the mid arm joint between them
        guide_curve: The curve the hand pivot slides along. Its local xz
            plane is the pivot plane (see dynamic_pivot.DynamicPivot).
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name
        location: The location token (config.left, config.middle etc)
        parent: Optional node to parent the root control under
        ik_target_transform: Optional node to match the ik target control
            to. If not given, it is matched to the hand joint.
        shape_scale: Optional scale for the arm control shapes. If not given
            it is derived from the length of the chain.
        soft_ik: If True, soft ik (with stretch) is applied to the ik chain,
            with its attributes on the ik target control
        upper_twist_joints: Optional twist joints between the upper and mid
            joints, driven by the multi chain twists
        lower_twist_joints: Optional twist joints between the mid and hand
            joints, driven by the multi chain twists
        cvs_per_segment: How many cvs each multi chain twist curve has
        rotation_multiplier: Passed to the hand pivot
        rotation_limit: Passed to the hand pivot
        digits: Ordered mapping of digit label (such as "Index") to its
            joints, root first, all below the hand joint. The last joint is
            the tip, an end joint which is not given a control.
        blend_rotator_joints: Optional joints, each parented under a
            controlled digit joint which has another controlled joint after
            it, driven between the controls of that digit joint and the next.
            A joint carrying a
            blendRotatorWeight attribute starts its Blend at that value,
            otherwise the joints under the same digit joint are spread evenly
            (0.5 for one, 0.33 and 0.67 for two).
        finger_shape_scale: Optional scale for the finger control shapes. If
            not given it is derived from the length of the digits.
        finger_twist_joints: Optional joints, each parented under a digit
            joint other than the tip, driven by a MultiChainTwisters setup
            along the digit it is in
        finger_cvs_per_segment: How many cvs each finger twist curve has
        debug: Passed to the hand pivot

    Usage:
        arm = FlexiArm(shoulder, wrist, palm_guide, config, "arm", config.left, digits=digits).build()
    """

    IK_TARGET_LABEL = "IkHand"

    def __init__(
            self,
            upper_joint: str,
            hand_joint: str,
            guide_curve: str,
            config: "aniseed.RigConfiguration",
            prefix: str = "",
            location: str = "",
            parent: str = None,
            ik_target_transform: str = None,
            shape_scale: float = None,
            soft_ik: bool = True,
            upper_twist_joints: typing.List[str] = None,
            lower_twist_joints: typing.List[str] = None,
            cvs_per_segment: int = 4,
            rotation_multiplier: float = 2.0,
            rotation_limit: float = 45.0,
            digits: typing.Dict[str, typing.List[str]] = None,
            blend_rotator_joints: typing.List[str] = None,
            finger_shape_scale: float = None,
            finger_twist_joints: typing.List[str] = None,
            finger_cvs_per_segment: int = 3,
            debug: bool = False,
    ):
        super().__init__(
            start_joint=upper_joint,
            end_joint=hand_joint,
            ik_target_transform=ik_target_transform,
            config=config,
            prefix=prefix,
            location=location,
            parent=parent,
            shape_scale=shape_scale,
        )

        self.guide_curve = guide_curve
        self.soft_ik = soft_ik
        self.upper_twist_joints = upper_twist_joints or []
        self.lower_twist_joints = lower_twist_joints or []
        self.cvs_per_segment = cvs_per_segment
        self.rotation_multiplier = rotation_multiplier
        self.rotation_limit = rotation_limit
        self.debug = debug

        self.digits = collections.OrderedDict(
            (label, [mref.get(joint).full_name() for joint in joints])
            for label, joints in (digits or dict()).items()
            if joints
        )
        self.blend_rotator_joints = [mref.get(joint).full_name() for joint in blend_rotator_joints or []]
        self.finger_twist_joints = [mref.get(joint).full_name() for joint in finger_twist_joints or []]
        self.finger_cvs_per_segment = finger_cvs_per_segment
        self.finger_shape_scale = finger_shape_scale or self._digit_length() / 10.0

        # -- Populated by build
        self.pivot: dynamic_pivot.DynamicPivot = None
        self.soft_ik_connection: soft_ik_connection.SoftIkConnection = None
        self.twisters: multi_chain_twists.MultiChainTwisters = None
        self.finger_org: str = ""
        self.fingers: typing.Dict[str, typing.List[au.rig.control.Control]] = collections.OrderedDict()
        self.blend_rotator_org: str = ""
        self.blend_rotators: typing.List[au.rig.control.Control] = []
        self.finger_twisters: typing.Dict[str, multi_chain_twists.MultiChainTwisters] = collections.OrderedDict()

    def build(self) -> "FlexiArm":
        """
        Creates the spring limb with the hand pivot, then the twists, which
        need the blend chain to be driving the joints, then the fingers and
        blend rotators under the blend chain's hand.

        Returns:
            This instance, so the created nodes can be read from it
        """
        super().build()

        self._create_twisters()
        self._create_fingers()
        self._create_blend_rotators()
        self._create_finger_twisters()

        ikfk = f"{self.root_control.ctl}.ikfk"
        controls = [self.pivot.control] + [control for chain in self.fingers.values() for control in chain]
        for control in controls + self.blend_rotators:
            mref.get(control.ctl).add_proxy("ikfk", ikfk)

        cmds.select(clear=True)
        return self

    def _digit_length(self) -> float:
        """
        Returns the length of the longest digit (from its root to its last
        joint), or a tenth of the arm's length if there are no digits with
        more than one joint
        """
        lengths = [
            sum((self._position(b) - self._position(a)).length() for a, b in zip(joints, joints[1:]))
            for joints in self.digits.values()
        ]
        return max(lengths + [0.0]) or self.chain_length / 10.0

    def _create_ik(self):
        """
        Creates the ik chain, then the hand pivot under the ik target control
        and moves the ik handle under the pivot's result. Soft ik is applied
        if enabled.
        """
        super()._create_ik()

        self.pivot = dynamic_pivot.DynamicPivot(
            guide_curve=self.guide_curve,
            config=self.config,
            prefix=self.prefix,
            location=self.location,
            debug=self.debug,
            parent=self.ik_target_control.ctl,
            rotation_multiplier=self.rotation_multiplier,
            rotation_limit=self.rotation_limit,
            align_to_guide=True,
        ).build()

        handle = mref.get(self.ik_handle)
        handle_transform = mref.get(self.ik_handle_transform)
        handle_transform.set_parent(self.pivot.anchor)
        self.ik_handle_transform = handle_transform.full_name()
        self.ik_handle = handle.full_name()

        if self.soft_ik:
            self.soft_ik_connection = soft_ik_connection.SoftIkConnection(
                root=self.root_control.ctl,
                target=self.ik_handle_transform,
                second_joint=self.ik_chain[1],
                third_joint=self.ik_chain[2],
                host=self.ik_target_control.ctl,
                config=self.config,
                prefix=self.prefix,
                location=self.location,
            ).build()

    def _constrain_ik_end(self):
        """
        Makes the ik chain's hand take its rotation from the pivot's result
        """
        mref.orientConstraint(self.pivot.anchor, self.ik_chain[-1], maintainOffset=True)

    def _create_twisters(self):
        """
        Builds a MultiChainTwisters setup from the upper arm to the hand, if
        there are any twist joints, which places each one on the bone it lies
        on. The start of the upper arm holds the roll of the root control, so
        rolling the upper arm spreads a twist along it.
        """
        twist_joints = self.upper_twist_joints + self.lower_twist_joints
        if not twist_joints:
            return

        self.twisters = multi_chain_twists.MultiChainTwisters(
            start_joint=self.joints[0],
            end_joint=self.joints[-1],
            twist_joints=twist_joints,
            cvs_per_segment=self.cvs_per_segment,
            config=self.config,
            prefix=self.prefix,
            location=self.location,
            parent=self.root_control.ctl,
            shape_scale=self.shape_scale,
            root_twist_node=self.root_control.ctl,
        ).build()

    def _create_fingers(self):
        """
        Creates an fk control per digit joint but the tip, each under the
        previous one in its digit and the first under the Fingers org (which
        follows the blend chain's hand), and parent and scale constrains each
        joint to its control. The tip follows the joint it is under.
        """
        if not self.digits:
            return

        self.finger_org = au.scene.transforms.create(
            classification=self.config.organisational,
            description=self._description("Fingers"),
            location=self.location,
            config=self.config,
            parent=self.blend_chain[-1],
            match_to=self.blend_chain[-1],
        )

        for label, joints in self.digits.items():
            shape_rotation = _shape_rotation(joints)
            parent = self.finger_org
            controls = []

            for joint in joints[:-1]:
                control = au.rig.control.create(
                    description=label,
                    location=self.location,
                    parent=parent,
                    shape="core_paddle",
                    config=self.config,
                    match_to=joint,
                    shape_scale=self.finger_shape_scale,
                    rotate_shape=shape_rotation,
                )
                au.scene.constraints.parent_and_scale(control.ctl, joint, maintain_offset=False)

                controls.append(control)
                parent = control.ctl

            self.fingers[label] = controls

    def _create_blend_rotators(self):
        """
        Creates a blend rotator for each blend rotator joint, between the
        control of the digit joint it is parented under and the control of
        the next digit joint. Their controls are hidden unless the root
        control's blendRotatorVisibility is on.
        """
        if not self.blend_rotator_joints:
            return

        self.blend_rotator_org = au.scene.transforms.create(
            classification=self.config.organisational,
            description=self._description("BlendRotators"),
            location=self.location,
            config=self.config,
            parent=self.finger_org,
        )

        visibility = mref.get(self.root_control.ctl).add_attribute(
            "blendRotatorVisibility",
            value=False,
            attribute_type="bool",
            keyable=False,
            defaultValue=False,
        )
        visibility.set(channelBox=True)
        visibility.connect(mref.get(self.blend_rotator_org).attr("visibility"))

        # -- The control of every controlled digit joint, and the controlled
        # -- digit joint after it
        controls = dict()
        following = dict()
        for label, joints in self.digits.items():
            controlled = joints[:-1]
            for idx, joint in enumerate(controlled):
                controls[joint] = self.fingers[label][idx].ctl
                if idx + 1 < len(controlled):
                    following[joint] = (label, controlled[idx + 1])

        # -- The blend rotator joints under each digit joint, in the order given
        siblings = collections.defaultdict(list)
        for joint in self.blend_rotator_joints:
            siblings[mref.get(joint).parent().full_name()].append(joint)

        for joint in self.blend_rotator_joints:
            parent = mref.get(joint).parent().full_name()
            label, next_joint = following[parent]

            m_joint = mref.get(joint)
            if m_joint.has_attribute(BLEND_WEIGHT_ATTRIBUTE):
                blend = m_joint.attr(BLEND_WEIGHT_ATTRIBUTE).get()
            else:
                blend = (siblings[parent].index(joint) + 1.0) / (len(siblings[parent]) + 1.0)

            self.blend_rotators.append(
                au.rig.blend_rotator.create(
                    joint=joint,
                    target_a=controls[parent],
                    target_b=controls[next_joint],
                    description=f"{label}Blend",
                    location=self.location,
                    config=self.config,
                    parent=self.blend_rotator_org,
                    blend=blend,
                    shape_scale=self.finger_shape_scale * 0.5,
                ),
            )

    def _create_finger_twisters(self):
        """
        Builds a MultiChainTwisters setup from the first joint to the tip of
        each digit which has twist joints (each twist joint belonging to the
        digit its parent is in), under the Fingers org. Its controls are
        hidden unless the bendyVisibility attribute on the digit's first
        control is on.
        """
        if not self.finger_twist_joints:
            return

        digit_of = {
            joint: label
            for label, joints in self.digits.items()
            for joint in joints[:-1]
        }

        twist_joints = collections.defaultdict(list)
        for joint in self.finger_twist_joints:
            twist_joints[digit_of[mref.get(joint).parent().full_name()]].append(joint)

        for label, joints in self.digits.items():
            if not twist_joints[label]:
                continue

            twisters = multi_chain_twists.MultiChainTwisters(
                start_joint=joints[0],
                end_joint=joints[-1],
                twist_joints=twist_joints[label],
                cvs_per_segment=self.finger_cvs_per_segment,
                config=self.config,
                prefix=label,
                location=self.location,
                parent=self.finger_org,
                shape_scale=self.finger_shape_scale * 0.5,
            ).build()

            visibility = mref.get(self.fingers[label][0].ctl).add_attribute(
                "bendyVisibility",
                value=False,
                attribute_type="bool",
                keyable=False,
                defaultValue=False,
            )
            visibility.set(channelBox=True)
            visibility.connect(mref.get(twisters.org).attr("visibility"))

            self.finger_twisters[label] = twisters


def _shape_rotation(joints: typing.List[str]) -> typing.List[float]:
    """
    Returns the rotation to give a digit's paddle shapes, as the standard
    hand does: the default for digits running down positive x, switched for
    digits running down negative x (such as a mirrored hand)
    """
    if len(joints) > 1:
        facing = au.scene.joints.get_chain_facing_direction(joints[-2], joints[-1])
        if facing == facing.NegativeX:
            return [0, 0, 90]

    return [90, 90, 0]
