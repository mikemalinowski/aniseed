import mref
from maya import cmds
from maya.api import OpenMaya as om


class NurbsSurface(mref.Trait):
    """
    Trait bound to any node with ``MFn.kNurbsSurface`` — nurbs surface
    shape nodes. Provides CV counts / spans / degrees in U and V, CV
    position queries (single and bulk), parameter ranges, closest point
    and point-at-parameter queries, skin cluster discovery, and the
    skinnable-shape protocol used by ``SkinCluster`` to read and write
    weights.

    CVs are addressed as ``(u, v)`` pairs. Bulk lists are ordered with
    ``u`` as the outer loop and ``v`` as the inner loop (flat index
    ``u * cv_count_v() + v``) — the same ordering ``SkinCluster`` uses.

    Supports the full set of Maya transformation spaces (``"object"``,
    ``"world"``, ``"local"``, ``"pretransform"``, ``"posttransform"``,
    ``"last"``). The function set is built from a DAG path so world
    space queries work.
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
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kNurbsSurface)

    def cv_count_u(self) -> int:
        """
        Returns the number of CVs in the U direction
        """
        return self._surface().numCVsInU

    def cv_count_v(self) -> int:
        """
        Returns the number of CVs in the V direction
        """
        return self._surface().numCVsInV

    def cv_count(self) -> int:
        """
        Returns the total number of CVs making up the surface (U * V)
        """
        surface = self._surface()
        return surface.numCVsInU * surface.numCVsInV

    def span_count_u(self) -> int:
        """
        Returns the number of spans in the U direction
        """
        return self._surface().numSpansInU

    def span_count_v(self) -> int:
        """
        Returns the number of spans in the V direction
        """
        return self._surface().numSpansInV

    def degree_u(self) -> int:
        """
        Returns the degree of the surface in the U direction
        """
        return self._surface().degreeInU

    def degree_v(self) -> int:
        """
        Returns the degree of the surface in the V direction
        """
        return self._surface().degreeInV

    def parameter_range_u(self) -> tuple[float, float]:
        """
        Returns the ``(min, max)`` parameter range of the surface in U
        """
        return tuple(self._surface().knotDomainInU)

    def parameter_range_v(self) -> tuple[float, float]:
        """
        Returns the ``(min, max)`` parameter range of the surface in V
        """
        return tuple(self._surface().knotDomainInV)

    def cv_positions(self, space: str = "object") -> list[list[float]]:
        """
        Returns a list of ``[x, y, z]`` positions, one per CV, ordered
        with ``u`` as the outer loop and ``v`` as the inner loop. Uses
        ``MFnNurbsSurface.cvPositions`` for a single bulk API call.
        """
        points = self._surface().cvPositions(self._resolve_space(space))
        return [
            [p.x, p.y, p.z]
            for p in points
        ]

    def set_cv_positions(self, positions: list[list[float]], space: str = "object"):
        """
        Sets every CV position from a list of ``[x, y, z]`` triplets in
        the same ``u``-outer / ``v``-inner order :meth:`cv_positions`
        returns. ``positions`` must have exactly ``cv_count()`` entries —
        anything else raises ``ValueError``.
        """
        if len(positions) != self.cv_count():
            raise ValueError(
                f"Number of CVs ({self.cv_count()}) does not match "
                f"length of positions ({len(positions)})"
            )

        point_array = om.MPointArray()
        point_array.setLength(len(positions))
        for i, (x, y, z) in enumerate(positions):
            point_array[i] = om.MPoint(x, y, z)

        surface = self._surface()
        surface.setCVPositions(point_array, self._resolve_space(space))

        # -- Like curves, surfaces need an explicit update after CV edits
        surface.updateSurface()

    def cv_position(self, u: int, v: int, space: str = "object") -> list[float]:
        """
        Returns the ``[x, y, z]`` position of the CV at index ``(u, v)``.
        """
        point = self._surface().cvPosition(u, v, self._resolve_space(space))
        return [point.x, point.y, point.z]

    def set_cv_position(self, u: int, v: int, position: list[float], space: str = "object"):
        """
        Sets the position of the CV at index ``(u, v)`` from ``[x, y, z]``.
        """
        surface = self._surface()
        surface.setCVPosition(
            u,
            v,
            om.MPoint(position[0], position[1], position[2]),
            self._resolve_space(space),
        )
        surface.updateSurface()

    def point_at_parameter(self, u: float, v: float, space: str = "object") -> list[float]:
        """
        Returns the ``[x, y, z]`` position on the surface at the given
        ``(u, v)`` parameter.
        """
        point = self._surface().getPointAtParam(u, v, self._resolve_space(space))
        return [point.x, point.y, point.z]

    def closest_point(self, position: list[float], space: str = "object") -> tuple[list[float], float, float]:
        """
        Returns the point on the surface closest to ``position`` as a
        tuple of ``([x, y, z], u, v)`` — the closest position and the
        surface parameters at that position. Both the input and the
        result are expressed in ``space``.
        """
        point, u, v = self._surface().closestPoint(
            om.MPoint(position[0], position[1], position[2]),
            space=self._resolve_space(space),
        )
        return [point.x, point.y, point.z], u, v

    def skin(self) -> mref.ReferencedItem|None:
        """
        Returns a ReferencedItem for the SkinCluster bound to this
        surface, or None if no skin cluster is connected.
        """
        skins = self.item.inputs(type="skinCluster")
        if skins:
            return skins[0]
        return None

    def component_count(self) -> int:
        """
        Returns the number of CVs in the surface.

        Part of the skinnable-shape protocol consumed by
        :class:`SkinCluster`: ``component_count()`` is the number of
        weights that need to be supplied per influence.
        """
        return self.cv_count()

    def component_path(self, component_index: int) -> str:
        """
        Returns the fully qualified path to the component with the
        given flat index — for surfaces, this is ``<full_path>.cv[u][v]``
        where ``u = index // cv_count_v()`` and ``v = index % cv_count_v()``,
        matching the ordering ``SkinCluster`` uses.

        Part of the skinnable-shape protocol consumed by
        :class:`SkinCluster`.
        """
        u, v = divmod(component_index, self.cv_count_v())
        return f"{self.item.full_name()}.cv[{u}][{v}]"

    def _surface(self) -> om.MFnNurbsSurface:
        """
        Returns an MFnNurbsSurface built from a DAG path to this shape.
        Rebuilt per call so it stays valid if the shape is re-parented,
        and so that world space queries are available.
        """
        return om.MFnNurbsSurface(om.MDagPath.getAPathTo(self._pointer))

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
