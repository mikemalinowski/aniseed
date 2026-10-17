import mref
from maya import cmds
from maya.api import OpenMaya as om


class Shape(mref.Trait):
    """
    Trait bound to any node with ``MFn.kShape`` — meshes, curves,
    surfaces, locators, cameras, lights, lattices and every other shape
    type. Exposes the owning transform, the intermediate-object flag,
    bounding boxes and the deformer stack feeding the shape.

    Priority ``0``. Shape-specific traits (``Mesh``, ``NurbsCurve``,
    ``Camera``, ...) sit at priority ``1`` so they win if they ever
    define a method with the same name.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shape_dag_node = om.MFnDagNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kShape)

    def transform(self) -> mref.ReferencedItem|None:
        """
        Returns the transform which owns this shape, or None if the
        shape has no parent (which Maya does not normally allow).
        """
        return self.item.parent()

    def is_intermediate(self) -> bool:
        """
        Returns True if this shape is flagged as an intermediate object
        (typically the original, pre-deformation shape of a deformed mesh).
        """
        return self._shape_dag_node.isIntermediateObject

    def set_intermediate(self, state: bool) -> None:
        """
        Sets whether this shape is flagged as an intermediate object
        """
        cmds.setAttr(f"{self.item.full_name()}.intermediateObject", state)

    def bounding_box(self, space: str = "object") -> list[list[float]]:
        """
        Returns the bounding box of the shape as ``[[min_x, min_y, min_z],
        [max_x, max_y, max_z]]``. ``space`` may be ``"object"`` or
        ``"world"``.
        """
        if space == "object":
            box = self._shape_dag_node.boundingBox
            return [
                [box.min.x, box.min.y, box.min.z],
                [box.max.x, box.max.y, box.max.z],
            ]

        if space == "world":
            values = cmds.exactWorldBoundingBox(self.item.full_name())
            return [values[:3], values[3:]]

        raise ValueError(f"Unknown space {space!r}; expected 'object' or 'world'")

    def deformers(self, node_type: str = "geometryFilter") -> mref.ReferenceList:
        """
        Returns the deformers in this shape's history, nearest first.
        ``node_type`` can be used to narrow the result to a specific
        deformer type (for instance ``"skinCluster"``).
        """
        history = cmds.listHistory(
            self.item.full_name(),
            pruneDagObjects=True,
            interestLevel=1,
        ) or []

        return mref.ReferenceList(
            mref.get(node)
            for node in history
            if cmds.objectType(node, isAType=node_type)
        )
