import mref
from maya import cmds
from maya.api import OpenMaya as om


class Mesh(mref.Trait):
    """
    Trait bound to any node with ``MFn.kMesh`` — polygon mesh shape
    nodes. Provides vertex position queries (single and bulk),
    polygon and edge counts, normals, UV sets and UVs, topology
    queries (face / edge / connected / border vertices), closest point
    and ray intersection queries, shading engine discovery, skin
    cluster discovery, and the skinnable-shape protocol used by
    ``SkinCluster`` to read and write weights.

    Unlike ``Transform``, this trait supports the full set of Maya
    transformation spaces (``"object"``, ``"world"``, ``"local"``,
    ``"pretransform"``, ``"posttransform"``, ``"last"``) via the
    underlying ``MFnMesh`` API — see :meth:`vertex_positions` and the
    other space-aware methods. The function set is built from a DAG
    path on every call, so world space queries work and the trait
    stays valid if the shape is re-parented. Binding never touches the
    mesh data, so an empty mesh node (``cmds.createNode("mesh")``) can
    still be wrapped.
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
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kMesh)

    # ------------------------------------------------------------------
    # counts
    # ------------------------------------------------------------------

    def vertex_count(self) -> int:
        """
        Returns the total count of vertices making up the mesh
        """
        return self._mesh().numVertices

    def polygon_count(self) -> int:
        """
        Returns the total count of polygons making up the mesh
        """
        return self._mesh().numPolygons

    def edge_count(self) -> int:
        """
        Returns the total count of edges making up the mesh
        """
        return self._mesh().numEdges

    # ------------------------------------------------------------------
    # vertex positions
    # ------------------------------------------------------------------

    def vertex_positions(self, space: str = "object") -> list[list[float]]:
        """
        This returns a list containing a list of three components correlating to
        the x, y, z positions of the vertices.
        """
        points = self._mesh().getPoints(self._resolve_space(space))
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
        self._mesh().setPoints(point_array, self._resolve_space(space))

    def vertex_position(self, vertex_id: int, space: str = "object") -> list[float]:
        """
        This returns a list containing the three components correlating to
        the x, y, z positions of the vertex.
        """
        point = self._mesh().getPoint(vertex_id, self._resolve_space(space))
        return [point.x, point.y, point.z]


    def set_vertex_position(self, vertex_id: int, position: list[float], space="object"):
        """
        This takes in a position list, in the format:

            [x, y, z]

        The vertex with the given id will then have its position set to those values.
        """
        self._mesh().setPoint(vertex_id, om.MPoint(*position), self._resolve_space(space))

    # ------------------------------------------------------------------
    # normals
    # ------------------------------------------------------------------

    def vertex_normals(self, space: str = "object", angle_weighted: bool = False) -> list[list[float]]:
        """
        Returns one ``[x, y, z]`` normal per vertex, in vertex index
        order. Each is the average of the vertex's face-vertex normals,
        optionally weighted by the face angle at the vertex. Uses a
        single bulk ``MFnMesh.getVertexNormals`` call.
        """
        normals = self._mesh().getVertexNormals(angle_weighted, self._resolve_space(space))
        return [
            [n.x, n.y, n.z]
            for n in normals
        ]

    def face_normals(self, space: str = "object") -> list[list[float]]:
        """
        Returns one ``[x, y, z]`` normal per polygon, in face index
        order.
        """
        mesh = self._mesh()
        resolved_space = self._resolve_space(space)
        results = []
        for face_id in range(mesh.numPolygons):
            normal = mesh.getPolygonNormal(face_id, resolved_space)
            results.append([normal.x, normal.y, normal.z])
        return results

    # ------------------------------------------------------------------
    # topology
    # ------------------------------------------------------------------

    def face_vertices(self, face_id: int|None = None) -> list[int]|list[list[int]]:
        """
        Returns the vertex indices making up the face with the given id,
        in winding order. If ``face_id`` is None the vertex lists for
        every face are returned (a list of lists, in face index order),
        read in a single bulk ``MFnMesh.getVertices`` call.
        """
        mesh = self._mesh()

        if face_id is not None:
            return list(mesh.getPolygonVertices(face_id))

        counts, connects = mesh.getVertices()
        results = []
        offset = 0
        for count in counts:
            results.append(list(connects[offset:offset + count]))
            offset += count
        return results

    def edge_vertices(self, edge_id: int) -> tuple[int, int]:
        """
        Returns the two vertex indices at either end of the edge with
        the given id.
        """
        return tuple(self._mesh().getEdgeVertices(edge_id))

    def connected_vertices(self, vertex_id: int) -> list[int]:
        """
        Returns the indices of every vertex sharing an edge with the
        given vertex.
        """
        iterator = om.MItMeshVertex(self._dag_path())
        iterator.setIndex(vertex_id)
        return list(iterator.getConnectedVertices())

    def border_vertices(self) -> list[int]:
        """
        Returns the sorted indices of every vertex lying on an open
        (boundary) edge of the mesh. A closed mesh returns an empty
        list.
        """
        border = set()
        iterator = om.MItMeshEdge(self._dag_path())
        while not iterator.isDone():
            if iterator.onBoundary():
                border.add(iterator.vertexId(0))
                border.add(iterator.vertexId(1))
            iterator.next()
        return sorted(border)

    # ------------------------------------------------------------------
    # uvs
    # ------------------------------------------------------------------

    def uv_set_names(self) -> list[str]:
        """
        Returns the names of all the UV sets on the mesh
        """
        return list(self._mesh().getUVSetNames())

    def current_uv_set(self) -> str:
        """
        Returns the name of the mesh's current (working) UV set
        """
        return self._mesh().currentUVSetName()

    def set_current_uv_set(self, uv_set: str) -> None:
        """
        Makes the given UV set the mesh's current (working) UV set.
        Raises ``ValueError`` if no UV set with that name exists.
        """
        self._validate_uv_set(uv_set)
        self._mesh().setCurrentUVSetName(uv_set)

    def uv_count(self, uv_set: str|None = None) -> int:
        """
        Returns the number of UVs in the given UV set, or in the current
        UV set if none is given.
        """
        mesh = self._mesh()
        return mesh.numUVs(self._resolve_uv_set(uv_set, mesh))

    def uvs(self, uv_set: str|None = None) -> list[list[float]]:
        """
        Returns one ``[u, v]`` pair per UV in the given UV set (or the
        current UV set if none is given), in UV index order.
        """
        mesh = self._mesh()
        u_values, v_values = mesh.getUVs(self._resolve_uv_set(uv_set, mesh))
        return [
            [u, v]
            for u, v in zip(u_values, v_values)
        ]

    def set_uvs(self, uvs: list[list[float]], uv_set: str|None = None) -> None:
        """
        Sets every UV in the given UV set (or the current UV set if none
        is given) from a list of ``[u, v]`` pairs in UV index order, as
        returned by :meth:`uvs`. Only the UV values change — face
        assignments are left untouched, so ``uvs`` must have exactly
        ``uv_count(uv_set)`` entries or ``ValueError`` is raised.
        """
        mesh = self._mesh()
        uv_set = self._resolve_uv_set(uv_set, mesh)

        if len(uvs) != mesh.numUVs(uv_set):
            raise ValueError(
                f"Number of UVs ({mesh.numUVs(uv_set)}) does not match "
                f"length of uvs ({len(uvs)})"
            )

        u_values = om.MFloatArray([uv[0] for uv in uvs])
        v_values = om.MFloatArray([uv[1] for uv in uvs])
        mesh.setUVs(u_values, v_values, uv_set)

    def uv_at_point(self, position: list[float], space: str = "object", uv_set: str|None = None) -> tuple[float, float, int]:
        """
        Returns the UV of the point on the mesh closest to ``position``
        as a tuple of ``(u, v, face_id)``. Useful for placing follicles
        or pinning objects to a surface.
        """
        mesh = self._mesh()
        u, v, face_id = mesh.getUVAtPoint(
            om.MPoint(position[0], position[1], position[2]),
            self._resolve_space(space),
            self._resolve_uv_set(uv_set, mesh),
        )
        return u, v, face_id

    # ------------------------------------------------------------------
    # spatial queries
    # ------------------------------------------------------------------

    def closest_point(self, position: list[float], space: str = "object") -> tuple[list[float], list[float], int]:
        """
        Returns the point on the mesh closest to ``position`` as a tuple
        of ``([x, y, z], [nx, ny, nz], face_id)`` — the closest position,
        the surface normal at that position and the id of the face it
        lies on. Both the input and the results are expressed in
        ``space``.
        """
        point, normal, face_id = self._mesh().getClosestPointAndNormal(
            om.MPoint(position[0], position[1], position[2]),
            self._resolve_space(space),
        )
        return [point.x, point.y, point.z], [normal.x, normal.y, normal.z], face_id

    def ray_intersection(
            self,
            source: list[float],
            direction: list[float],
            space: str = "world",
            max_distance: float = 99999.0,
            both_directions: bool = False,
    ) -> tuple[list[float], int]|None:
        """
        Casts a ray from ``source`` along ``direction`` and returns the
        nearest hit on the mesh as a tuple of ``([x, y, z], face_id)``,
        or None if the ray misses. ``source``, ``direction`` and the
        hit point are all expressed in ``space`` (world by default).
        Hits further than ``max_distance`` are ignored, and
        ``both_directions`` also tests the ray backwards from source.
        """
        result = self._mesh().closestIntersection(
            om.MFloatPoint(source[0], source[1], source[2]),
            om.MFloatVector(direction[0], direction[1], direction[2]),
            self._resolve_space(space),
            max_distance,
            both_directions,
        )
        # -- API 2.0 returns None on a miss (older builds returned a
        # -- tuple with a hit face of -1), so guard against both
        if not result or result[2] < 0:
            return None

        hit_point, hit_face = result[0], result[2]
        return [hit_point.x, hit_point.y, hit_point.z], hit_face

    # ------------------------------------------------------------------
    # shading
    # ------------------------------------------------------------------

    def shading_engines(self) -> mref.ReferenceList:
        """
        Returns the shading engines (shading groups) assigned to this
        mesh — whole-object and per-face assignments alike — for the
        first instance of the shape.
        """
        dag_path = self._dag_path()
        shading_engines, _ = self._mesh().getConnectedShaders(dag_path.instanceNumber())
        return mref.ReferenceList(
            mref.get(engine)
            for engine in shading_engines
        )

    # ------------------------------------------------------------------
    # skin discovery
    # ------------------------------------------------------------------

    def skin(self) -> mref.ReferencedItem|None:
        """
        Returns a ReferencedItem for the SkinCluster bound to this
        mesh, or None if no skin cluster is connected.
        """
        skins = self.item.inputs(type="skinCluster")
        if skins:
            return skins[0]
        return None

    # ------------------------------------------------------------------
    # component paths / skinnable-shape protocol
    # ------------------------------------------------------------------

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

    def face_component_path(self, face_id: int) -> str:
        """
        Returns the fully qualified path to the face with the given id,
        in the form ``<full_path>.f[N]``.
        """
        return f"{self.item.full_name()}.f[{face_id}]"

    def edge_component_path(self, edge_id: int) -> str:
        """
        Returns the fully qualified path to the edge with the given id,
        in the form ``<full_path>.e[N]``.
        """
        return f"{self.item.full_name()}.e[{edge_id}]"

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _dag_path(self) -> om.MDagPath:
        """
        Returns a DAG path to this shape. Resolved per call so it stays
        valid if the shape is re-parented.
        """
        return om.MDagPath.getAPathTo(self._pointer)

    def _mesh(self) -> om.MFnMesh:
        """
        Returns an MFnMesh built from a DAG path to this shape, so that
        world space queries are available. Built lazily per call
        because ``MFnMesh`` raises on a mesh node with no geometry data,
        which would otherwise make such nodes impossible to wrap.
        """
        return om.MFnMesh(self._dag_path())

    def _validate_uv_set(self, uv_set: str, mesh: om.MFnMesh|None = None) -> None:
        """
        Raises ``ValueError`` if the mesh has no UV set with the given name
        """
        names = list((mesh or self._mesh()).getUVSetNames())
        if uv_set not in names:
            raise ValueError(
                f"Unknown UV set {uv_set!r}; expected one of {tuple(names)}"
            )

    def _resolve_uv_set(self, uv_set: str|None, mesh: om.MFnMesh) -> str:
        """
        Returns ``uv_set`` if given (validating that it exists), or the
        mesh's current UV set name otherwise.
        """
        if uv_set is None:
            return mesh.currentUVSetName()
        self._validate_uv_set(uv_set, mesh)
        return uv_set

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
