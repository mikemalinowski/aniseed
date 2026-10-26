import mref
from maya import cmds
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as oma


class GeometryFilter(mref.Trait):
    """
    Trait bound to any node with ``MFn.kGeometryFilt`` — the base of every
    deformer in Maya (skin clusters, blendshapes, clusters, lattices,
    wires, nonlinears, delta mush, tension and so on). Exposes the
    geometry being deformed, the envelope, and per-component deformer
    weights.

    Priority ``0``. Deformer-specific traits (``SkinCluster``,
    ``Blendshape``, ``Cluster``, ...) sit at priority ``1`` so their
    more specific behaviour wins where method names overlap.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._geometry_filter = oma.MFnGeometryFilter(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kGeometryFilt)

    def input_geometry(self) -> mref.ReferenceList:
        """
        Returns the shapes feeding into this deformer
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in self._geometry_filter.getInputGeometry()
        )

    def output_geometry(self) -> mref.ReferenceList:
        """
        Returns the shapes this deformer is deforming
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in self._geometry_filter.getOutputGeometry()
        )

    def envelope(self) -> float:
        """
        Returns the envelope value of the deformer
        """
        return self._geometry_filter.envelope

    def set_envelope(self, value: float) -> None:
        """
        Sets the envelope value of the deformer
        """
        cmds.setAttr(f"{self.item.full_name()}.envelope", value)

    def geometry_index(self, shape: mref.ReferencedItem|str) -> int:
        """
        Returns the plug index this deformer uses for the given output
        shape. This is the index into ``input[]``, ``outputGeometry[]``
        and ``weightList[]``.
        """
        shape = mref.get(shape)
        return self._geometry_filter.indexForOutputShape(shape.pointer())

    def deformer_weights(self, shape: mref.ReferencedItem|str = None) -> list[float]:
        """
        Returns the per-component deformer weights (the paintable
        ``weightList`` values) for the given shape, or the first output
        shape when no shape is given. Components with no stored value
        report Maya's default of ``1.0``.

        The shape must support the skinnable-shape protocol
        (``component_count()``), which ``Mesh``, ``NurbsCurve`` and
        ``NurbsSurface`` provide.

        On blendshapes in Maya 2024 and earlier these are read from
        ``inputTarget[n].baseWeights``, which is where those versions
        store the painted base weights.
        """
        shape, plug = self._weights_plug(shape)
        weights = [1.0] * shape.component_count()

        for index in plug.getExistingArrayAttributeIndices():
            if index < len(weights):
                weights[index] = plug.elementByLogicalIndex(index).asFloat()

        return weights

    def set_deformer_weights(self, weights: list[float], shape: mref.ReferencedItem|str = None) -> None:
        """
        Sets the per-component deformer weights for the given shape, or
        the first output shape when no shape is given. ``weights`` must
        have exactly one entry per component.
        """
        shape, plug = self._weights_plug(shape)

        if len(weights) != shape.component_count():
            raise ValueError(
                f"Number of components ({shape.component_count()}) does not "
                f"match length of weights ({len(weights)})"
            )

        for index, weight in enumerate(weights):
            plug.elementByLogicalIndex(index).setFloat(weight)

    def _weights_plug(self, shape) -> tuple:
        """
        Resolves the shape (defaulting to the first output shape) and
        returns it along with its ``weightList[n].weights`` plug.
        """
        if shape is None:
            outputs = self.output_geometry()
            if not outputs:
                raise RuntimeError(f"{self.item.name()} is not deforming any geometry")
            shape = outputs[0]

        shape = mref.get(shape)
        index = self.geometry_index(shape)
        dependency_node = om.MFnDependencyNode(self._pointer)

        # -- Up to Maya 2024 a blendshape is a plain geometryFilter with no
        # -- weightList - its painted weights live in inputTarget[n].baseWeights.
        # -- From 2025 it is a weightGeometryFilter which uses weightList and
        # -- ignores baseWeights, so it falls through to the generic path.
        if self._pointer.hasFn(om.MFn.kBlendShape) and not self._pointer.hasFn(om.MFn.kWeightGeometryFilt):
            input_target = dependency_node.findPlug("inputTarget", False).elementByLogicalIndex(index)
            return shape, input_target.child(dependency_node.attribute("baseWeights"))

        if not self.item.has_attribute("weightList"):
            raise RuntimeError(f"{self.item.name()} does not support paintable weights")

        weight_list = dependency_node.findPlug("weightList", False)
        weights_plug = weight_list.elementByLogicalIndex(index).child(0)
        return shape, weights_plug
