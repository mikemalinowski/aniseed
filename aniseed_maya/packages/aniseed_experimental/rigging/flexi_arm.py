"""
Provides the FlexiArm class, an IkfkSpringLimb from the upper arm to the hand
with a pivot control on the hand driving its ik, optional soft ik, and fk
fingers with optional blend rotators at the knuckles.

The pivot control sits under the ik target control (at the pivot control
transform if one is given, otherwise at the ik target), and the spring ik
handle sits under the pivot control, so rotating the pivot control turns the
hand about that point and carries the arm with it. The ik chain's hand joint
takes its rotation from the pivot control and its position from the ik
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
its bones. Its controls are hidden unless the ShowDetailedFingerControls
attribute on the digit's first control (proxied to the digit's other
controls) is on.

Added to the IkfkSpringLimb structure:

    SpringRoot
        IkHand (the ik target control)
            IkHandPivot (the pivot control)
                SpringIkHandleTransform (moved here from the ik target)
        SpringIkChain
            ... hand (rotation from the pivot control)
        SpringBlendChain
            ... hand
                Fingers (org)
                    <Digit> controls, each under the previous one
                    BlendRotators (org, visibility from the root control)
                        <Digit>Blend controls
                    <Digit>MultiChainTwisters (per digit with twist joints,
                        visibility from the digit's first control)

If show_detailed_controls is set, a ShowDetailedControls attribute (off by
default) is added to the root control and proxied to the ik, fk and pivot
controls, for other components (such as twists) to drive the visibility of
their controls with.
"""
import typing
import collections

from maya import cmds

import mref
import aniseed_utilities as au
from aniseed_experimental.rigging import dynamic_pivot
from aniseed_experimental.rigging import ikfk_spring_limb
from aniseed_experimental.rigging import multi_chain_twists
from aniseed_experimental.rigging import soft_ik_connection

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
        show_detailed_controls: If True, the ShowDetailedControls attribute
            is added to the root control and proxied to the ik, fk and pivot
            controls
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
        pivot_control_transform: Optional node to match the pivot control
            to (position and rotation). If not given, it is matched to the
            ik target control.

    Usage:
        arm = FlexiArm(shoulder, wrist, config, "arm", config.left, digits=digits).build()
    """

    IK_TARGET_LABEL = "IkHand"

    # -- The attribute on the root control which other components (such as
    # -- twists) drive the visibility of their controls with
    SHOW_DETAILED_CONTROLS = "ShowDetailedControls"

    # -- The attribute on each digit's first control (proxied to the rest of
    # -- the digit's controls) which shows that digit's twist controls
    SHOW_DETAILED_FINGER_CONTROLS = "ShowDetailedFingerControls"

    # -- The scale of the fingers' multi chain twist key (paddle) and cv
    # -- (lollipop) control shapes
    FINGER_TWIST_SHAPE_SCALE = 6

    def __init__(
            self,
            upper_joint: str,
            hand_joint: str,
            config: "aniseed.RigConfiguration",
            prefix: str = "",
            location: str = "",
            parent: str = None,
            ik_target_transform: str = None,
            shape_scale: float = None,
            soft_ik: bool = True,
            show_detailed_controls: bool = False,
            digits: typing.Dict[str, typing.List[str]] = None,
            blend_rotator_joints: typing.List[str] = None,
            finger_shape_scale: float = None,
            finger_twist_joints: typing.List[str] = None,
            finger_cvs_per_segment: int = 3,
            pivot_control_transform: str = None,
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

        self.soft_ik = soft_ik
        self.show_detailed_controls = show_detailed_controls
        self.pivot_control_transform = pivot_control_transform

        self.digits =collections.OrderedDict(
            (label, [mref.get(joint).full_name() for joint in joints])
            for label, joints in (digits or dict()).items()
            if joints
        )
        self.blend_rotator_joints = [mref.get(joint).full_name() for joint in blend_rotator_joints or []]
        self.finger_twist_joints = [mref.get(joint).full_name() for joint in finger_twist_joints or []]
        self.finger_cvs_per_segment = finger_cvs_per_segment
        self.finger_shape_scale = finger_shape_scale or self._digit_length() / 10.0

        # -- Populated by build
        self.pivot_control: au.rig.control.Control = None
        self.soft_ik_connection: soft_ik_connection.SoftIkConnection = None
        self.finger_org: str = ""
        self.fingers: typing.Dict[str, typing.List[au.rig.control.Control]] = collections.OrderedDict()
        self.blend_rotator_org: str = ""
        self.blend_rotators: typing.List[au.rig.control.Control] = []
        self.finger_twisters: typing.Dict[str, multi_chain_twists.MultiChainTwisters] = collections.OrderedDict()

    def build(self) -> "FlexiArm":
        """
        Creates the spring limb with the pivot control, then the fingers,
        blend rotators and finger twists under the blend chain's hand.

        Returns:
            This instance, so the created nodes can be read from it
        """
        super().build()

        self._create_fingers()
        self._create_blend_rotators()
        self._create_finger_twisters()

        ikfk = f"{self.root_control.ctl}.ikfk"
        controls = [self.pivot_control] +[control for chain in self.fingers.values() for control in chain]
        for control in controls + self.blend_rotators:
            mref.get(control.ctl).add_proxy("ikfk", ikfk)

        if self.show_detailed_controls:
            self._create_detailed_visibility()

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
        Creates the ik chain, then the pivot control under the ik target
        control (at the pivot control transform, or the ik target if not
        given) and moves the ik handle under it. Soft ik is applied if
        enabled.
        """
        super()._create_ik()

        self.pivot_control = self._create_control(
            "IkHandPivot",
            parent=self.ik_target_control.ctl,
            shape="core_circle",
            match_to=self.pivot_control_transform or self.ik_target_control.ctl,
        )
        dynamic_pivot.set_rotator_shape(self.pivot_control)

        handle = mref.get(self.ik_handle)
        handle_transform = mref.get(self.ik_handle_transform)
        handle_transform.set_parent(self.pivot_control.ctl)
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
        Makes the ik chain's hand take its rotation from the pivot control
        """
        mref.orientConstraint(self.pivot_control.ctl,self.ik_chain[-1], maintainOffset=True)

    def _create_detailed_visibility(self):
        """
        Adds the ShowDetailedControls attribute to the root control (off by
        default) and proxies it to the ik, fk and pivot controls.
        """
        show = mref.get(self.root_control.ctl).add_attribute(
            self.SHOW_DETAILED_CONTROLS,
            value=False,
            attribute_type="bool",
            keyable=False,
            defaultValue=False,
        )
        show.set(channelBox=True)

        for control in self.fk_controls + [
            self.ik_target_control,
            self.pole_vector_control,
            self.pivot_control,
        ]:
            mref.get(control.ctl).add_proxy(
                self.SHOW_DETAILED_CONTROLS,
                f"{self.root_control.ctl}.{self.SHOW_DETAILED_CONTROLS}",
            )

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
                    shape="core_rounded_square",
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
        hidden unless the ShowDetailedFingerControls attribute on the digit's
        first control is on, which every other control of the digit carries
        as a proxy.
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

            # -- Styled as the arm's twist controls, at a quarter of their size
            # -- and turned 90 in x
            for control in twisters.key_controls:
                _set_shape(control, "core_paddle", self.FINGER_TWIST_SHAPE_SCALE, rotate=[90, 0, 0])

            for controls in twisters.cv_controls:
                for control in controls:
                    _set_shape(control, "core_lollipop", self.FINGER_TWIST_SHAPE_SCALE, rotate=[90, 0, 0])

            first, *others = self.fingers[label]
            visibility = mref.get(first.ctl).add_attribute(
                self.SHOW_DETAILED_FINGER_CONTROLS,
                value=False,
                attribute_type="bool",
                keyable=False,
                defaultValue=False,
            )
            visibility.set(channelBox=True)
            visibility.connect(mref.get(twisters.org).attr("visibility"))

            # -- So it can be switched from any control of the digit
            for control in others:
                mref.get(control.ctl).add_proxy(
                    self.SHOW_DETAILED_FINGER_CONTROLS,
                    f"{first.ctl}.{self.SHOW_DETAILED_FINGER_CONTROLS}",
                )

            self.finger_twisters[label] = twisters


def _set_shape(control: au.rig.control.Control, shape: str, scale: float, rotate: typing.List[float] = None):
    """
    Replaces the control's shape, scaled and optionally rotated, as
    au.rig.control.create applies one
    """
    au.scene.shapes.load_shape(control.ctl, shape)
    au.scene.shapes.scale(control.ctl, scale_by=scale)
    if rotate:
        au.scene.shapes.rotate(control.ctl, *rotate)


def _shape_rotation(joints: typing.List[str]) -> typing.List[float]:
    """
    Returns the rotation to give a digit's control shapes, as the standard
    hand does: the default for digits running down positive x, switched for
    digits running down negative x (such as a mirrored hand)
    """
    if len(joints) > 1:
        facing = au.scene.joints.get_chain_facing_direction(joints[-2], joints[-1])
        if facing == facing.NegativeX:
            return [0, 0, 90]

    return [90, 90, 0]
