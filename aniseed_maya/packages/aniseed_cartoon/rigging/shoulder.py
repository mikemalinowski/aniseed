"""
Provides the Shoulder class, which builds an fk shoulder (a single bone,
driven only by its control) with an automated scapula. The scapula counters
the shoulder's rotation, and pulls out (back, off the ribcage) as the
shoulder is rotated down and/or back.

The structure built is:

    Shoulder (control, matched to and driving the shoulder joint)
        ShoulderTip (at the end of the shoulder bone, measured for the pull out)
        ScapulaFollow (matched to the scapula, rotating with the shoulder)
        ScapulaCounter (matched to the scapula, its rotation blended between
                        ScapulaFollow and ScapulaStatic)
            ScapulaPull (translated back by the pull out)
                Scapula (control, driving the scapula joint)
    ScapulaStatic (under the Shoulder control's org, so it keeps the
                   orientation of the shoulder's parent)

The scapulaCounter attribute on the Shoulder control (0 to 1) blends the
ScapulaCounter's rotation from following the shoulder (at 0) to keeping the
orientation of the shoulder's parent (at 1), so the scapula counters the
shoulder's rotation. Its position always follows the shoulder.

The pull out reads where the ShoulderTip has moved to from its rest position,
in the space of the Shoulder control's org (which follows the shoulder's
parent). Only the movement down (world -y) and back (world -z) at build time
is counted, and the two are added together:

    pull = (max(0, moved down) + max(0, moved back)) * pull_out_amount * pullOut

The ScapulaPull is moved that far back (world -z at build time, in the
ScapulaCounter's space, so it stays back relative to the shoulder's parent).
The pullOut attribute on the Shoulder control (0 to 1) dials the effect out.
As world down and back are the same for either side, a mirrored shoulder
behaves the same way.

Both attributes are proxied onto the Scapula control.
"""
import typing

from maya import cmds
from maya.api import OpenMaya as om

import mref
import aniseed_utilities as au

if typing.TYPE_CHECKING:
    import aniseed


# -- The world directions, at build time, the pull out measures and pushes along
_DOWN = (0, -1, 0)
_BACK = (0, 0, -1)


class Shoulder:
    """
    Builds the shoulder and scapula.

    Args:
        shoulder_joint: The shoulder joint
        shoulder_end: The joint at the end of the shoulder bone (such as the
            upper arm), which the pull out measures
        scapula_joint: The scapula joint
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name
        location: The location token (config.left, config.middle etc)
        parent: Optional node to parent the Shoulder control under
        pull_out_amount: How far the scapula pulls out for each unit the
            shoulder's end moves down and back
        shape_scale: Optional scale for the control shapes. If not given it
            is derived from the length of the shoulder bone.

    Usage:
        shoulder = Shoulder(clavicle, upper_arm, scapula, config, "Shoulder", config.left).build()
        mref.parentConstraint(shoulder.shoulder_control.ctl, arm_root, maintainOffset=True)
    """

    def __init__(
            self,
            shoulder_joint: str,
            shoulder_end: str,
            scapula_joint: str,
            config: "aniseed.RigConfiguration",
            prefix: str = "",
            location: str = "",
            parent: str = None,
            pull_out_amount: float = 0.15,
            shape_scale: float = None,
    ):
        self.shoulder_joint = mref.get(shoulder_joint).full_name()
        self.shoulder_end = mref.get(shoulder_end).full_name()
        self.scapula_joint = mref.get(scapula_joint).full_name()
        self.config = config
        self.location = location
        self.parent = parent
        self.pull_out_amount = pull_out_amount

        # -- "shoulder" becomes "Shoulder" so it reads as part of a camel cased description
        self.prefix = prefix[:1].upper() + prefix[1:]

        self.length = (_position(self.shoulder_end) - _position(self.shoulder_joint)).length()
        self.shape_scale = shape_scale or self.length

        # -- Populated by build
        self.shoulder_control: au.rig.control.Control = None
        self.scapula_control: au.rig.control.Control = None
        self.tip: str = ""
        self.scapula_follow: str = ""
        self.scapula_static: str = ""
        self.scapula_counter: str = ""
        self.scapula_pull: str = ""

    def build(self) -> "Shoulder":
        """
        Creates the shoulder, the scapula counter and the pull out.

        Returns:
            This instance, so the created nodes can be read from it
        """
        self._create_shoulder()
        self._create_scapula()
        self._create_pull_out()

        for attribute in ["scapulaCounter", "pullOut"]:
            mref.get(self.scapula_control.ctl).add_proxy(attribute, f"{self.shoulder_control.ctl}.{attribute}")

        au.scene.constraints.parent_and_scale(self.shoulder_control.ctl, self.shoulder_joint)
        au.scene.constraints.parent_and_scale(self.scapula_control.ctl, self.scapula_joint)

        cmds.select(clear=True)
        return self

    def _description(self, label: str) -> str:
        return f"{self.prefix}{label}"

    def _name(self, classification: str, label: str) -> str:
        return self.config.generate_name(
            classification=classification,
            description=self._description(label),
            location=self.location,
        )

    def _create_transform(self, label: str, parent: str, match_to: str) -> str:
        return mref.get(
            au.scene.transforms.create(
                classification=self.config.mechanical,
                description=self._description(label),
                location=self.location,
                config=self.config,
                parent=parent,
                match_to=match_to,
            ),
        ).full_name()

    def _create_node(self, node_type: str, label: str) -> str:
        return cmds.createNode(node_type, name=self._name(self.config.mechanical, label))

    def _create_shoulder(self):
        """
        Creates the Shoulder control with the scapulaCounter and pullOut
        attributes, and the ShoulderTip
        """
        # -- The control is named by the prefix alone (falling back to
        # -- "Shoulder"), so the default prefix does not give "ShoulderShoulder"
        self.shoulder_control = au.rig.control.create(
            description=self.prefix or "Shoulder",
            location=self.location,
            parent=self.parent,
            shape="core_paddle",
            config=self.config,
            match_to=self.shoulder_joint,
            shape_scale=self.shape_scale * 0.5,
            rotate_shape=[0, 0, 90],
        )

        ctl = mref.get(self.shoulder_control.ctl)
        for attribute in ["scapulaCounter", "pullOut"]:
            ctl.add_attribute(attribute, value=1.0, attribute_type="float", keyable=True, min=0, max=1, defaultValue=1)

        self.tip = self._create_transform("ShoulderTip", self.shoulder_control.ctl, self.shoulder_end)

    def _create_scapula(self):
        """
        Creates the ScapulaFollow and ScapulaStatic, the ScapulaCounter whose
        rotation is blended between them by scapulaCounter, the ScapulaPull
        under it and the Scapula control under that
        """
        self.scapula_follow = self._create_transform("ScapulaFollow", self.shoulder_control.ctl, self.scapula_joint)
        self.scapula_static = self._create_transform("ScapulaStatic", self.shoulder_control.org, self.scapula_joint)
        self.scapula_counter = self._create_transform("ScapulaCounter", self.shoulder_control.ctl, self.scapula_joint)

        mref.orientConstraint(self.scapula_follow, self.scapula_counter, maintainOffset=True)
        constraint = mref.orientConstraint(self.scapula_static, self.scapula_counter, maintainOffset=True)[0]
        constraint.attr("interpType").set(2)  # -- Shortest

        reverse = au.scene.constraints.blend_weights(f"{self.shoulder_control.ctl}.scapulaCounter", constraint)
        reverse.rename(self._name(self.config.mechanical, "ScapulaCounterReverse"))

        self.scapula_pull = self._create_transform("ScapulaPull", self.scapula_counter, self.scapula_joint)

        self.scapula_control = au.rig.control.create(
            description=self._description("Scapula"),
            location=self.location,
            parent=self.scapula_pull,
            shape="core_rounded_square",
            config=self.config,
            match_to=self.scapula_joint,
            shape_scale=self.shape_scale * 0.4,
        )

    def _create_pull_out(self):
        """
        Drives the ScapulaPull's translation back by how far the ShoulderTip
        has moved down and back from its rest position
        """
        org = self.shoulder_control.org
        to_org = om.MMatrix(cmds.getAttr(f"{org}.worldInverseMatrix[0]"))

        # -- The tip's position in the org's space
        tip_matrix = self._create_node("multMatrix", "ShoulderTipInOrg")
        cmds.connectAttr(f"{self.tip}.worldMatrix[0]", f"{tip_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{org}.worldInverseMatrix[0]", f"{tip_matrix}.matrixIn[1]")

        tip_position = self._create_node("decomposeMatrix", "ShoulderTipPosition")
        cmds.connectAttr(f"{tip_matrix}.matrixSum", f"{tip_position}.inputMatrix")

        rest = om.MPoint(_position(self.tip)) * to_org
        moved = self._create_node("plusMinusAverage", "ShoulderTipMoved")
        cmds.setAttr(f"{moved}.operation", 2)  # -- Subtract
        cmds.connectAttr(f"{tip_position}.outputTranslate", f"{moved}.input3D[0]")
        cmds.setAttr(f"{moved}.input3D[1]", rest.x, rest.y, rest.z)

        # -- How far it has moved down and back, in world terms at build time
        clamp = self._create_node("clamp", "ScapulaPullDownBack")
        cmds.setAttr(f"{clamp}.max", 1e6, 1e6, 0)
        for label, world_direction, channel in [("Down", _DOWN, "R"), ("Back", _BACK, "G")]:
            direction = om.MVector(*world_direction) * to_org
            dot = self._create_node("vectorProduct", f"ShoulderMoved{label}")
            cmds.setAttr(f"{dot}.operation", 1)  # -- Dot product
            cmds.connectAttr(f"{moved}.output3D", f"{dot}.input1")
            cmds.setAttr(f"{dot}.input2", direction.x, direction.y, direction.z)
            cmds.connectAttr(f"{dot}.outputX", f"{clamp}.input{channel}")

        total = self._create_node("plusMinusAverage", "ScapulaPullTotal")
        cmds.connectAttr(f"{clamp}.outputR", f"{total}.input1D[0]")
        cmds.connectAttr(f"{clamp}.outputG", f"{total}.input1D[1]")

        # -- Scaled by the pullOut alpha
        alpha = self._create_node("multiplyDivide", "ScapulaPullAlpha")
        cmds.connectAttr(f"{total}.output1D", f"{alpha}.input1X")
        cmds.connectAttr(f"{self.shoulder_control.ctl}.pullOut", f"{alpha}.input2X")

        # -- Back (in the ScapulaCounter's space) by the amount
        to_counter = om.MMatrix(cmds.getAttr(f"{self.scapula_counter}.worldInverseMatrix[0]"))
        back = (om.MVector(*_BACK) * to_counter).normal() * self.pull_out_amount
        offset = self._create_node("multiplyDivide", "ScapulaPullOffset")
        cmds.setAttr(f"{offset}.input1", back.x, back.y, back.z)
        for axis in "XYZ":
            cmds.connectAttr(f"{alpha}.outputX", f"{offset}.input2{axis}")
        cmds.connectAttr(f"{offset}.output", f"{self.scapula_pull}.translate")


def _position(node: str) -> om.MVector:
    return om.MVector(cmds.xform(node, query=True, translation=True, worldSpace=True))
