"""
Provides the DynamicPivot class, which builds a rocking pivot: as a control
is rotated in x and z, the pivot it rotates around slides along a guide curve
to the point the rotation tips towards (such as the edge of a foot).

The guide curve is assumed to lie flat in the xz plane with z forward. By
default that is the world's xz plane, and the setup is world aligned. With
align_to_guide it is the guide curve's own (local) xz plane, and the setup
takes the guide curve's orientation, so a pivot can lie at any angle (such as
across the palm of a hand). It is
duplicated into the pivot track and a normalized curve is made from it: a
unit circle with the same cvs, degree and knots as the track, its cvs spread
around the circle in proportion to the distances between the track's cvs.

The control's x and z rotation give a direction in the xz plane,

    direction = normalize(-rz, 0, rx)

which falls back to z forward when the control is not rotated. A rocker
transform sits at that direction (on the unit circle), the parameter of the
nearest point on the normalized curve is read from it, and that parameter on
the pivot track gives the pivot point. As the two curves share their cvs and
knots, a parameter on one sits at the matching point of the other.

The structure built is:

    PivotSetup (org, at the guide curve's translation)
        PivotTrack (the duplicated guide curve)
        NormalizedCurve (the unit circle made from the pivot track)
        NormalizedRocker (sits at the rotation direction on the unit circle)
        Pivot (control, rotate y locked)
        DynamicPivot (takes the control's rotation around the pivot point)
            DynamicPivotResult (the anchor to drive things from)
        DynamicMarker (debug only, a sphere at the pivot point)

DynamicFootPivot extends it with a toe and a heel roll, which takes the
first part of the control's forward x rotation.
"""
import math
import typing

from maya import cmds
from maya.api import OpenMaya as om

import mref
import aniseed_utilities as au

if typing.TYPE_CHECKING:
    import aniseed


class DynamicPivot:
    """
    Builds the dynamic pivot setup around a guide curve.

    Args:
        guide_curve: The curve the pivot slides along. It is duplicated, so
            the guide itself is left alone. It is assumed to lie in the xz
            plane with z forward.
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name, so
            "foot" names the control "FootPivot"
        location: The location token (config.left, config.middle etc)
        debug: If True a sphere is created which sits at the pivot point
        parent: Optional node to parent the setup's org under. The org keeps
            its world placement at the guide curve's translation.
        rotation_multiplier: The control's rotation is multiplied by this
            before it drives anything
        rotation_limit: The control's x and z rotation is limited to plus
            and minus this value (before the multiplier is applied)
        align_to_guide: If True the setup takes the guide curve's world
            orientation (ignoring its scale) rather than being world
            aligned, so the guide curve's local xz plane is the pivot plane

    Usage:
        setup = DynamicPivot(guide, config, "foot", config.left).build()
        mref.parentConstraint(setup.anchor, foot_ctl, maintainOffset=True)
    """

    def __init__(
            self,
            guide_curve: str,
            config: "aniseed.RigConfiguration",
            prefix: str,
            location: str,
            debug: bool = False,
            parent: str = None,
            rotation_multiplier: float = 2.0,
            rotation_limit: float = 45.0,
            align_to_guide: bool = False,
    ):
        self.guide_curve = mref.get(guide_curve)
        self.config = config
        self.location = location
        self.debug = debug
        self.parent = parent
        self.rotation_multiplier = rotation_multiplier
        self.rotation_limit = rotation_limit
        self.align_to_guide = align_to_guide

        # -- "foot" becomes "Foot" so it reads as part of a camel cased description
        self.prefix = prefix[:1].upper() + prefix[1:]

        # -- Populated by build
        self.org: str = ""
        self.track_curve: str = ""
        self.normalized_curve: str = ""
        self.rocker: str = ""
        self.control: au.rig.control.Control = None
        self.pivot: str = ""
        self.anchor: str = ""
        self.debug_marker: str = ""
        self.point_on_track: mref.ReferencedItem = None
        self.radius: float = 0.0

        # -- The rotation the pivot rocks by, the control's multiplied
        # -- rotation unless a subclass routes it elsewhere
        self.rotate_x: mref.ReferencedItem = None
        self.rotate_y: mref.ReferencedItem = None
        self.rotate_z: mref.ReferencedItem = None

    def build(self) -> "DynamicPivot":
        """
        Creates the whole setup.

        Returns:
            This instance, so the created nodes can be read from it
        """
        # -- floatMath comes from the lookdevKit plugin
        if not cmds.pluginInfo("lookdevKit", query=True, loaded=True):
            cmds.loadPlugin("lookdevKit", quiet=True)

        self._create_org()
        self._create_curves()
        self._create_control()
        self._create_rocker()
        self._create_pivot()

        if self.debug:
            self._create_debug_marker()

        return self

    def _description(self, label: str) -> str:
        """
        Returns the description for the given label with the prefix applied
        """
        return f"{self.prefix}{label}"

    def _name(self, classification: str, label: str) -> str:
        """
        Returns a unique name for the given classification and label
        """
        return self.config.generate_name(
            classification=classification,
            description=self._description(label),
            location=self.location,
        )

    def _create_node(self, node_type: str, label: str) -> mref.ReferencedItem:
        """
        Creates a mechanical utility node named for the label
        """
        return mref.create(node_type, name=self._name(self.config.mechanical, label))

    def _create_transform(self, classification: str, label: str, parent: str = None, at: str = None) -> str:
        """
        Creates a transform at the given node's translation, or the guide
        curve's if no node is given. It is world aligned, or takes the guide
        curve's orientation if align_to_guide is set.
        """
        at = at or self.guide_curve.full_name()
        translation = cmds.xform(at, query=True, translation=True, worldSpace=True)

        return au.scene.transforms.create(
            classification=classification,
            description=self._description(label),
            location=self.location,
            config=self.config,
            parent=parent,
            match_to=self._orientation()[:12] + translation + [1],
        )

    def _orientation(self) -> typing.List[float]:
        """
        Returns the matrix (as 16 floats) the setup is oriented by: the
        identity, or the guide curve's world rotation (without its scale or
        translation) if align_to_guide is set
        """
        if not self.align_to_guide:
            return list(om.MMatrix())

        world = om.MMatrix(cmds.xform(self.guide_curve.full_name(), query=True, matrix=True, worldSpace=True))
        return list(om.MTransformationMatrix(world).rotation(asQuaternion=True).asMatrix())

    def _create_org(self):
        """
        Creates the org which every part of the setup lives under, at the
        guide curve's translation
        """
        self.org = self._create_transform(self.config.organisational, "PivotSetup", self.parent)

    def _create_curves(self):
        """
        Duplicates the guide curve into the pivot track and creates the
        normalized curve from it. The track is frozen under the org, so its
        local space is the org's space, which the pivot point is read in.
        """
        track = cmds.duplicate(
            self.guide_curve.full_name(),
            name=self._name(self.config.mechanical, "PivotTrack"),
            returnRootsOnly=True,
        )[0]

        # -- Only the curve shape is wanted, not anything parented under the guide
        children = cmds.listRelatives(track, children=True, fullPath=True) or []
        shapes = cmds.listRelatives(track, shapes=True, type="nurbsCurve", fullPath=True, noIntermediate=True) or []
        if not shapes:
            raise ValueError(f"{self.guide_curve.full_name()} is not a nurbs curve")

        extras = [child for child in children if child not in shapes]
        if extras:
            cmds.delete(extras)

        track = cmds.parent(track, self.org)[0]
        cmds.makeIdentity(track, apply=True, translate=True, rotate=True, scale=True)
        cmds.xform(track, pivots=[0, 0, 0], objectSpace=True)
        self.track_curve = mref.get(track).full_name()

        normalized = _normalized_circle(self._track_shape())
        normalized = cmds.rename(normalized, self._name(self.config.mechanical, "NormalizedCurve"))
        self.normalized_curve = mref.get(cmds.parent(normalized, self.org, relative=True)[0]).full_name()

    def _track_shape(self) -> str:
        return cmds.listRelatives(
            self.track_curve,
            shapes=True,
            type="nurbsCurve",
            fullPath=True,
            noIntermediate=True,
        )[0]

    def _create_control(self):
        """
        Creates the control, sized to the furthest point of the pivot track.
        Rotating in y would not tip towards any point, so it is locked.
        """
        cvs = om.MFnNurbsCurve(om.MSelectionList().add(self._track_shape()).getDagPath(0)).cvPositions()
        self.radius = max(om.MVector(cv).length() for cv in cvs)

        self.control = au.rig.control.create(
            description=self._description("Pivot"),
            location=self.location,
            parent=self.org,
            shape="core_circle",
            config=self.config,
            match_to=self.org,
            # -- The circle shape has a radius of 0.5
            shape_scale=self.radius * 2,
        )

        ctl = mref.get(self.control.ctl)
        ctl.attr("rotateOrder").set(3)  # -- xzy
        ctl.attr("rotateY").set(lock=True, keyable=False)

        cmds.transformLimits(
            ctl.full_name(),
            rotationX=(-self.rotation_limit, self.rotation_limit),
            rotationZ=(-self.rotation_limit, self.rotation_limit),
            enableRotationX=(True, True),
            enableRotationZ=(True, True),
        )

        multiplier = self._create_node("multiplyDivide", "RotationMultiplier")
        ctl.attr("rotate").connect(multiplier.attr("input1"))
        multiplier.attr("input2").set(*[self.rotation_multiplier] * 3)

        self.rotate_x = multiplier.attr("outputX")
        self.rotate_y = multiplier.attr("outputY")
        self.rotate_z = multiplier.attr("outputZ")

    def _create_rocker(self):
        """
        Creates the rocker, which sits on the unit circle in the direction
        the control is rotated towards:

            direction = normalize(-rz, 0, rx)

        With no rotation the direction falls back to z forward.
        """
        amount = self._create_node("length", "RotationAmount")
        self.rotate_x.connect(amount.attr("inputX"))
        self.rotate_z.connect(amount.attr("inputZ"))

        # -- Catches a zero length vector, which has no direction
        rotated = self._create_node("condition", "IsRotated")
        rotated.attr("operation").set(2)  # -- Greater than
        amount.attr("output").connect(rotated.attr("firstTerm"))
        rotated.attr("secondTerm").set(0)
        self.rotate_x.connect(rotated.attr("colorIfTrueR"))
        self.rotate_z.connect(rotated.attr("colorIfTrueB"))
        rotated.attr("colorIfFalse").set(1, 0, 0)

        invert = self._create_node("floatMath", "InvertRotateZ")
        invert.attr("operation").set(2)  # -- Multiply
        rotated.attr("outColorB").connect(invert.attr("floatA"))
        invert.attr("floatB").set(-1)

        direction = self._create_node("vectorProduct", "RockerDirection")
        direction.attr("operation").set(0)  # -- No operation
        direction.attr("normalizeOutput").set(True)
        invert.attr("outFloat").connect(direction.attr("input1X"))
        rotated.attr("outColorR").connect(direction.attr("input1Z"))

        self.rocker = mref.get(self._create_transform(self.config.mechanical, "NormalizedRocker", self.org)).full_name()
        direction.attr("output").connect(mref.get(self.rocker).attr("translate"))

    def _create_pivot(self):
        """
        Creates the pivot, which takes the control's rotation around the
        point on the pivot track matching the rocker's nearest point on the
        normalized curve, and the anchor under it
        """
        rocker_position = self._create_node("decomposeMatrix", "RockerPosition")
        mref.get(self.rocker).attr("worldMatrix[0]").connect(rocker_position.attr("inputMatrix"))

        nearest = self._create_node("nearestPointOnCurve", "NormalizedNearest")
        mref.get(self.normalized_curve).attr("worldSpace[0]").connect(nearest.attr("inputCurve"))
        rocker_position.attr("outputTranslate").connect(nearest.attr("inPosition"))

        self.point_on_track = self._create_node("pointOnCurveInfo", "PivotPoint")
        mref.get(self.track_curve).attr("local").connect(self.point_on_track.attr("inputCurve"))
        nearest.attr("parameter").connect(self.point_on_track.attr("parameter"))

        self.pivot = mref.get(self._create_transform(self.config.mechanical, "DynamicPivot", self.org)).full_name()
        pivot = mref.get(self.pivot)
        self.rotate_x.connect(pivot.attr("rotateX"))
        self.rotate_y.connect(pivot.attr("rotateY"))
        self.rotate_z.connect(pivot.attr("rotateZ"))
        # -- cmds rather than mref, as mref fails to connect to the rotatePivot
        cmds.connectAttr(f"{self.point_on_track.full_name()}.position", f"{self.pivot}.rotatePivot")

        self.anchor = mref.get(self._create_transform(self.config.mechanical, "DynamicPivotResult", self.pivot)).full_name()

    def _create_debug_marker(self):
        """
        Creates a sphere which sits at the pivot point
        """
        marker = cmds.polySphere(
            name=self._name(self.config.mechanical, "DynamicMarker"),
            radius=0.1,
            constructionHistory=False,
        )[0]
        marker = mref.get(cmds.parent(marker, self.org, relative=True)[0])
        self.point_on_track.attr("position").connect(marker.attr("translate"))
        self.debug_marker = marker.full_name()


class DynamicFootPivot(DynamicPivot):
    """
    A DynamicPivot which drives a foot and a toe. The control's x rotation
    is split by its animatable heelRollLimit attribute (in degrees). Forward
    (positive) rotation up to the limit lifts the heel, rolling the foot
    around the toe, and only the rest rocks the pivot:

        heel = clamp(rx, 0, heelRollLimit)
        pivot = rx - heel

    Added under the DynamicPivotResult:

        DynamicPivotResult
            Toe (control, at the toe, to drive the toe from)
            HeelRoll (at the toe, takes the heel share of the x rotation)
                Heel (control)
                    FootResult (matched to the foot, to drive the foot from)

    Args:
        foot: The node the FootResult is matched to (such as the foot joint)
        toe: The node whose translation the toe and heel roll sit at (such
            as the toe joint)

        The remaining arguments are as DynamicPivot.

    Usage:
        setup = DynamicFootPivot(guide, config, "", config.left, foot_jnt, toe_jnt).build()
        mref.parentConstraint(setup.foot_anchor, foot_jnt, maintainOffset=True)
    """

    def __init__(
            self,
            guide_curve: str,
            config: "aniseed.RigConfiguration",
            prefix: str,
            location: str,
            foot: str,
            toe: str,
            debug: bool = False,
            parent: str = None,
            rotation_multiplier: float = 2.0,
            rotation_limit: float = 45.0,
    ):
        super().__init__(
            guide_curve,
            config,
            prefix,
            location,
            debug=debug,
            parent=parent,
            rotation_multiplier=rotation_multiplier,
            rotation_limit=rotation_limit,
        )
        self.foot = foot
        self.toe = toe

        # -- Populated by build
        self.heel_rotation: mref.ReferencedItem = None
        self.heel_roll: str = ""
        self.toe_control: au.rig.control.Control = None
        self.heel_control: au.rig.control.Control = None
        self.foot_anchor: str = ""

    def build(self) -> "DynamicFootPivot":
        """
        Creates the dynamic pivot, then the toe and heel on its result.

        Returns:
            This instance, so the created nodes can be read from it
        """
        super().build()
        self._create_toe_and_heel()
        return self

    def _create_control(self):
        """
        Creates the control, then splits its x rotation between the heel
        roll and the pivot
        """
        super()._create_control()
        ctl = mref.get(self.control.ctl)

        limit = ctl.add_attribute(
            "heelRollLimit",
            value=40,
            attribute_type="double",
            keyable=True,
            min=0,
            defaultValue=40,
        )

        heel = self._create_node("clamp", "HeelRollAmount")
        self.rotate_x.connect(heel.attr("inputR"))
        limit.connect(heel.attr("maxR"))

        pivot_x = self._create_node("floatMath", "PivotRotateX")
        pivot_x.attr("operation").set(1)  # -- Subtract
        self.rotate_x.connect(pivot_x.attr("floatA"))
        heel.attr("outputR").connect(pivot_x.attr("floatB"))

        self.heel_rotation = heel.attr("outputR")
        self.rotate_x = pivot_x.attr("outFloat")

    def _create_toe_and_heel(self):
        """
        Creates the heel roll at the toe with the heel control under it,
        the toe control beside it and the foot result under the heel
        control
        """
        self.heel_roll = mref.get(
            self._create_transform(self.config.mechanical, "HeelRoll", self.anchor, at=self.toe),
        ).full_name()
        self.heel_rotation.connect(mref.get(self.heel_roll).attr("rotateX"))

        # -- The circle shape has a radius of 0.5
        self.toe_control = au.rig.control.create(
            description=self._description("Toe"),
            location=self.location,
            parent=self.anchor,
            shape="core_circle",
            config=self.config,
            match_to=self.heel_roll,
            shape_scale=self.radius * 0.5,
        )

        self.heel_control = au.rig.control.create(
            description=self._description("Heel"),
            location=self.location,
            parent=self.heel_roll,
            shape="core_circle",
            config=self.config,
            match_to=self.heel_roll,
            shape_scale=self.radius * 0.75,
        )

        self.foot_anchor = mref.get(
            au.scene.transforms.create(
                classification=self.config.mechanical,
                description=self._description("FootResult"),
                location=self.location,
                config=self.config,
                parent=self.heel_control.ctl,
                match_to=self.foot,
            ),
        ).full_name()


def _normalized_circle(curve_shape: str) -> str:
    """
    Creates a curve with the same cv count, degree, form and knots as the
    given curve, with its cvs on a unit circle in the xz plane, centred at the
    origin. The cvs are spaced around the circle in proportion to the
    distances between the given curve's cvs, wind in the same direction and
    are rotated for the best overall match of each cv's angle to its
    counterpart's.

    Args:
        curve_shape: The nurbs curve shape to build from (in object space)

    Returns:
        The new curve's transform
    """
    fn = om.MFnNurbsCurve(om.MSelectionList().add(curve_shape).getDagPath(0))

    degree = fn.degree
    form = fn.form
    knots = fn.knots()
    cvs = fn.cvPositions(om.MSpace.kObject)

    # -- Periodic curves repeat the first <degree> cvs at the end
    periodic = form == om.MFnNurbsCurve.kPeriodic
    unique = len(cvs) - degree if periodic else len(cvs)
    points = [om.MVector(cvs[idx]) for idx in range(unique)]

    # -- Arc length fractions from the cv to cv distances. On an open
    # -- curve the last cv lands at 2 pi, on top of the first.
    segments = [(points[idx + 1] - points[idx]).length() for idx in range(unique - 1)]
    if periodic:
        segments.append((points[0] - points[-1]).length())
    total = sum(segments)

    if total < 1e-10:
        fractions = [idx / float(len(segments)) for idx in range(unique)]
    else:
        fractions = [0.0]
        accumulated = 0.0
        for length in segments[:unique - 1]:
            accumulated += length
            fractions.append(accumulated / total)

    # -- A closed open form curve duplicates its end cv, which is ignored
    # -- for the centre and winding
    ring = points
    if not periodic and unique > 2 and (points[0] - points[-1]).length() < 1e-6:
        ring = points[:-1]

    centre = om.MVector()
    for point in ring:
        centre += point
    centre *= 1.0 / len(ring)

    # -- The y of the polygon (newell) normal gives the winding in the xz plane
    winding = 0.0
    for idx, a in enumerate(ring):
        b = ring[(idx + 1) % len(ring)]
        winding += (a.z - b.z) * (a.x + b.x)

    normal = om.MVector(0, -1 if winding < 0 else 1, 0)
    u = om.MVector(1, 0, 0)
    v = normal ^ u

    # -- Rotate by the circular mean of the per cv angle differences so the
    # -- new cvs line up with the given curve's
    base = [2.0 * math.pi * fraction for fraction in fractions]
    angles = [math.atan2((point - centre) * v, (point - centre) * u) for point in points]

    sine = cosine = 0.0
    for angle, base_angle in zip(angles, base):
        sine += math.sin(angle - base_angle)
        cosine += math.cos(angle - base_angle)
    offset = math.atan2(sine, cosine)

    new_points = [om.MPoint(u * math.cos(angle + offset) + v * math.sin(angle + offset)) for angle in base]
    if periodic:
        new_points += new_points[:degree]

    created = om.MFnNurbsCurve().create(om.MPointArray(new_points), knots, degree, form, False, False)
    return om.MFnDagNode(created).fullPathName()
