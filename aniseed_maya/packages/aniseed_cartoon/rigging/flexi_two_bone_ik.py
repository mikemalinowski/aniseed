"""
Provides the FlexiTwoBoneIk class, which builds a two bone ik chain with a
one bone ik chain riding on each bone. Each one bone chain is aimed by an fk
style control, so the animator can pose the limb with the ik target and then
push the elbow and wrist around on top of that solve.

The structure built is:

    FlexiTwoBoneIk (org)
        IkRoot (control)
            TwoBoneIk 01 (joint)
                TopFk (control)
                    TopBoneIk 01 -> 02 (joints, solved by the TopBoneIk handle)
                TwoBoneIk 02 (joint)
                    MidFk (control)
                        TopBoneIk (ik handle)
                        BottomBoneIk 01 -> 02 (joints, solved by the BottomBoneIk handle)
                    TwoBoneIk 03 (joint)
                        BottomFk (control)
                            BottomBoneIk (ik handle)
        IKTarget (control, at the ik target guide if one is given)
            IKTargetRest (transform at the wrist)
                TwoBoneIk (ik handle, pole vector constrained to IkUpVector)
        IkUpVector (control)

The MidFk and BottomFk zero nodes are driven through their offsetParentMatrix
so that rotating TopFk swings MidFk (and everything below it) around the TopFk
pivot, and rotating MidFk swings BottomFk around the MidFk pivot. BottomFk's
followIkTarget attribute (default 1) blends its orientation towards the
IKTarget's rotation, so rotating the IKTarget turns the wrist.

If soft_ik is True, a SoftIkConnection drives the lengths of the two bone ik
chain, with its attributes on the IKTarget control.

If twist counts are given, a BendyTwisters setup is also built between the
upper and lower joints and/or between the lower and wrist joints, with its
org under the FlexiTwoBoneIk org.
"""
import typing

from maya.api import OpenMaya as om

import mref
import aniseed_utilities as au
from aniseed_standard.rigging import ik as _ik

from . import bendy_twists
from . import soft_ik_connection

if typing.TYPE_CHECKING:
    import aniseed


class FlexiTwoBoneIk:
    """
    Builds the flexi two bone ik setup for a three joint chain and constrains
    the given joints to it: the upper joint follows the top bone, the lower
    joint follows the bottom bone and the wrist joint follows the BottomFk
    control.

    Args:
        upper_joint: The first joint of the chain (e.g. the upper arm)
        lower_joint: The second joint of the chain (e.g. the lower arm)
        wrist_joint: The last joint of the chain (e.g. the wrist)
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name, so
            "leg" names the two bone chain "LegTwoBoneIk"
        location: The location token (config.left, config.middle etc)
        parent: Optional node to parent the setup's org under (the org is
            matched to it). If not given the org is created at the scene root.
        shape_scale: Optional scale for the control shapes. If not given it
            is derived from the length of the chain.
        upper_twist_count: If given, a BendyTwisters setup with this many
            twist joints is built between the upper and lower joints
        lower_twist_count: If given, a BendyTwisters setup with this many
            twist joints is built between the lower and wrist joints
        upper_twist_joints: Optional existing joints for the upper
            BendyTwisters to drive, instead of creating upper_twist_count
            joints
        lower_twist_joints: Optional existing joints for the lower
            BendyTwisters to drive, instead of creating lower_twist_count
            joints
        soft_ik: If True, soft ik (with stretch) is applied to the two bone
            ik chain, with its attributes on the IKTarget control
        world_space_ik_controls: If True the IkRoot, IKTarget and IkUpVector
            controls are aligned to the world. If False the IkRoot matches
            the upper joint, the IKTarget matches the wrist joint and the
            IkUpVector is aligned to the plane of the chain.
        ik_target_guide: Optional transform to place the IKTarget control at
            (matching its position and rotation, regardless of
            world_space_ik_controls). The ik handle and soft ik still work
            from the wrist, through the IKTargetRest transform under the
            control.

    Usage:
        setup = FlexiTwoBoneIk(upper, lower, wrist, config, "arm", config.left)
        setup.build()
    """

    def __init__(
            self,
            upper_joint: mref.ReferencedItem,
            lower_joint: mref.ReferencedItem,
            wrist_joint: mref.ReferencedItem,
            config: "aniseed.RigConfiguration",
            prefix: str,
            location: str,
            parent: str = None,
            shape_scale: float = None,
            upper_twist_count: int = None,
            lower_twist_count: int = None,
            soft_ik: bool = False,
            world_space_ik_controls: bool = True,
            upper_twist_joints: typing.List[str] = None,
            lower_twist_joints: typing.List[str] = None,
            ik_target_guide: str = None,
    ):
        self.upper_joint = mref.get(upper_joint)
        self.lower_joint = mref.get(lower_joint)
        self.wrist_joint = mref.get(wrist_joint)
        self.config = config
        self.location = location
        self.parent = parent
        self.upper_twist_count = upper_twist_count
        self.lower_twist_count = lower_twist_count
        self.upper_twist_joints = upper_twist_joints or []
        self.lower_twist_joints = lower_twist_joints or []
        self.soft_ik = soft_ik
        self.world_space_ik_controls = world_space_ik_controls
        self.ik_target_guide = ik_target_guide

        # -- "leg" becomes "Leg" so it reads as part of a camel cased description
        self.prefix = prefix[:1].upper() + prefix[1:]

        self.shape_scale = shape_scale or au.scene.joints.chain_length(
            start=self.upper_joint.full_name(),
            end=self.wrist_joint.full_name(),
            log_result=False,
        ) / 30.0

        # -- Populated by build
        self.org: str = ""
        self.ik_root_control: au.rig.control.Control = None
        self.ik_target_control: au.rig.control.Control = None
        self.ik_target_rest: str = ""
        self.upvector_control: au.rig.control.Control = None
        self.top_fk_control: au.rig.control.Control = None
        self.mid_fk_control: au.rig.control.Control = None
        self.bottom_fk_control: au.rig.control.Control = None

        self.two_bone_joints: list[str] = []
        self.top_bone_joints: list[str] = []
        self.bottom_bone_joints: list[str] = []

        self.two_bone_handle: mref.ReferencedItem = None
        self.top_bone_handle: mref.ReferencedItem = None
        self.bottom_bone_handle: mref.ReferencedItem = None

        self.upper_twisters: bendy_twists.BendyTwisters = None
        self.lower_twisters: bendy_twists.BendyTwisters = None
        self.soft_ik_connection: soft_ik_connection.SoftIkConnection = None

    def build(self) -> "FlexiTwoBoneIk":
        """
        Creates the whole setup and constrains the given joints to it.

        Returns:
            This instance, so the created nodes can be read from it
        """
        self._create_org()
        self._create_two_bone_ik()
        self._create_soft_ik()
        self._create_fk_controls()
        self._create_one_bone_iks()
        self._drive_offset_parent_matrices()
        self._constrain_joints()
        self._create_twisters()
        return self

    def _description(self, label: str) -> str:
        """
        Returns the description for the given label with the prefix applied
        """
        return f"{self.prefix}{label}"

    def _create_control(
            self,
            label: str,
            parent: str,
            match_to: str,
            shape: str,
            shape_scale: float,
            rotate_shape=None,
            align_to_world: bool = False,
    ) -> au.rig.control.Control:
        """
        Creates an aniseed control (org, zero, offset and ctl) for the label
        """
        control = au.rig.control.create(
            description=self._description(label),
            location=self.location,
            parent=parent,
            shape=shape,
            config=self.config,
            match_to=match_to,
            shape_scale=shape_scale,
            rotate_shape=rotate_shape,
        )

        if align_to_world:
            mref.get(control.org).set_rotation([0, 0, 0], space="world")

        return control

    def _create_joint_chain(self, label: str, parent: str, match_to: list[str]) -> list[str]:
        """
        Creates a joint for each of the match_to nodes, each one parented
        under the last, with the rotations moved onto the joint orients so
        the ik solve starts from zero rotations.
        """
        chain = []
        for target in match_to:
            chain.append(
                au.scene.joints.create(
                    description=self._description(label),
                    location=self.location,
                    parent=chain[-1] if chain else parent,
                    config=self.config,
                    match_to=target,
                )
            )

        au.scene.joints.move_rotations_to_orients(chain)
        return chain

    def _create_handle(
            self,
            label: str,
            start_joint: str,
            end_joint: str,
            parent: str,
            pole_vector: str,
            cancel_roll: bool = False,
    ):
        """
        Creates a rotate plane ik handle and names the handle and its effector.

        If cancel_roll is True, any roll the pole vector applies to the start
        joint is twisted back out, so the rest pose is unchanged.
        """
        rest_y_axis = om.MVector(mref.get(start_joint).axis_vector("y", space="world"))

        handle = _ik.create_rp_handle(
            start_joint=start_joint,
            end_joint=end_joint,
            parent=parent,
            pole_vector=pole_vector,
        )

        if cancel_roll:
            self._cancel_roll(handle, start_joint, end_joint, rest_y_axis)

        handle.effector().rename(
            self.config.generate_name(
                classification=self.config.mechanical,
                description=self._description(f"{label}Effector"),
                location=self.location,
            ),
        )

        handle.rename(
            self.config.generate_name(
                classification=self.config.mechanical,
                description=self._description(label),
                location=self.location,
            ),
        )
        return handle

    def _create_pole_target(self, label: str, start_joint: str, end_joint: str, parent: str) -> str:
        """
        Creates a transform under the given parent, out along the start
        joint's z axis by half the bone length, to pole vector constrain a
        one bone chain to. The parent therefore owns the roll of the bone.
        """
        joint = mref.get(start_joint)
        start = om.MVector(joint.get_position(space="world"))
        length = (om.MVector(mref.get(end_joint).get_position(space="world")) - start).length()
        z_axis = om.MVector(joint.axis_vector("z", space="world"))

        target = au.scene.transforms.create(
            classification=self.config.mechanical,
            description=self._description(f"{label}PoleVector"),
            location=self.location,
            config=self.config,
            parent=parent,
            match_to=start_joint,
        )
        mref.get(target).set_position(list(start + z_axis * length * 0.5), space="world")
        return target

    @staticmethod
    def _cancel_roll(handle: mref.ReferencedItem, start_joint: str, end_joint: str, rest_y_axis: om.MVector):
        """
        A one bone chain is straight, so maya has no bend to take the rotate
        plane from and falls back to one of the joint's axes. When that axis
        differs from the pole vector the bone rolls on creation, so measure
        that roll around the bone and twist it back out.

        The handle twists around the line from the start joint to the end
        joint, so the roll is measured around that line rather than the
        joint's x axis, which points the other way on mirrored (negative x)
        chains.
        """
        joint = mref.get(start_joint)
        bone_axis = (
            om.MVector(mref.get(end_joint).get_position(space="world")) -
            om.MVector(joint.get_position(space="world"))
        ).normal()
        rolled_y_axis = om.MVector(joint.axis_vector("y", space="world"))
        roll = rolled_y_axis.angle(rest_y_axis)
        if (rolled_y_axis ^ rest_y_axis) * bone_axis < 0:
            roll = -roll

        handle.set_twist(handle.twist() + om.MAngle(roll).asDegrees())

    def _create_org(self):
        """
        Creates the transform which every top level node of the setup lives under
        """
        self.org = au.scene.transforms.create(
            classification=self.config.organisational,
            description=self._description("FlexiTwoBoneIk"),
            location=self.location,
            config=self.config,
            parent=self.parent,
            match_to=self.parent,
        )

    def _create_two_bone_ik(self):
        """
        Creates the IkRoot, IKTarget and IkUpVector controls along with the
        two bone ik chain which they drive. The controls are either aligned
        to the world or to the chain, depending on world_space_ik_controls,
        except the IKTarget which matches the ik target guide if given.

        The ik handle lives under the IKTargetRest transform, which sits at
        the wrist (aligned as the IKTarget would be without a guide), so the
        IKTarget control can be placed anywhere.
        """
        self.ik_root_control = self._create_control(
            label="IkRoot",
            parent=self.org,
            match_to=self.upper_joint.full_name(),
            shape="core_cube",
            shape_scale=self.shape_scale,
            align_to_world=self.world_space_ik_controls,
        )

        self.ik_target_control = self._create_control(
            label="IKTarget",
            parent=self.org,
            match_to=self.ik_target_guide or self.wrist_joint.full_name(),
            shape="core_stumpy_cross",
            shape_scale=self.shape_scale * 2.0,
            align_to_world=self.world_space_ik_controls and not self.ik_target_guide,
        )

        self.ik_target_rest = au.scene.transforms.create(
            classification=self.config.mechanical,
            description=self._description("IKTargetRest"),
            location=self.location,
            config=self.config,
            parent=self.ik_target_control.ctl,
            match_to=self.wrist_joint.full_name(),
        )

        if self.world_space_ik_controls:
            mref.get(self.ik_target_rest).set_rotation([0, 0, 0], space="world")

        self.upvector_control = self._create_control(
            label="IkUpVector",
            parent=self.org,
            match_to=self.lower_joint.full_name(),
            shape="core_sphere",
            shape_scale=self.shape_scale * 0.5,
            align_to_world=True,
        )

        for control in [self.ik_root_control, self.ik_target_control, self.upvector_control]:
            au.scene.shapes.scale(control.ctl, scale_by=2)

        upvector_org = mref.get(self.upvector_control.org)
        upvector_org.set_position(
            au.core.maths.calculate_upvector_position(
                point_a=self.upper_joint.full_name(),
                point_b=self.lower_joint.full_name(),
                point_c=self.wrist_joint.full_name(),
                length=0.5,
            ),
            space="world",
        )

        if not self.world_space_ik_controls:
            upvector_org.set_matrix(list(self._chain_plane_matrix()), space="world")

        self.two_bone_joints = self._create_joint_chain(
            label="TwoBoneIk",
            parent=self.ik_root_control.ctl,
            match_to=[
                self.upper_joint.full_name(),
                self.lower_joint.full_name(),
                self.wrist_joint.full_name(),
            ],
        )

        self.two_bone_handle = self._create_handle(
            label="TwoBoneIk",
            start_joint=self.two_bone_joints[0],
            end_joint=self.two_bone_joints[-1],
            parent=self.ik_target_rest,
            pole_vector=self.upvector_control.ctl,
        )

        au.rig.guide.link(
            self.upvector_control.ctl,
            self.two_bone_joints[1],
        )

    def _create_soft_ik(self):
        """
        If soft ik is enabled, drives the lengths of the two bone ik chain
        from the distance between the IkRoot control and the IKTargetRest
        transform. The fk controls (and so everything riding on them) follow
        the chain.
        """
        if not self.soft_ik:
            return

        self.soft_ik_connection = soft_ik_connection.SoftIkConnection(
            root=self.ik_root_control.ctl,
            target=self.ik_target_rest,
            second_joint=self.two_bone_joints[1],
            third_joint=self.two_bone_joints[2],
            host=self.ik_target_control.ctl,
        ).build()

    def _chain_plane_matrix(self) -> om.MMatrix:
        """
        Returns a world matrix at the IkUpVector org's position, aligned to
        the plane of the chain: x runs along the line from the upper joint to
        the wrist joint, y points towards the up vector and z is the plane's
        normal.

        x and y follow the chain's convention, so they are negated when the
        upper joint's x axis points back up the bone (a behaviour mirrored
        chain), keeping the left and right controls mirrored.
        """
        upper = om.MVector(self.upper_joint.get_position(space="world"))
        lower = om.MVector(self.lower_joint.get_position(space="world"))
        wrist = om.MVector(self.wrist_joint.get_position(space="world"))
        position = om.MVector(mref.get(self.upvector_control.org).get_position(space="world"))

        direction = 1 if om.MVector(self.upper_joint.axis_vector("x", space="world")) * (lower - upper) >= 0 else -1

        x_axis = (wrist - upper).normal()
        y_axis = position - upper
        y_axis = (y_axis - x_axis * (y_axis * x_axis)).normal()
        x_axis *= direction
        y_axis *= direction
        z_axis = (x_axis ^ y_axis).normal()

        return om.MMatrix([
            list(x_axis) + [0],
            list(y_axis) + [0],
            list(z_axis) + [0],
            list(position) + [1],
        ])

    def _create_fk_controls(self):
        """
        Creates the TopFk, MidFk and BottomFk controls, each under the two
        bone ik joint it sits on.
        """
        fk_controls = []

        for label, joint in zip(["TopFk", "MidFk", "BottomFk"], self.two_bone_joints):
            fk_controls.append(
                self._create_control(
                    label=label,
                    parent=joint,
                    match_to=joint,
                    shape="core_circle",
                    shape_scale=self.shape_scale,
                    rotate_shape=[0, 0, 90],
                )
            )

        self.top_fk_control, self.mid_fk_control, self.bottom_fk_control = fk_controls

        for control in fk_controls:
            au.scene.shapes.scale(control.ctl, scale_by=2)

    def _create_one_bone_iks(self):
        """
        Creates the one bone ik chains. The top bone lives under TopFk and
        aims at MidFk, the bottom bone lives under MidFk and aims at BottomFk.

        Each handle is pole vector constrained to a target under the control
        the bone lives under (not the control carrying the handle), so
        TopFk owns the roll of the top bone and MidFk the roll of the bottom
        bone. Rotating a control therefore only re-aims the bone above it.
        """
        self.top_bone_joints, self.top_bone_handle = self._create_one_bone_ik(
            label="TopBoneIk",
            match_to=[self.upper_joint.full_name(), self.lower_joint.full_name()],
            parent_control=self.top_fk_control,
            handle_control=self.mid_fk_control,
        )

        self.bottom_bone_joints, self.bottom_bone_handle = self._create_one_bone_ik(
            label="BottomBoneIk",
            match_to=[self.lower_joint.full_name(), self.wrist_joint.full_name()],
            parent_control=self.mid_fk_control,
            handle_control=self.bottom_fk_control,
        )

    def _create_one_bone_ik(self, label: str, match_to: list[str], parent_control, handle_control):
        """
        Creates a one bone chain (and its pole vector target) under the
        parent control, solved by a handle under the handle control.

        Returns:
            The joint chain and the ik handle
        """
        chain = self._create_joint_chain(
            label=label,
            parent=parent_control.ctl,
            match_to=match_to,
        )

        pole_target = self._create_pole_target(
            label=label,
            start_joint=chain[0],
            end_joint=chain[-1],
            parent=parent_control.ctl,
        )

        handle = self._create_handle(
            label=label,
            start_joint=chain[0],
            end_joint=chain[-1],
            parent=handle_control.ctl,
            pole_vector=pole_target,
            cancel_roll=True,
        )
        return chain, handle

    def _drive_offset_parent_matrices(self):
        """
        Drives the MidFk zero from TopFk and the BottomFk zero from MidFk,
        with BottomFk's orientation blended towards the IKTarget's rotation
        by its followIkTarget attribute.
        """
        mid_offset = self._drive_from_control(self.mid_fk_control, self.top_fk_control, "MidFkOffset")
        mid_offset.attr("matrixSum").connect(f"{self.mid_fk_control.zero}.offsetParentMatrix")

        bottom_offset = self._drive_from_control(self.bottom_fk_control, self.mid_fk_control, "BottomFkOffset")
        follow = self._follow_ik_target_rotation(bottom_offset)
        follow.attr("outputMatrix").connect(f"{self.bottom_fk_control.zero}.offsetParentMatrix")

    def _follow_ik_target_rotation(self, offset: mref.ReferencedItem) -> mref.ReferencedItem:
        """
        Adds the followIkTarget attribute (default 1) to BottomFk and blends
        the given offset matrix towards one which gives BottomFk the IKTarget's
        rotation since rest, applied in world space:

            follow = bottom.org.restWorldMatrix * target.org.worldInverseMatrix
                     * target.ctl.worldMatrix * bottom.org.worldInverseMatrix

        Only the rotation (and scale) is blended, so BottomFk's position
        still comes from the chain and MidFk. At rest the IKTarget has not
        moved, so both matrices match and nothing pops.

        Returns:
            The blendMatrix node
        """
        ctl = self.bottom_fk_control.ctl
        mref.addAttr(
            ctl,
            longName="followIkTarget",
            attributeType="float",
            minValue=0,
            maxValue=1,
            defaultValue=1,
            keyable=True,
        )

        bottom_org = mref.get(self.bottom_fk_control.org)
        target = self.ik_target_control

        follow = mref.create(
            "multMatrix",
            name=self.config.generate_name(
                classification=self.config.mechanical,
                description=self._description("BottomFkFollowIkTarget"),
                location=self.location,
            ),
        )
        follow.attr("matrixIn[0]").set(bottom_org.attr("worldMatrix[0]").get(), type="matrix")
        mref.get(f"{target.org}.worldInverseMatrix[0]").connect(follow.attr("matrixIn[1]"))
        mref.get(f"{target.ctl}.worldMatrix[0]").connect(follow.attr("matrixIn[2]"))
        bottom_org.attr("worldInverseMatrix[0]").connect(follow.attr("matrixIn[3]"))

        blend = mref.create(
            "blendMatrix",
            name=self.config.generate_name(
                classification=self.config.mechanical,
                description=self._description("BottomFkFollowBlend"),
                location=self.location,
            ),
        )
        offset.attr("matrixSum").connect(blend.attr("inputMatrix"))
        follow.attr("matrixSum").connect(blend.attr("target[0].targetMatrix"))
        blend.attr("target[0].translateWeight").set(0)
        mref.get(f"{ctl}.followIkTarget").connect(blend.attr("target[0].weight"))
        return blend

    def _drive_from_control(self, driven, driver, label: str) -> mref.ReferencedItem:
        """
        Creates the multMatrix which, connected to the offsetParentMatrix of
        the driven control's zero, makes it behave as if it were a child of
        the driver control, whilst still living under its ik joint.

            delta  = driver.org.worldInverseMatrix * driver.ctl.worldMatrix
            offset = driven.org.worldMatrix * delta * driven.org.worldInverseMatrix

        The delta is how far the driver control has moved from its rest frame
        (the identity at rest, so nothing moves on build). As the delta reads
        the driver ctl's world matrix it includes any offset the driver itself
        receives, so the chain cascades: TopFk -> MidFk -> BottomFk.
        """
        mult_matrix = mref.create(
            "multMatrix",
            name=self.config.generate_name(
                classification=self.config.mechanical,
                description=self._description(label),
                location=self.location,
            ),
        )

        mref.get(f"{driven.org}.worldMatrix[0]").connect(mult_matrix.attr("matrixIn[0]"))
        mref.get(f"{driver.org}.worldInverseMatrix[0]").connect(mult_matrix.attr("matrixIn[1]"))
        mref.get(f"{driver.ctl}.worldMatrix[0]").connect(mult_matrix.attr("matrixIn[2]"))
        mref.get(f"{driven.org}.worldInverseMatrix[0]").connect(mult_matrix.attr("matrixIn[3]"))
        return mult_matrix

    def _constrain_joints(self):
        """
        Constrains the given joints to the setup
        """
        for driver, driven in [
            (self.top_bone_joints[0], self.upper_joint),
            (self.bottom_bone_joints[0], self.lower_joint),
            (self.bottom_fk_control.ctl, self.wrist_joint),
        ]:
            mref.parentConstraint(driver, driven, maintainOffset=False)
            mref.scaleConstraint(driver, driven, maintainOffset=False)

    def _create_twisters(self):
        """
        Builds a BendyTwisters setup on the upper and/or lower bone, for
        whichever has a twist count.

        The start of the upper twisters holds the roll of the IkRoot control
        rather than the upper bone, so as the pole vector rolls the chain the
        twist spreads along the upper bone.
        """
        if self.upper_twist_count or self.upper_twist_joints:
            self.upper_twisters = self._create_bendy_twisters(
                label="Upper",
                start_joint=self.upper_joint,
                end_joint=self.lower_joint,
                count=self.upper_twist_count,
                start_twist_node=self.ik_root_control.ctl,
                twist_joints=self.upper_twist_joints,
            )

        if self.lower_twist_count or self.lower_twist_joints:
            self.lower_twisters = self._create_bendy_twisters(
                label="Lower",
                start_joint=self.lower_joint,
                end_joint=self.wrist_joint,
                count=self.lower_twist_count,
                twist_joints=self.lower_twist_joints,
            )

    def _create_bendy_twisters(
            self,
            label: str,
            start_joint,
            end_joint,
            count: int,
            start_twist_node: str = None,
            twist_joints: typing.List[str] = None,
    ):
        """
        Builds a BendyTwisters setup between the two joints, under the org
        """
        return bendy_twists.BendyTwisters(
            start_joint=start_joint,
            end_joint=end_joint,
            config=self.config,
            prefix=self._description(label),
            location=self.location,
            count=count or 0,
            parent=self.org,
            shape_scale=self.shape_scale,
            start_twist_node=start_twist_node,
            twist_joints=twist_joints,
        ).build()
