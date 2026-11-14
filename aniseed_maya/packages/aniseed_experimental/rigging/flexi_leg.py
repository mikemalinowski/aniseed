"""
Provides the FlexiLeg class, an IkfkSpringLimb from the upper leg to the
foot with a DynamicFootPivot driving its ik, a toe which blends between ik
and fk, and optional soft ik.

The dynamic foot pivot sits under the ik target control, and the spring ik
handle follows its FootResult, so rocking the pivot or rolling the heel
carries the leg with it. The ik chain's foot joint takes its rotation from
the FootResult and its position from the ik chain, so the given foot joint
follows the spring limb's blend chain like the upper and mid joints, whether
in ik or fk.

The toe is the one joint beyond the spring limb's chain. In ik it follows the
pivot's Toe control (through an IkToe under the ik chain's foot) and in fk the
FkToe control under the fk foot control, blended by the root control's ikfk.

Added to the IkfkSpringLimb structure:

    SpringRoot
        SpringFk 03 (the fk foot)
            FkToe (control)
        IkFoot (the ik target control)
            PivotSetup (the DynamicFootPivot)
                ... FootResult
                    SpringIkHandleTransform (moved here from the ik target)
        SpringIkChain
            ... foot (rotation from the FootResult)
                IkToe (rotation from the pivot's Toe control)

The ik target control (IkFoot) is matched to the guide curve unless an ik
target transform is given, and its shape is an outline of the guide curve
where it sits in world space (an even gap outside it, 15% bigger). If
show_detailed_controls is set, a ShowDetailedControls attribute (off by
default) is added to the root control and proxied to every ik and fk
control, for other components (such as twists) to drive the visibility of
their controls with.
"""
import math
import typing

from maya import cmds
from maya.api import OpenMaya as om

import mref
import aniseed_utilities as au
from aniseed_experimental.rigging import dynamic_pivot
from aniseed_experimental.rigging import ikfk_spring_limb
from aniseed_experimental.rigging import soft_ik_connection

if typing.TYPE_CHECKING:
    import aniseed


class FlexiLeg(ikfk_spring_limb.IkfkSpringLimb):
    """
    Builds the flexi leg on an upper, mid, foot and toe joint.

    Args:
        upper_joint: The upper leg joint
        foot_joint: The foot joint, which must be below the upper joint with
            the mid leg joint between them
        toe_joint: The toe joint, below the foot joint
        guide_curve: The curve the foot pivot slides along (see
            dynamic_pivot.DynamicPivot)
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name
        location: The location token (config.left, config.middle etc)
        parent: Optional node to parent the root control under
        ik_target_transform: Optional node to match the ik target control
            to. If not given, it is matched to the guide curve.
        pivot_control_transform: Optional node to match the pivot control's
            org to (position and rotation)
        invert_pivot_z: Passed to the foot pivot as invert_z, inverting the
            pivot control's z rotation
        shape_scale: Optional scale for the control shapes. If not given it
            is derived from the length of the chain.
        soft_ik: If True, soft ik (with stretch) is applied to the ik chain,
            with its attributes on the ik target control
        show_detailed_controls: If True, the ShowDetailedControls attribute
            is added to the root control and proxied to every ik and fk
            control
        rotation_multiplier: Passed to the foot pivot
        rotation_limit: Passed to the foot pivot
        debug: Passed to the foot pivot

    Usage:
        leg = FlexiLeg(hip, ankle, ball, foot_guide, config, "leg", config.left).build()
    """

    IK_TARGET_LABEL = "IkFoot"

    # -- The attribute on the root control which other components (such as
    # -- twists) drive the visibility of their controls with
    SHOW_DETAILED_CONTROLS = "ShowDetailedControls"

    def __init__(
            self,
            upper_joint: str,
            foot_joint: str,
            toe_joint: str,
            guide_curve: str,
            config: "aniseed.RigConfiguration",
            prefix: str = "",
            location: str = "",
            parent: str = None,
            ik_target_transform: str = None,
            shape_scale: float = None,
            soft_ik: bool = True,
            show_detailed_controls: bool = False,
            rotation_multiplier: float = 2.0,
            rotation_limit: float = 45.0,
            debug: bool = False,
            pivot_control_transform: str = None,
            invert_pivot_z: bool = False,
    ):
        super().__init__(
            start_joint=upper_joint,
            end_joint=foot_joint,
            ik_target_transform=ik_target_transform or guide_curve,
            config=config,
            prefix=prefix,
            location=location,
            parent=parent,
            shape_scale=shape_scale,
        )

        self.toe_joint = mref.get(toe_joint).full_name()
        self.guide_curve = guide_curve
        self.soft_ik = soft_ik
        self.show_detailed_controls = show_detailed_controls
        self.rotation_multiplier = rotation_multiplier
        self.rotation_limit = rotation_limit
        self.debug = debug
        self.pivot_control_transform = pivot_control_transform
        self.invert_pivot_z = invert_pivot_z

        # -- Populated by build
        self.foot_pivot: dynamic_pivot.DynamicFootPivot = None
        self.fk_toe_control: au.rig.control.Control = None
        self.ik_toe: str = ""
        self.soft_ik_connection: soft_ik_connection.SoftIkConnection = None

    def build(self) -> "FlexiLeg":
        """
        Creates the spring limb with the foot pivot, then the toe blend, which
        needs the blend chain to be driving the joints.

        Returns:
            This instance, so the created nodes can be read from it
        """
        super().build()

        self._blend_toe()

        ikfk = f"{self.root_control.ctl}.ikfk"
        for control in [
            self.foot_pivot.control,
            self.foot_pivot.heel_control,
            self.foot_pivot.toe_control,
            self.fk_toe_control,
        ]:
            mref.get(control.ctl).add_proxy("ikfk", ikfk)

        if self.show_detailed_controls:
            self._create_detailed_visibility()

        cmds.select(clear=True)
        return self

    def _create_root(self):
        """
        Creates the root control, with a sphere shape
        """
        super()._create_root()
        _set_shape(self.root_control, "core_sphere", 8)

    def _create_fk(self):
        """
        Creates the fk chain and controls, then the FkToe control under the
        fk foot control. Every fk control has a rounded square shape.
        """
        super()._create_fk()

        for control in self.fk_controls:
            _set_shape(control, "core_rounded_square", 14, rotate=[0, 0, 90])

        self.fk_toe_control = self._create_control(
            "FkToe",
            parent=self.fk_controls[-1].ctl,
            shape="core_rounded_square",
            match_to=self.toe_joint,
            shape_scale=14,
            rotate_shape=[0, 0, 90],
        )

    def _create_ik(self):
        """
        Creates the ik chain, then the foot pivot under the ik target control,
        moves the ik handle under the pivot's FootResult and creates the
        IkToe. Soft ik is applied if enabled.
        """
        super()._create_ik()

        self.foot_pivot = dynamic_pivot.DynamicFootPivot(
            guide_curve=self.guide_curve,
            config=self.config,
            prefix=self.prefix,
            location=self.location,
            foot=self.joints[-1],
            toe=self.toe_joint,
            debug=self.debug,
            parent=self.ik_target_control.ctl,
            rotation_multiplier=self.rotation_multiplier,
            rotation_limit=self.rotation_limit,
            invert_z=self.invert_pivot_z,
        ).build()

        dynamic_pivot.set_rotator_shape(self.foot_pivot.control)
        if self.pivot_control_transform:
            cmds.matchTransform(self.foot_pivot.control.org, self.pivot_control_transform, position=True, rotation=True)

        _set_world_shape_offset(self.guide_curve, self.ik_target_control.ctl, growth=0.15)
        _set_shape(self.foot_pivot.heel_control, "core_saddle", 6)

        handle = mref.get(self.ik_handle)
        handle_transform = mref.get(self.ik_handle_transform)
        handle_transform.set_parent(self.foot_pivot.foot_anchor)
        self.ik_handle_transform = handle_transform.full_name()
        self.ik_handle = handle.full_name()

        self.ik_toe = au.scene.transforms.create(
            classification=self.config.mechanical,
            description=self._description("IkToe"),
            location=self.location,
            config=self.config,
            parent=self.ik_chain[-1],
            match_to=self.toe_joint,
        )
        mref.orientConstraint(self.foot_pivot.toe_control.ctl, self.ik_toe, maintainOffset=True)

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
        Makes the ik chain's foot take its rotation from the pivot's
        FootResult
        """
        mref.orientConstraint(self.foot_pivot.foot_anchor, self.ik_chain[-1], maintainOffset=True)

    def _blend_toe(self):
        """
        Constrains the toe joint between the IkToe (at 0) and the FkToe
        control (at 1), blended by the root control's ikfk
        """
        mref.parentConstraint(self.ik_toe, self.toe_joint, maintainOffset=True)
        constraint = mref.parentConstraint(self.fk_toe_control.ctl, self.toe_joint, maintainOffset=True)[0]
        constraint.attr("interpType").set(2)  # -- Shortest

        reverse = au.scene.constraints.blend_weights(f"{self.root_control.ctl}.ikfk", constraint)
        reverse.rename(self._name(self.config.mechanical, "ToeIkFkReverse"))

    def _create_detailed_visibility(self):
        """
        Adds the ShowDetailedControls attribute to the root control (off by
        default) and proxies it to every ik and fk control.
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
            self.fk_toe_control,
            self.ik_target_control,
            self.pole_vector_control,
            self.foot_pivot.control,
            self.foot_pivot.heel_control,
            self.foot_pivot.toe_control,
        ]:
            mref.get(control.ctl).add_proxy(
                self.SHOW_DETAILED_CONTROLS,
                f"{self.root_control.ctl}.{self.SHOW_DETAILED_CONTROLS}",
            )


def _set_shape(control: au.rig.control.Control, shape: str, scale: float, rotate: typing.List[float] = None):
    """
    Replaces the control's shape, scaled and optionally rotated, as
    au.rig.control.create applies one
    """
    au.scene.shapes.load_shape(control.ctl, shape)
    au.scene.shapes.scale(control.ctl, scale_by=scale)
    if rotate:
        au.scene.shapes.rotate(control.ctl, *rotate)


def _set_world_shape(source: str, target: str):
    """
    Gives the target the curve shapes of the source, keeping them where they
    sit in world space
    """
    to_target = (
        om.MMatrix(cmds.xform(source, query=True, matrix=True, worldSpace=True)) *
        om.MMatrix(cmds.xform(target, query=True, matrix=True, worldSpace=True)).inverse()
    )

    data = au.scene.shapes.shape_to_dict(source)
    for curve in data["curves"]:
        curve["cvs"] = [list(om.MPoint(cv) * to_target)[:3] for cv in curve["cvs"]]

    au.scene.shapes.load_shape(target, data)


def _set_world_shape_offset(source: str, target: str, growth: float):
    """
    Gives the target an outline of the source curve, an even gap outside it,
    keeping it where it sits in world space. The gap is sized so a circle
    would grow by the given fraction (0.15 is 15% bigger), which is the
    perimeter times growth over 2 pi.
    """
    length = cmds.arclen(source)
    distance = length * growth / (2 * math.pi)

    # -- Which side a positive distance offsets to depends on the curve's
    # -- direction, so if it came out shorter it went inwards and is redone
    outline = cmds.offsetCurve(source, distance=distance, useGivenNormal=True, normal=(0, 1, 0), constructionHistory=False)
    if cmds.arclen(outline[0]) < length:
        cmds.delete(outline)
        outline = cmds.offsetCurve(source, distance=-distance, useGivenNormal=True, normal=(0, 1, 0), constructionHistory=False)

    # -- The offset curves are created in world space under identity transforms
    _set_world_shape(outline[0], target)
    cmds.delete(outline)
