import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- Index to name mapping of the ffd ``outsideLattice`` enum
_OUTSIDE_LATTICE_MODES = ["inside", "all", "falloff"]


def _divisions(lattice_shape_name: str) -> tuple[int, int, int]:
    """
    Returns the (s, t, u) divisions of the given lattice shape
    """
    return tuple(
        cmds.getAttr(f"{lattice_shape_name}.{axis}Divisions")
        for axis in "stu"
    )


class Lattice(mref.Trait):
    """
    Trait bound to any node with ``MFn.kFFD`` — the free-form (``ffd``)
    lattice deformer. Exposes the driving lattice and base lattice
    shapes, the lattice divisions, local mode and local influence, and
    the outside-lattice behaviour.

    Input/output geometry, the envelope and the paintable per-component
    weights are provided by the generic ``GeometryFilter`` trait which is
    also bound to every ffd.
    """

    # -- Sits above the generic GeometryFilter trait
    priority = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kFFD)

    def lattice(self) -> mref.ReferencedItem|None:
        """
        Returns the lattice shape (``MFn.kLattice``) driving this ffd, or
        None if it is not connected. Use ``.transform()`` on the result
        to get the lattice transform.
        """
        return self._source_node("deformedLatticePoints")

    def base_lattice(self) -> mref.ReferencedItem|None:
        """
        Returns the base lattice shape (``MFn.kBaseLattice``) which
        defines the rest position of the lattice, or None if it is not
        connected.
        """
        return self._source_node("baseLatticeMatrix")

    def divisions(self) -> tuple[int, int, int]:
        """
        Returns the (s, t, u) divisions of the lattice driving this ffd
        """
        return tuple(cmds.lattice(self.item.full_name(), query=True, divisions=True))

    def set_divisions(self, s: int, t: int, u: int) -> None:
        """
        Sets the (s, t, u) divisions of the lattice driving this ffd.
        This resets the lattice points to a regular grid.
        """
        cmds.lattice(self.item.full_name(), edit=True, divisions=(s, t, u))

    def is_local(self) -> bool:
        """
        Returns True if the ffd is in local mode — each lattice point
        only influences the geometry near it (see
        :meth:`local_influence`).
        """
        return cmds.getAttr(f"{self.item.full_name()}.local")

    def set_local(self, state: bool) -> None:
        """
        Sets whether the ffd is in local mode
        """
        cmds.setAttr(f"{self.item.full_name()}.local", state)

    def local_influence(self) -> tuple[int, int, int]:
        """
        Returns the (s, t, u) local influence — the number of lattice
        points in each direction that affect a deformed point when the
        ffd is in local mode.
        """
        return tuple(
            cmds.getAttr(f"{self.item.full_name()}.localInfluence{axis}")
            for axis in "STU"
        )

    def set_local_influence(self, s: int, t: int, u: int) -> None:
        """
        Sets the (s, t, u) local influence used when the ffd is in local
        mode
        """
        for axis, value in zip("STU", (s, t, u)):
            cmds.setAttr(f"{self.item.full_name()}.localInfluence{axis}", value)

    def outside_lattice(self) -> str:
        """
        Returns how points outside the lattice are deformed, one of
        ``"inside"`` (only points inside are deformed), ``"all"`` (every
        point is deformed) or ``"falloff"`` (points within
        :meth:`outside_falloff_distance` are deformed).
        """
        return _OUTSIDE_LATTICE_MODES[cmds.getAttr(f"{self.item.full_name()}.outsideLattice")]

    def set_outside_lattice(self, mode: str, falloff_distance: float = None) -> None:
        """
        Sets how points outside the lattice are deformed — ``mode`` is
        one of ``"inside"``, ``"all"`` or ``"falloff"``. If given,
        ``falloff_distance`` also sets the falloff distance used by the
        ``"falloff"`` mode.
        """
        if mode not in _OUTSIDE_LATTICE_MODES:
            raise ValueError(
                f"Unknown outside lattice mode {mode!r}; expected one of "
                f"{tuple(_OUTSIDE_LATTICE_MODES)}"
            )

        cmds.setAttr(
            f"{self.item.full_name()}.outsideLattice",
            _OUTSIDE_LATTICE_MODES.index(mode),
        )

        if falloff_distance is not None:
            cmds.setAttr(f"{self.item.full_name()}.outsideFalloffDist", falloff_distance)

    def outside_falloff_distance(self) -> float:
        """
        Returns the distance outside the lattice within which points are
        still deformed when the outside-lattice mode is ``"falloff"``
        """
        return cmds.getAttr(f"{self.item.full_name()}.outsideFalloffDist")

    def _source_node(self, attribute_name: str) -> mref.ReferencedItem|None:
        """
        Returns the node feeding the given attribute on this ffd, or
        None if it is not connected.
        """
        source = self._dependency_node.findPlug(attribute_name, False).source()
        if source.isNull:
            return None
        return mref.get(source.node())


class LatticeShape(mref.Trait):
    """
    Trait bound to any node with ``MFn.kLattice`` — the lattice shape
    which drives an ffd deformer (but not the base lattice, which is
    ``MFn.kBaseLattice``). Exposes the divisions, bulk and single point
    position get/set, the ffd deformers it drives, and the
    skinnable-shape protocol (``component_count``/``component_path``)
    so other deformers on the lattice (clusters, skins) can read and
    write per-point weights.

    Point positions use the flat point index Maya uses for the lattice
    geometry: ``s + t * S + u * S * T`` for divisions ``(S, T, U)`` —
    see :meth:`point_index`. API 2.0 has no ``MFnLattice``, so positions
    are read and written through ``MItGeometry``, which supports the
    ``"object"`` and ``"world"`` spaces.
    """

    # -- Map of space-name strings to MSpace enums.
    spaces = mref.constants.spaces

    # -- Sits above the generic Shape trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kLattice)

    def divisions(self) -> tuple[int, int, int]:
        """
        Returns the (s, t, u) divisions of the lattice
        """
        return _divisions(self.item.full_name())

    def set_divisions(self, s: int, t: int, u: int) -> None:
        """
        Sets the (s, t, u) divisions of the lattice. If the lattice
        drives an ffd the edit goes through ``cmds.lattice`` so the
        deformer is updated correctly; this resets the lattice points to
        a regular grid.
        """
        ffds = self.ffd_deformers()
        if ffds:
            cmds.lattice(ffds[0].full_name(), edit=True, divisions=(s, t, u))
            return

        for axis, value in zip("stu", (s, t, u)):
            cmds.setAttr(f"{self.item.full_name()}.{axis}Divisions", value)

    def point_count(self) -> int:
        """
        Returns the number of lattice points (``S * T * U``)
        """
        s, t, u = self.divisions()
        return s * t * u

    def point_index(self, s: int, t: int, u: int) -> int:
        """
        Returns the flat point index of the lattice point ``pt[s][t][u]``
        as used by the point position methods.
        """
        div_s, div_t, div_u = self.divisions()
        if not (0 <= s < div_s and 0 <= t < div_t and 0 <= u < div_u):
            raise IndexError(
                f"Lattice point [{s}][{t}][{u}] is outside divisions "
                f"({div_s}, {div_t}, {div_u})"
            )
        return s + (t * div_s) + (u * div_s * div_t)

    def point_positions(self, space: str = "object") -> list[list[float]]:
        """
        Returns the positions of every lattice point as a list of
        ``[x, y, z]`` lists, ordered by flat point index.
        """
        points = self._iterator().allPositions(self._resolve_space(space))
        return [[p.x, p.y, p.z] for p in points]

    def set_point_positions(self, positions: list[list[float]], space: str = "object") -> None:
        """
        Sets the position of every lattice point from a list of
        ``[x, y, z]`` lists ordered by flat point index. ``positions``
        must have exactly ``point_count()`` entries.
        """
        if len(positions) != self.point_count():
            raise ValueError(
                f"Number of lattice points ({self.point_count()}) does not "
                f"match length of positions ({len(positions)})"
            )

        point_array = om.MPointArray()
        point_array.setLength(len(positions))
        for i, (x, y, z) in enumerate(positions):
            point_array[i] = om.MPoint(x, y, z)

        self._iterator().setAllPositions(point_array, self._resolve_space(space))

    def point_position(self, index: int, space: str = "object") -> list[float]:
        """
        Returns the ``[x, y, z]`` position of the lattice point with the
        given flat index (see :meth:`point_index`).
        """
        return self.point_positions(space)[index]

    def set_point_position(self, index: int, position: list[float], space: str = "object") -> None:
        """
        Sets the ``[x, y, z]`` position of the lattice point with the
        given flat index (see :meth:`point_index`).
        """
        positions = self.point_positions(space)
        positions[index] = list(position)
        self.set_point_positions(positions, space)

    def ffd_deformers(self) -> mref.ReferenceList:
        """
        Returns the ffd deformers this lattice drives
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in cmds.listConnections(
                f"{self.item.full_name()}.latticeOutput",
                source=False,
                destination=True,
                type="ffd",
            ) or []
        )

    def component_count(self) -> int:
        """
        Returns the number of lattice points.

        Part of the skinnable-shape protocol consumed by
        ``GeometryFilter``/``SkinCluster``.
        """
        return self.point_count()

    def component_path(self, component_index: int) -> str:
        """
        Returns the fully qualified path to the lattice point with the
        given flat index — ``<full_path>.pt[s][t][u]``.

        Part of the skinnable-shape protocol consumed by
        ``GeometryFilter``/``SkinCluster``.
        """
        div_s, div_t, _ = self.divisions()
        s = component_index % div_s
        t = (component_index // div_s) % div_t
        u = component_index // (div_s * div_t)
        return f"{self.item.full_name()}.pt[{s}][{t}][{u}]"

    def _iterator(self) -> om.MItGeometry:
        """
        Returns a geometry iterator over the lattice points
        """
        return om.MItGeometry(om.MDagPath.getAPathTo(self._pointer))

    def _resolve_space(self, space: str):
        """
        Maps a space-name string to the corresponding ``om.MSpace`` enum
        """
        if space not in self.spaces:
            raise ValueError(
                f"Unknown space {space!r}; expected one of "
                f"{tuple(self.spaces.keys())}"
            )
        return self.spaces[space]
