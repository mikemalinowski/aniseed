import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- Map of MFnNurbsCurve form enums to readable names
_FORMS = {
    om.MFnNurbsCurve.kOpen: "open",
    om.MFnNurbsCurve.kClosed: "closed",
    om.MFnNurbsCurve.kPeriodic: "periodic",
}


class NurbsCurve(mref.Trait):
    """
    Trait bound to any node with ``MFn.kNurbsCurve`` — nurbs curve
    shape nodes. Provides CV position queries (single and bulk),
    counts of CVs / knots / spans, degree, form, knots, length and
    parameter range, point / tangent / normal at parameter, parameter
    at length, closest point queries, reversing, skin cluster
    discovery, and the skinnable-shape protocol used by
    ``SkinCluster`` to read and write weights.

    Unlike ``Transform``, this trait supports the full set of Maya
    transformation spaces (``"object"``, ``"world"``, ``"local"``,
    ``"pretransform"``, ``"posttransform"``, ``"last"``) via the
    underlying ``MFnNurbsCurve`` API — see :meth:`cv_positions` and
    the other space-aware methods. The function set is built from a
    DAG path on every call, so world space queries work and the trait
    stays valid if the shape is re-parented. Binding never touches the
    curve data, so an empty curve node (``cmds.createNode("nurbsCurve")``)
    can still be wrapped.
    """

    # -- Map of space-name strings to MSpace enums. Exposed as a class
    # -- attribute so callers can enumerate supported space names if
    # -- they need to (e.g. for UI dropdowns).
    spaces = mref.constants.spaces

    # -- Sits above the generic Shape trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kNurbsCurve)

    def skin(self) -> mref.ReferencedItem|None:
        """
        Returns a ReferencedItem for the SkinCluster bound to this
        curve, or None if no skin cluster is connected.
        """
        skins = self.item.inputs(type="skinCluster")
        if skins:
            return skins[0]
        return None

    # ------------------------------------------------------------------
    # counts and structure
    # ------------------------------------------------------------------

    def cv_count(self) -> int:
        """
        Returns the total count of cv's making up the curve
        """
        return self._curve().numCVs

    def knot_count(self) -> int:
        """
        Returns the total count of knots making up the curve
        """
        return self._curve().numKnots

    def span_count(self) -> int:
        """
        Returns the total count of spans making up the curve
        """
        return self._curve().numSpans

    def degree(self) -> int:
        """
        Returns the degree of the curve (1 = linear, 3 = cubic, ...)
        """
        return self._curve().degree

    def form(self) -> str:
        """
        Returns the form of the curve as one of ``"open"``, ``"closed"``
        or ``"periodic"``.
        """
        return _FORMS.get(self._curve().form, "invalid")

    def knots(self) -> list[float]:
        """
        Returns the knot vector of the curve
        """
        return list(self._curve().knots())

    def parameter_range(self) -> tuple[float, float]:
        """
        Returns the ``(min, max)`` parameter range of the curve
        """
        return tuple(self._curve().knotDomain)

    def length(self) -> float:
        """
        Returns the arc length of the curve in object space units
        """
        return self._curve().length()

    # ------------------------------------------------------------------
    # skinnable-shape protocol
    # ------------------------------------------------------------------

    def component_count(self) -> int:
        """
        Returns the number of CVs in the curve.

        Part of the skinnable-shape protocol consumed by
        :class:`SkinCluster`: ``component_count()`` is the number of
        weights that need to be supplied per influence.
        """
        return self.cv_count()

    def component_path(self, component_index: int) -> str:
        """
        Returns the fully qualified path to the component with the
        given index — for curves, this is ``<full_path>.cv[N]``.

        Part of the skinnable-shape protocol consumed by
        :class:`SkinCluster`.
        """
        return f"{self.item.full_name()}.cv[{component_index}]"

    # ------------------------------------------------------------------
    # cv positions
    # ------------------------------------------------------------------

    def cv_positions(self, space: str = "object") -> list[list[float]]:
        """
        Returns a list of ``[x, y, z]`` positions, one per CV, in CV
        index order. Uses ``MFnNurbsCurve.cvPositions`` for a single
        bulk API call instead of iterating per-CV.
        """
        points = self._curve().cvPositions(self._resolve_space(space))
        return [
            [p.x, p.y, p.z]
            for p in points
        ]

    def set_cv_positions(self, positions: list[list[float]], space: str = "object"):
        """
        This takes in a positions list, in the format:

        [
            [x, y, z],
            [x, y, z],
            [x, y, z],
            [x, y, z],
            ...
        ]

        Where each triplet list defines the position of the CV id in the
        list order. Applies the entire array in one
        ``MFnNurbsCurve.setCVPositions`` call.
        """
        if len(positions) != self.cv_count():
            raise ValueError(
                f"Number of CVs ({self.cv_count()}) does not match "
                f"length of cv_positions ({len(positions)})"
            )

        point_array = om.MPointArray()
        point_array.setLength(len(positions))
        for i, (x, y, z) in enumerate(positions):
            point_array[i] = om.MPoint(x, y, z)

        curve = self._curve()
        curve.setCVPositions(point_array, self._resolve_space(space))

        # -- Nurbs curves require an explicit updateCurve() after any
        # -- CV mutation; unlike meshes, the API does not propagate the
        # -- dirty flag automatically.
        curve.updateCurve()

    def cv_position(self, cv_index: int, space: str = "object") -> list[float]:
        """
        This returns a list containing the three components correlating to
        the x, y, z positions of the cv.
        """
        point = self._curve().cvPosition(cv_index, self._resolve_space(space))
        return [point.x, point.y, point.z]


    def set_cv_position(self, cv_index: int, position: list[float], space: str = "object"):
        """
        This takes in a position list, in the format:

            [x, y, z]

        The vertex with the given id will then have its position set to those values.
        """
        curve = self._curve()
        curve.setCVPosition(
            cv_index,
            om.MPoint(position[0], position[1], position[2]),
            self._resolve_space(space),
        )

        # -- Nurbs curves require an explicit updateCurve() after any
        # -- CV mutation; unlike meshes, the API does not propagate the
        # -- dirty flag automatically.
        curve.updateCurve()

    # ------------------------------------------------------------------
    # parametric queries
    # ------------------------------------------------------------------

    def point_at_parameter(self, parameter: float, space: str = "object") -> list[float]:
        """
        Returns the ``[x, y, z]`` position on the curve at the given
        parameter.
        """
        point = self._curve().getPointAtParam(parameter, self._resolve_space(space))
        return [point.x, point.y, point.z]

    def tangent_at_parameter(self, parameter: float, space: str = "object") -> list[float]:
        """
        Returns the normalised ``[x, y, z]`` tangent of the curve at the
        given parameter.
        """
        tangent = self._curve().tangent(parameter, self._resolve_space(space))
        tangent.normalize()
        return [tangent.x, tangent.y, tangent.z]

    def normal_at_parameter(self, parameter: float, space: str = "object") -> list[float]:
        """
        Returns the normalised ``[x, y, z]`` normal of the curve at the
        given parameter. Straight (linear) sections of a curve have no
        meaningful curvature normal; Maya returns a perpendicular vector
        there.
        """
        normal = self._curve().normal(parameter, self._resolve_space(space))
        normal.normalize()
        return [normal.x, normal.y, normal.z]

    def parameter_at_length(self, length: float) -> float:
        """
        Returns the parameter at the given arc length along the curve,
        measured from its start. ``length`` is clamped to the curve's
        total :meth:`length`.
        """
        curve = self._curve()
        length = max(0.0, min(length, curve.length()))
        return curve.findParamFromLength(length)

    def parameter_at_point(self, position: list[float], space: str = "object") -> float:
        """
        Returns the curve parameter at the point on the curve closest to
        ``position``. Unlike ``MFnNurbsCurve.getParamAtPoint`` the
        position does not need to lie exactly on the curve.
        """
        return self.closest_point(position, space=space)[1]

    def closest_point(self, position: list[float], space: str = "object") -> tuple[list[float], float]:
        """
        Returns the point on the curve closest to ``position`` as a
        tuple of ``([x, y, z], parameter)``. Both the input and the
        result are expressed in ``space``.
        """
        point, parameter = self._curve().closestPoint(
            om.MPoint(position[0], position[1], position[2]),
            space=self._resolve_space(space),
        )
        return [point.x, point.y, point.z], parameter

    # ------------------------------------------------------------------
    # editing
    # ------------------------------------------------------------------

    def reverse(self) -> None:
        """
        Reverses the direction of the curve in place, so the last CV
        becomes the first. Done directly on the shape's data via
        ``MFnNurbsCurve.reverse``, so no history node is added.
        """
        curve = self._curve()
        curve.reverse()
        curve.updateCurve()

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _curve(self) -> om.MFnNurbsCurve:
        """
        Returns an MFnNurbsCurve built from a DAG path to this shape, so
        that world space queries are available. Built lazily per call so
        it stays valid if the shape is re-parented, and so that curve
        nodes with no geometry data can still be wrapped.
        """
        return om.MFnNurbsCurve(om.MDagPath.getAPathTo(self._pointer))

    def _resolve_space(self, space: str):
        """
        Maps a space-name string to the corresponding ``om.MSpace``
        enum. Raises ``ValueError`` for unknown space names with a
        clear message listing the supported values, rather than the
        bare ``KeyError`` a dict lookup would produce.
        """
        if space not in self.spaces:
            raise ValueError(
                f"Unknown space {space!r}; expected one of "
                f"{tuple(self.spaces.keys())}"
            )
        return self.spaces[space]
