import mref
from maya import cmds
from maya.api import OpenMaya as om


class Cluster(mref.Trait):
    """
    Trait bound to any node with ``MFn.kClusterFilter`` — the cluster
    deformer node. (Note that ``MFn.kCluster`` is, somewhat confusingly,
    the ``clusterHandle`` *shape* rather than the deformer.) Exposes the
    handle transform and handle shape, relative mode, the weighted node
    and re-binding of the cluster to the handle's current position.

    Input/output geometry, the envelope and the paintable per-component
    weights are provided by the generic ``GeometryFilter`` trait which is
    also bound to every cluster.
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
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kClusterFilter)

    def handle(self) -> mref.ReferencedItem|None:
        """
        Returns the transform driving the cluster (the node whose
        ``worldMatrix`` feeds the cluster's ``matrix`` input), or None
        if nothing is driving it.
        """
        source = self._dependency_node.findPlug("matrix", False).source()
        if source.isNull:
            return None
        return mref.get(source.node())

    def handle_shape(self) -> mref.ReferencedItem|None:
        """
        Returns the ``clusterHandle`` shape node which draws the cluster
        in the viewport, or None if there is no handle shape.
        """
        # -- The handle shape's clusterTransforms feeds clusterXforms
        source = self._dependency_node.findPlug("clusterXforms", False).source()
        if source.isNull:
            return None
        return mref.get(source.node())

    def is_relative(self) -> bool:
        """
        Returns True if the cluster is in relative mode — only the
        handle's local transformation (not that of its parents) affects
        the deformation.
        """
        return cmds.getAttr(f"{self.item.full_name()}.relative")

    def set_relative(self, state: bool) -> None:
        """
        Sets whether the cluster is in relative mode
        """
        cmds.setAttr(f"{self.item.full_name()}.relative", state)

    def weighted_node(self) -> mref.ReferencedItem|None:
        """
        Returns the cluster's weighted node — the transform whose matrix
        is used to deform the geometry. This is normally the cluster
        handle, but can be any transform.
        """
        result = cmds.cluster(self.item.full_name(), query=True, weightedNode=True)
        if not result:
            return None
        if isinstance(result, list):
            result = result[0]
        return mref.get(result)

    def set_weighted_node(self, node: mref.ReferencedItem|str) -> None:
        """
        Sets the transform which drives the cluster. Its world matrix is
        connected to the cluster's ``matrix`` input, so :meth:`handle`
        will report this node afterwards.
        """
        node_name = mref.get(node).full_name()
        cmds.cluster(
            self.item.full_name(),
            edit=True,
            weightedNode=(node_name, node_name),
        )

    def bind_pre_matrix(self) -> list[float]:
        """
        Returns the cluster's ``bindPreMatrix`` as a flat list of sixteen
        floats — the inverse of the handle's matrix at bind time. Maya
        leaves this unset (identity) for a handle created at the origin.
        """
        plug = self._dependency_node.findPlug("bindPreMatrix", False)
        try:
            data = plug.asMObject()
        except RuntimeError:
            return list(om.MMatrix())

        if data.isNull():
            return list(om.MMatrix())
        return list(om.MFnMatrixData(data).matrix())

    def rebind(self) -> None:
        """
        Re-binds the cluster to the current position of its handle by
        setting the ``bindPreMatrix`` to the handle's current world
        inverse matrix. Afterwards the handle in its current pose has no
        deforming effect — the geometry returns to its undeformed shape.
        """
        handle = self.handle()
        if handle is None:
            raise RuntimeError(f"{self.item.name()} has no handle to rebind to")

        bind_plug = f"{self.item.full_name()}.bindPreMatrix"
        if cmds.listConnections(bind_plug, source=True, destination=False):
            raise RuntimeError(f"{bind_plug} is connected and cannot be rebound")

        cmds.setAttr(
            bind_plug,
            cmds.getAttr(f"{handle.full_name()}.worldInverseMatrix[0]"),
            type="matrix",
        )
