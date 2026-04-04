import mref
from maya import cmds
from maya.api import OpenMaya as om


class Mesh(mref.Trait):

    spaces = mref.constants.spaces

    def __init__(self, *args, **kwargs):
        super(Mesh, self).__init__(*args, **kwargs)
        self._mesh = om.MFnMesh(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kMesh):
            return True

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
        points = self._mesh.getPoints(self.spaces[space])
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
        list order.
        """

        point_array = om.MPointArray()
        point_array.setLength(len(positions))

        for i, (x, y, z) in enumerate(positions):
            point_array[i] = om.MPoint(x, y, z)

        # Apply all positions in one call
        self._mesh.setPoints(point_array, self.spaces[space])

    def vertex_position(self, vertex_id: int, space: str = "object") -> list[float]:
        """
        This returns a list containing the three components correlating to
        the x, y, z positions of the vertex.
        """
        point = self._mesh.getPoint(vertex_id, self.spaces[space])
        return [point.x, point.y, point.z]


    def set_vertex_position(self, vertex_id: int, position: list[float], space="object"):
        """
        This takes in a position list, in the format:

            [x, y, z]

        The vertex with the given id will then have its position set to those values.
        """
        self._mesh.setPoint(vertex_id, om.MPoint(*position), self.spaces[space])

    def skin(self) -> mref.ReferencedItem|None:
        """
        This will return a ReferencedItem for the SkinCluster if one is bound
        to this mesh.
        """
        try:
            return self.item.inputs(type="skinCluster")[0]
        except IndexError:
            return None

    def component_count(self) -> int:
        """
        This will return the vertex count
        """
        return self.vertex_count()

    def component_path(self, component_index: int) -> str:
        """
        This will return the fully qualified path of the component id
        """
        return f"{self.item.full_name()}.vtx[{component_index}]"
