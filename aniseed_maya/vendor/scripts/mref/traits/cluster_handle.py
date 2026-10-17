import mref
from maya.api import OpenMaya as om


class ClusterHandle(mref.Trait):
    """
    Trait bound to any node with ``MFn.kCluster`` — the ``clusterHandle``
    shape which draws a cluster in the viewport. Exposes the cluster
    deformer the handle belongs to and the geometry it deforms, matching
    the ``DeformerHandle`` trait for nonLinear handles.

    Note that ``MFn.kCluster`` is the handle shape; the cluster deformer
    node itself is ``MFn.kClusterFilter`` (see the ``Cluster`` trait).
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
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kCluster)

    def deformer(self) -> mref.ReferencedItem|None:
        """
        Returns the cluster deformer this handle belongs to, or None if
        the handle is not connected to a cluster.
        """
        # -- The handle shape's clusterTransforms feeds the cluster's
        # -- clusterXforms
        plug = self._dependency_node.findPlug("clusterTransforms", False)
        for element_index in range(plug.numElements()):
            for destination in plug.elementByPhysicalIndex(element_index).destinations():
                if destination.node().hasFn(om.MFn.kClusterFilter):
                    return mref.get(destination.node())
        return None

    def deformed_geometry(self) -> mref.ReferenceList:
        """
        Returns the shapes deformed by the cluster this handle belongs
        to, or an empty list if the handle has no cluster.
        """
        deformer = self.deformer()
        if deformer is None:
            return mref.ReferenceList()
        return deformer.output_geometry()
