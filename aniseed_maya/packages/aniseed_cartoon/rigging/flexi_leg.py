"""
Provides the FlexiLeg class, an IkfkSpringLimb from the upper leg to the
foot with a DynamicFootPivot driving its ik, a toe which blends between ik
and fk, and optional soft ik and multi chain twists.

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
        MultiChainTwisters (upper leg to foot, if twist joints are given)
"""
import typing

from maya import cmds

import mref
import aniseed_utilities as au
from aniseed_cartoon.rigging import dynamic_pivot
from aniseed_cartoon.rigging import ikfk_spring_limb
from aniseed_cartoon.rigging import multi_chain_twists
from aniseed_cartoon.rigging import soft_ik_connection

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
            to. If not given, it is matched to the foot joint.
        shape_scale: Optional scale for the control shapes. If not given it
            is derived from the length of the chain.
        soft_ik: If True, soft ik (with stretch) is applied to the ik chain,
            with its attributes on the ik target control
        upper_twist_joints: Optional twist joints between the upper and mid
            joints, driven by the multi chain twists
        lower_twist_joints: Optional twist joints between the mid and foot
            joints, driven by the multi chain twists
        cvs_per_segment: How many cvs each multi chain twist curve has
        rotation_multiplier: Passed to the foot pivot
        rotation_limit: Passed to the foot pivot
        debug: Passed to the foot pivot

    Usage:
        leg = FlexiLeg(hip, ankle, ball, foot_guide, config, "leg", config.left).build()
    """

    IK_TARGET_LABEL = "IkFoot"

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
            upper_twist_joints: typing.List[str] = None,
            lower_twist_joints: typing.List[str] = None,
            cvs_per_segment: int = 4,
            rotation_multiplier: float = 2.0,
            rotation_limit: float = 45.0,
            debug: bool = False,
    ):
        super().__init__(
            start_joint=upper_joint,
            end_joint=foot_joint,
            ik_target_transform=ik_target_transform,
            config=config,
            prefix=prefix,
            location=location,
            parent=parent,
            shape_scale=shape_scale,
        )

        self.toe_joint = mref.get(toe_joint).full_name()
        self.guide_curve = guide_curve
        self.soft_ik = soft_ik
        self.upper_twist_joints = upper_twist_joints or []
        self.lower_twist_joints = lower_twist_joints or []
        self.cvs_per_segment = cvs_per_segment
        self.rotation_multiplier = rotation_multiplier
        self.rotation_limit = rotation_limit
        self.debug = debug

        # -- Populated by build
        self.foot_pivot: dynamic_pivot.DynamicFootPivot = None
        self.fk_toe_control: au.rig.control.Control = None
        self.ik_toe: str = ""
        self.soft_ik_connection: soft_ik_connection.SoftIkConnection = None
        self.twisters: multi_chain_twists.MultiChainTwisters = None

    def build(self) -> "FlexiLeg":
        """
        Creates the spring limb with the foot pivot, then the toe blend and
        the twists, which need the blend chain to be driving the joints.

        Returns:
            This instance, so the created nodes can be read from it
        """
        super().build()

        self._blend_toe()
        self._create_twisters()

        ikfk = f"{self.root_control.ctl}.ikfk"
        for control in [
            self.foot_pivot.control,
            self.foot_pivot.heel_control,
            self.foot_pivot.toe_control,
            self.fk_toe_control,
        ]:
            mref.get(control.ctl).add_proxy("ikfk", ikfk)

        cmds.select(clear=True)
        return self

    def _create_fk(self):
        """
        Creates the fk chain and controls, then the FkToe control under the
        fk foot control
        """
        super()._create_fk()

        self.fk_toe_control = self._create_control(
            "FkToe",
            parent=self.fk_controls[-1].ctl,
            shape="core_paddle",
            match_to=self.toe_joint,
            shape_scale=self.shape_scale,
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
        ).build()

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

    def _create_twisters(self):
        """
        Builds a MultiChainTwisters setup from the upper leg to the foot, if
        there are any twist joints, which places each one on the bone it lies
        on. The start of the upper leg holds the roll of the root control, so
        rolling the upper leg spreads a twist along it.
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
