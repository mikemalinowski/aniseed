import mref
from maya import cmds
from maya.api import OpenMaya as om


class DeformerHandle(mref.Trait):
    """
    Trait bound to any node with ``MFn.kDeformFunc`` — the handle
    shapes of the nonLinear deformers (``deformBend``, ``deformTwist``,
    ``deformFlare``, ``deformSine``, ``deformSquash`` and
    ``deformWave``). Exposes the nonLinear deformer the handle drives,
    its deformer type and the geometry it deforms.

    The handle's parameter attributes (curvature, bounds, ...) are
    driven by the deformer, so edit them through the deformer's
    ``set_parameter``.
    """

    # -- Sits above the generic Shape trait
    priority = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kDeformFunc)

    def deformer(self) -> mref.ReferencedItem|None:
        """
        Returns the nonLinear deformer this handle belongs to, or None
        if the handle is not connected to a deformer.
        """
        # -- The handle shape's deformerData feeds the deformer
        plug = self._dependency_node.findPlug("deformerData", False)
        for destination in plug.destinations():
            if destination.node().hasFn(om.MFn.kNonLinear):
                return mref.get(destination.node())
        return None

    def deformer_type(self) -> str:
        """
        Returns the type of deformer this handle represents — one of
        ``"bend"``, ``"twist"``, ``"flare"``, ``"sine"``, ``"squash"``
        or ``"wave"``.
        """
        node_type = cmds.nodeType(self.item.full_name())
        if node_type.startswith("deform"):
            return node_type[len("deform"):].lower()
        return node_type

    def deformed_geometry(self) -> mref.ReferenceList:
        """
        Returns the shapes deformed by the deformer this handle belongs
        to, or an empty list if the handle has no deformer.
        """
        deformer = self.deformer()
        if deformer is None:
            return mref.ReferenceList()
        return deformer.output_geometry()
