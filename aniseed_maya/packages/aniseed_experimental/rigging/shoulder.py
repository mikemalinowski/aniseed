"""
Provides the Shoulder class, which builds an fk shoulder (a single bone,
driven only by its control) with an automated scapula.

The scapula only ever turns about the vertical axis (of the shoulder's
parent, at build time), so as the shoulder rotates up and down it stays
upright with the spine. How it follows the shoulder:

    * Turning forward (the scapula moving away from the spine) it follows
      the shoulder like a child, in position and turn.
    * Turning back (the scapula moving toward the spine) it slides along the
      same path a child would, progressively slower, easing to a stop at the
      Retract Limit toward the spine. It also turns out about its own -y,
      building steadily to the Retract Turn at the limit.
    * Twisting the shoulder (about its control's x) does not move it, as it
      is tracked from the shoulder's swing alone (an aim at a point on the
      control's x, keeping the parent's up).
    * Rotating up and down it rises and falls with the shoulder without
      swinging out sideways. It is tracked from a point on the swing at
      its horizontal position but at the shoulder's height, and hangs below
      that point by its rest drop in the parent's space, so the drop below
      the shoulder does not act as a lever.

Nothing reads rotation values: everything is driven by distances, and the
turn is an aim constraint at the scapula's driven position.

The structure built is:

    Shoulder (control, matched to and driving the shoulder joint)
        ShoulderTip (along the control's x, its twist axis)
        ScapulaFollow (matched to the scapula, a plain child of the shoulder)
    ShoulderSpace (at the shoulder, world aligned at build, under the
                   Shoulder control's org so it follows the shoulder's
                   parent, and point constrained to the Shoulder control)
        ShoulderSwing (aimed at the ShoulderTip keeping the parent's up, so
                       it swings with the shoulder but ignores its twist)
            ScapulaHeight (at the scapula's horizontal position, the
                           shoulder's height)
        ScapulaTrack (at the ScapulaHeight, dropped to the scapula's height)
        ScapulaPoint (the driven position, flattened onto the shoulder's height)
        ScapulaHeading (at the shoulder, aimed at the ScapulaPoint)
        ScapulaPosition (at the driven position, oriented by the ScapulaHeading)
            ScapulaTurnOutOrg (matched to the scapula)
                ScapulaTurnOut (rotateY driven out as it retracts)
        ScapulaBlend (blended between ScapulaFollow and ScapulaTurnOut)
            Scapula (control, driving the scapula joint)

In the ShoulderSpace (whose origin is the shoulder, and whose x is world x at
build) the ScapulaTrack moves around the shoulder on a circle, its translateX
being its horizontal distance from the spine plus a constant. How far it has
moved toward the spine (d) is remapped to a fraction (t) of twice the Retract
Limit (a remapValue, whose curve can be reshaped), and eased to
f = limit * t * (2 - t), which follows d exactly at first and slows to a stop
at the limit. The driven position is then the point on the ScapulaTrack's own
circle at the eased distance:

    x = track x + outward * (d - f)
    z = track z + |track z| - sqrt(track x^2 + track z^2 - x^2)
    y = track y

Moving away from the spine d and f are 0, so this is the ScapulaTrack
exactly. Moving toward it the point stays on the circle behind the shoulder
and stops when f does. The ScapulaHeading aims from the shoulder at that
point, so the scapula turns with its position and stops with it. The
fraction t drives the ScapulaTurnOut's rotateY from 0 to -Retract Turn, so
the turn out builds steadily all the way to the limit.

The scapulaAuto attribute on the Shoulder control (0 to 1, proxied onto the
Scapula control) blends the Scapula from a plain child of the shoulder (0)
to the automated ScapulaTurnOut (1).
"""
import typing

from maya import cmds

import mref
import aniseed_utilities as au

if typing.TYPE_CHECKING:
    import aniseed



class Shoulder:
    """
    Builds the shoulder and scapula.

    Args:
        shoulder_joint: The shoulder joint
        scapula_joint: The scapula joint
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name
        location: The location token (config.left, config.middle etc)
        parent: Optional node to parent the Shoulder control under
        retract_limit: The furthest the scapula moves toward the spine. It
            eases into this, stopping once its plain child position would
            be twice as far. If not given it is 0.25 of the distance
            between the shoulder and scapula.
        retract_turn: How far (in degrees) the scapula turns out about its
            own -y as it retracts, building steadily to this at the retract
            limit
        shape_scale: Optional scale for the control shapes. If not given it
            is derived from the distance between the shoulder and scapula.

    Usage:
        shoulder = Shoulder(clavicle, scapula, config, "Shoulder", config.left).build()
        mref.parentConstraint(shoulder.shoulder_control.ctl, arm_root, maintainOffset=True)
    """

    def __init__(
            self,
            shoulder_joint: str,
            scapula_joint: str,
            config: "aniseed.RigConfiguration",
            prefix: str = "",
            location: str = "",
            parent: str = None,
            retract_limit: float = None,
            retract_turn: float = 20.0,
            shape_scale: float = None,
    ):
        self.shoulder_joint = mref.get(shoulder_joint).full_name()
        self.scapula_joint = mref.get(scapula_joint).full_name()
        self.config = config
        self.location = location
        self.parent = parent

        # -- "shoulder" becomes "Shoulder" so it reads as part of a camel cased description
        self.prefix = prefix[:1].upper() + prefix[1:]

        shoulder_position = _position(self.shoulder_joint)
        self.length = _distance(shoulder_position, _position(self.scapula_joint)) or 1.0
        self.shape_scale = shape_scale or self.length
        self.retract_limit = retract_limit or self.length * 0.25
        self.retract_turn = retract_turn

        # -- Which way along world x is away from the spine
        self.outward = 1.0 if shoulder_position[0] >= 0 else -1.0

        # -- Populated by build
        self.shoulder_control: au.rig.control.Control = None
        self.scapula_control: au.rig.control.Control = None
        self.shoulder_space: str = ""
        self.tip: str = ""
        self.swing: str = ""
        self.scapula_height: str = ""
        self.scapula_follow: str = ""
        self.scapula_track: str = ""
        self.scapula_point: str = ""
        self.scapula_heading: str = ""
        self.scapula_position: str = ""
        self.scapula_turn_out: str = ""
        self.scapula_blend: str = ""

    def build(self) -> "Shoulder":
        """
        Creates the shoulder, the tracking and the automated scapula.

        Returns:
            This instance, so the created nodes can be read from it
        """
        self._create_shoulder()
        self._create_scapula()

        mref.get(self.scapula_control.ctl).add_proxy("scapulaAuto", f"{self.shoulder_control.ctl}.scapulaAuto")

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

    def _create_transform(self, label: str, parent: str, match_to: str, world_aligned: bool = False) -> str:
        node = mref.get(
            au.scene.transforms.create(
                classification=self.config.mechanical,
                description=self._description(label),
                location=self.location,
                config=self.config,
                parent=parent,
                match_to=match_to,
            ),
        ).full_name()

        if world_aligned:
            cmds.xform(node, rotation=(0, 0, 0), worldSpace=True)
        return node

    def _create_node(self, node_type: str, label: str) -> str:
        return cmds.createNode(node_type, name=self._name(self.config.mechanical, label))

    def _create_shoulder(self):
        """
        Creates the Shoulder control with the scapulaAuto attribute, the
        ShoulderTip and ScapulaFollow under it, the world aligned
        ShoulderSpace, and the ShoulderSwing (holding the ScapulaHeight)
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

        ctl = self.shoulder_control.ctl
        mref.get(ctl).add_attribute(
            "scapulaAuto", value=1.0, attribute_type="float", keyable=True, min=0, max=1, defaultValue=1,
        )

        self.scapula_follow = self._create_transform("ScapulaFollow", ctl, self.scapula_joint)

        # -- Its origin stays at the shoulder, so the shoulder is the centre
        # -- of the circle the ScapulaTrack moves on
        self.shoulder_space = self._create_transform(
            "ShoulderSpace", self.shoulder_control.org, self.shoulder_joint, world_aligned=True,
        )
        cmds.pointConstraint(ctl, self.shoulder_space)

        # -- The tip is on the control's x (its twist axis), so twisting does
        # -- not move it, and the ShoulderSwing aims at it keeping the parent's
        # -- up, so it takes the shoulder's swing without its twist
        bone_axis = cmds.xform(ctl, query=True, matrix=True, worldSpace=True)[0:3]
        self.tip = self._create_transform("ShoulderTip", ctl, self.shoulder_joint)
        cmds.setAttr(f"{self.tip}.translate", 0, 0, 0)
        cmds.move(*[value * self.length for value in _normal(*bone_axis)], self.tip, relative=True, worldSpace=True)

        self.swing = self._create_transform("ShoulderSwing", self.shoulder_space, self.shoulder_joint, world_aligned=True)
        cmds.setAttr(f"{self.swing}.translate", 0, 0, 0)
        cmds.aimConstraint(
            self.tip,
            self.swing,
            aimVector=_normal(*bone_axis),
            upVector=(0, 1, 0),
            worldUpType="objectrotation",
            worldUpObject=self.shoulder_space,
            worldUpVector=(0, 1, 0),
        )

        shoulder_position = _position(self.shoulder_joint)
        scapula_position = _position(self.scapula_joint)
        self.scapula_height = self._create_transform("ScapulaHeight", self.swing, self.shoulder_joint)
        cmds.xform(
            self.scapula_height,
            translation=(scapula_position[0], shoulder_position[1], scapula_position[2]),
            worldSpace=True,
        )

    def _create_scapula(self):
        """
        Creates the ScapulaTrack, the driven ScapulaPosition (sliding along
        the ScapulaTrack's circle, eased, as it retracts), the ScapulaTurnOut
        under it, and the ScapulaBlend (holding the Scapula control) blended
        between the ScapulaFollow and ScapulaTurnOut by scapulaAuto
        """
        # -- Follows the ScapulaHeight, offset down by the rest drop in the ShoulderSpace
        self.scapula_track = self._create_transform(
            "ScapulaTrack", self.shoulder_space, self.scapula_joint, world_aligned=True,
        )
        cmds.pointConstraint(self.scapula_height, self.scapula_track, maintainOffset=True)
        rest_x, _, rest_z = cmds.getAttr(f"{self.scapula_track}.translate")[0]
        track = self.scapula_track

        # -- How far it has moved toward the spine (d), and that as a fraction
        # -- (t) of twice the retract limit
        far = self.retract_limit * 1e4
        retracted = self._create_remap("ScapulaRetracted", rest_x, far, 0, far)
        fraction = self._create_remap("ScapulaRetractFraction", rest_x, self.retract_limit * 2, 0, 1)

        # -- The ease, g = t * (2 - t), so f = g * limit follows d exactly at
        # -- first and slows to a stop at the limit
        remainder = self._create_node("plusMinusAverage", "ScapulaRetractRemainder")
        cmds.setAttr(f"{remainder}.operation", 2)  # -- Subtract
        cmds.setAttr(f"{remainder}.input1D[0]", 2)
        cmds.connectAttr(f"{fraction}.outValue", f"{remainder}.input1D[1]")

        ease = self._create_node("multiplyDivide", "ScapulaRetractEase")
        cmds.connectAttr(f"{fraction}.outValue", f"{ease}.input1X")
        cmds.connectAttr(f"{remainder}.output1D", f"{ease}.input2X")

        # -- x = track x + outward * (d - f). The z channel is the turn out
        # -- (-retract turn * t, so it builds steadily all the way to the
        # -- limit rather than easing in early), used further down.
        slide = self._create_node("multiplyDivide", "ScapulaSlide")
        cmds.connectAttr(f"{retracted}.outValue", f"{slide}.input1X")
        cmds.connectAttr(f"{ease}.outputX", f"{slide}.input1Y")
        cmds.connectAttr(f"{fraction}.outValue", f"{slide}.input1Z")
        cmds.setAttr(f"{slide}.input2X", self.outward)
        cmds.setAttr(f"{slide}.input2Y", -self.outward * self.retract_limit)
        cmds.setAttr(f"{slide}.input2Z", -self.retract_turn)

        x = self._create_node("plusMinusAverage", "ScapulaX")
        cmds.connectAttr(f"{track}.translateX", f"{x}.input1D[0]")
        cmds.connectAttr(f"{slide}.outputX", f"{x}.input1D[1]")
        cmds.connectAttr(f"{slide}.outputY", f"{x}.input1D[2]")

        # -- z = track z + |track z| - sqrt(track x^2 + track z^2 - x^2)
        squares = self._create_node("multiplyDivide", "ScapulaSquares")
        for axis, source in zip("XYZ", [f"{track}.translateX", f"{x}.output1D", f"{track}.translateZ"]):
            cmds.connectAttr(source, f"{squares}.input1{axis}")
            cmds.connectAttr(source, f"{squares}.input2{axis}")

        radius = self._create_node("plusMinusAverage", "ScapulaRadius")
        cmds.connectAttr(f"{squares}.outputX", f"{radius}.input1D[0]")
        cmds.connectAttr(f"{squares}.outputZ", f"{radius}.input1D[1]")

        remaining = self._create_node("plusMinusAverage", "ScapulaRemaining")
        cmds.setAttr(f"{remaining}.operation", 2)  # -- Subtract
        cmds.connectAttr(f"{radius}.output1D", f"{remaining}.input1D[0]")
        cmds.connectAttr(f"{squares}.outputY", f"{remaining}.input1D[1]")

        # -- Never below zero, so the square root is always valid
        clamp = self._create_node("clamp", "ScapulaRemainingClamp")
        cmds.setAttr(f"{clamp}.maxR", 1e9)
        cmds.connectAttr(f"{remaining}.output1D", f"{clamp}.inputR")

        roots = self._create_node("multiplyDivide", "ScapulaRoots")
        cmds.setAttr(f"{roots}.operation", 3)  # -- Power
        cmds.connectAttr(f"{clamp}.outputR", f"{roots}.input1X")
        cmds.connectAttr(f"{squares}.outputZ", f"{roots}.input1Y")
        cmds.setAttr(f"{roots}.input2X", 0.5)
        cmds.setAttr(f"{roots}.input2Y", 0.5)

        # -- sqrt(...) - |track z|, taken from the track z
        offset = self._create_node("plusMinusAverage", "ScapulaZOffset")
        cmds.setAttr(f"{offset}.operation", 2)  # -- Subtract
        cmds.connectAttr(f"{roots}.outputX", f"{offset}.input1D[0]")
        cmds.connectAttr(f"{roots}.outputY", f"{offset}.input1D[1]")

        z = self._create_node("plusMinusAverage", "ScapulaZ")
        cmds.setAttr(f"{z}.operation", 2)  # -- Subtract
        cmds.connectAttr(f"{track}.translateZ", f"{z}.input1D[0]")
        cmds.connectAttr(f"{offset}.output1D", f"{z}.input1D[1]")

        # -- The heading aims from the shoulder at the driven position (flat),
        # -- so the scapula turns with its position and stops with it
        self.scapula_point = self._create_transform("ScapulaPoint", self.shoulder_space, self.shoulder_joint)
        self.scapula_heading = self._create_transform(
            "ScapulaHeading", self.shoulder_space, self.shoulder_joint, world_aligned=True,
        )
        cmds.setAttr(f"{self.scapula_point}.translate", 0, 0, 0)
        cmds.setAttr(f"{self.scapula_heading}.translate", 0, 0, 0)
        cmds.connectAttr(f"{x}.output1D", f"{self.scapula_point}.translateX")
        cmds.connectAttr(f"{z}.output1D", f"{self.scapula_point}.translateZ")
        cmds.aimConstraint(
            self.scapula_point,
            self.scapula_heading,
            aimVector=_normal(rest_x, 0, rest_z),
            upVector=(0, 1, 0),
            worldUpType="objectrotation",
            worldUpObject=self.shoulder_space,
            worldUpVector=(0, 1, 0),
        )

        self.scapula_position = self._create_transform(
            "ScapulaPosition", self.shoulder_space, self.scapula_joint, world_aligned=True,
        )
        cmds.connectAttr(f"{x}.output1D", f"{self.scapula_position}.translateX")
        cmds.connectAttr(f"{track}.translateY", f"{self.scapula_position}.translateY")
        cmds.connectAttr(f"{z}.output1D", f"{self.scapula_position}.translateZ")
        cmds.orientConstraint(self.scapula_heading, self.scapula_position)

        # -- Turns the scapula out about its own -y as it retracts, eased the
        # -- same way so it stops at the retract limit. The ScapulaTurnOutOrg
        # -- holds the joint's orientation so the ScapulaTurnOut's y is the joint's.
        turn_out_org = self._create_transform("ScapulaTurnOutOrg", self.scapula_position, self.scapula_joint)
        self.scapula_turn_out = self._create_transform("ScapulaTurnOut", turn_out_org, self.scapula_joint)
        cmds.connectAttr(f"{slide}.outputZ", f"{self.scapula_turn_out}.rotateY")

        # -- scapulaAuto blends from a plain child of the shoulder to the automation
        self.scapula_blend = self._create_transform("ScapulaBlend", self.shoulder_space, self.scapula_joint)
        constraint = cmds.parentConstraint(
            self.scapula_follow, self.scapula_turn_out, self.scapula_blend, maintainOffset=True,
        )[0]
        cmds.setAttr(f"{constraint}.interpType", 2)  # -- Shortest
        reverse = au.scene.constraints.blend_weights(f"{self.shoulder_control.ctl}.scapulaAuto", constraint)
        reverse.rename(self._name(self.config.mechanical, "ScapulaAutoReverse"))

        self.scapula_control = au.rig.control.create(
            description=self._description("Scapula"),
            location=self.location,
            parent=self.scapula_blend,
            shape="core_rounded_square",
            config=self.config,
            match_to=self.scapula_joint,
            shape_scale=self.shape_scale * 0.4,
        )

    def _create_remap(
            self,
            label: str,
            rest_x: float,
            distance: float,
            output_min: float,
            output_max: float,
    ) -> str:
        """
        Creates a remapValue reading the ScapulaTrack's translateX, from its
        rest (0) to the given distance toward the spine (1), clamped either
        side, through a linear curve
        """
        remap = self._create_node("remapValue", label)
        cmds.connectAttr(f"{self.scapula_track}.translateX", f"{remap}.inputValue")
        cmds.setAttr(f"{remap}.inputMin", rest_x)
        cmds.setAttr(f"{remap}.inputMax", rest_x - self.outward * distance)
        cmds.setAttr(f"{remap}.outputMin", output_min)
        cmds.setAttr(f"{remap}.outputMax", output_max)
        for index, value in enumerate([0, 1]):
            cmds.setAttr(f"{remap}.value[{index}].value_Position", value)
            cmds.setAttr(f"{remap}.value[{index}].value_FloatValue", value)
            cmds.setAttr(f"{remap}.value[{index}].value_Interp", 1)  # -- Linear
        return remap


def _position(node: str) -> list:
    return cmds.xform(node, query=True, translation=True, worldSpace=True)


def _distance(a: list, b: list) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _normal(x: float, y: float, z: float) -> tuple:
    length = (x * x + y * y + z * z) ** 0.5 or 1.0
    return x / length, y / length, z / length
