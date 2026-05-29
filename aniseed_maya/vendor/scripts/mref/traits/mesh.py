import mref
from maya import cmds
from maya.api import OpenMaya as om


class Mesh(mref.Trait):
    """
    Trait bound to any node with ``MFn.kMesh`` — polygon mesh shape
    nodes. Provides vertex position queries (single and bulk),
    polygon and edge counts, skin cluster discovery, and the
    skinnable-shape protocol used by ``SkinCluster`` to read and
    write weights.

    Unlike ``Transform``, this trait supports the full set of Maya
    transformation spaces (``"object"``, ``"world"``, ``"local"``,
    ``"pretransform"``, ``"posttransform"``, ``"last"``) via the
    underlying ``MFnMesh`` API — see :meth:`vertex_positions` and the
    other space-aware methods.
    """

    # -- Map of space-name strings to MSpace enums. Exposed as a class
    # -- attribute so callers can enumerate supported space names if
    # -- they need to (e.g. for UI dropdowns).
    spaces = mref.constants.spaces

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mesh = om.MFnMesh(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kMesh)

    def vertex_count(self) -> int:
        """
        Returns the total count of vertices making up the mesh
        """
        return self._mesh.numVertices

    def polygon_count(self) -> int:
        """
        Returns the total count of polygons making up the mesh
        """
        return self._mesh.numPolygons

    def edge_count(self) -> int:
        """
        Returns the total count of edges making up the mesh
        """
        return self._mesh.numEdges

    def vertex_positions(self, space: str = "object") -> list[list[float]]:
        """
        This returns a list containing a list of three components correlating to
        the x, y, z positions of the vertices.
        """
        points = self._mesh.getPoints(self._resolve_space(space))
        return [
            [p.x, p.y, p.z]
            for p in points
        ]

    def set_vertex_positions(self, positions: list[list[float]], space: str = "object"):
        """
        This takes in a positions list, in the format:

        [
            [x, y, z],
            [x, y, z],
            [x, y, z],
            [x, y, z],
            ...
        ]

        Where each triplet list defines the position of the vertex id in the
        list order. ``positions`` must have exactly ``vertex_count()``
        entries — anything else raises ``ValueError``.
        """
        if len(positions) != self.vertex_count():
            raise ValueError(
                f"Number of vertices ({self.vertex_count()}) does not match "
                f"length of positions ({len(positions)})"
            )

        point_array = om.MPointArray()
        point_array.setLength(len(positions))

        for i, (x, y, z) in enumerate(positions):
            point_array[i] = om.MPoint(x, y, z)

        # Apply all positions in one call
        self._mesh.setPoints(point_array, self._resolve_space(space))

    def vertex_position(self, vertex_id: int, space: str = "object") -> list[float]:
        """
        This returns a list containing the three components correlating to
        the x, y, z positions of the vertex.
        """
        point = self._mesh.getPoint(vertex_id, self._resolve_space(space))
        return [point.x, point.y, point.z]


    def set_vertex_position(self, vertex_id: int, position: list[float], space="object"):
        """
        This takes in a position list, in the format:

            [x, y, z]

        The vertex with the given id will then have its position set to those values.
        """
        self._mesh.setPoint(vertex_id, om.MPoint(*position), self._resolve_space(space))

    def skin(self) -> mref.ReferencedItem|None:
        """
        Returns a ReferencedItem for the SkinCluster bound to this
        mesh, or None if no skin cluster is connected.
        """
        skins = self.item.inputs(type="skinCluster")
        if skins:
            return skins[0]
        return None

    def component_count(self) -> int:
        """
        Returns the number of vertices in the mesh.

        Part of the skinnable-shape protocol consumed by
        :class:`SkinCluster`: ``component_count()`` is the number of
        weights that need to be supplied per influence.
        """
        return self.vertex_count()

    def component_path(self, component_index: int) -> str:
        """
        Returns the fully qualified path to the component with the
        given index — for meshes, this is ``<full_path>.vtx[N]``.

        Part of the skinnable-shape protocol consumed by
        :class:`SkinCluster`.
        """
        return f"{self.item.full_name()}.vtx[{component_index}]"

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
