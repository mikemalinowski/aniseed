import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- Built-in matrix utility node types, bound via their MFn constants
_MATRIX_NODE_FN_TYPES = (
    om.MFn.kMatrixMult,
    om.MFn.kMatrixAdd,
    om.MFn.kMatrixWtAdd,
    om.MFn.kDecomposeMatrix,
    om.MFn.kComposeMatrix,
    om.MFn.kPickMatrix,
    om.MFn.kBlendMatrix,
    om.MFn.kAimMatrix,
    om.MFn.kParentMatrix,
    om.MFn.kMatrixHold,
    om.MFn.kMatrixPass,
    om.MFn.kFourByFourMatrix,
    om.MFn.kUVPin,
    om.MFn.kProximityPin,
)

# -- Matrix nodes supplied by the matrixNodes plugin. These have no MFn
# -- constant of their own (they report kPluginDependNode) so they are
# -- matched by type name instead.
_PLUGIN_MATRIX_NODE_TYPES = frozenset((
    "inverseMatrix",
    "transposeMatrix",
))

# -- Per node type layout. ``inputs`` is an ordered list of
# -- ``(attribute, child, is_array)`` tuples describing where the matrix
# -- inputs live. ``child`` is the name of the matrix child for compound
# -- inputs (``target[n].targetMatrix``) or None for plain matrix plugs.
# -- ``output`` is the output matrix attribute (None when the node has
# -- no matrix output) and ``output_array`` flags array outputs.
_LAYOUTS = {
    "multMatrix": dict(inputs=[("matrixIn", None, True)], output="matrixSum", output_array=False),
    "addMatrix": dict(inputs=[("matrixIn", None, True)], output="matrixSum", output_array=False),
    "wtAddMatrix": dict(inputs=[("wtMatrix", "matrixIn", True)], output="matrixSum", output_array=False),
    "decomposeMatrix": dict(inputs=[("inputMatrix", None, False)], output=None, output_array=False),
    "composeMatrix": dict(inputs=[], output="outputMatrix", output_array=False),
    "inverseMatrix": dict(inputs=[("inputMatrix", None, False)], output="outputMatrix", output_array=False),
    "transposeMatrix": dict(inputs=[("inputMatrix", None, False)], output="outputMatrix", output_array=False),
    "pickMatrix": dict(inputs=[("inputMatrix", None, False)], output="outputMatrix", output_array=False),
    "blendMatrix": dict(
        inputs=[("inputMatrix", None, False), ("target", "targetMatrix", True)],
        output="outputMatrix",
        output_array=False,
    ),
    "parentMatrix": dict(
        inputs=[("inputMatrix", None, False), ("target", "targetMatrix", True)],
        output="outputMatrix",
        output_array=False,
    ),
    "aimMatrix": dict(
        inputs=[
            ("inputMatrix", None, False),
            ("primaryTargetMatrix", None, False),
            ("secondaryTargetMatrix", None, False),
        ],
        output="outputMatrix",
        output_array=False,
    ),
    "holdMatrix": dict(inputs=[("inMatrix", None, False)], output="outMatrix", output_array=False),
    "passMatrix": dict(inputs=[("inMatrix", None, False)], output="outMatrix", output_array=False),
    "fourByFourMatrix": dict(inputs=[], output="output", output_array=False),
    "uvPin": dict(inputs=[("relativeSpaceMatrix", None, False)], output="outputMatrix", output_array=True),
    "proximityPin": dict(
        inputs=[("inputMatrix", None, True), ("relativeSpaceMatrix", None, False)],
        output="outputMatrix",
        output_array=True,
    ),
}

_EMPTY_LAYOUT = dict(inputs=[], output=None, output_array=False)


def _source_plug_name(source: "mref.ReferencedItem|str") -> str:
    """
    Resolves a matrix source to a plug address. Attributes are used as
    given; nodes resolve to their ``worldMatrix[0]`` plug.
    """
    source = mref.get(source)
    if isinstance(source.pointer(), om.MPlug):
        return source.full_name()
    return f"{source.full_name()}.worldMatrix[0]"


class MatrixNode(mref.Trait):
    """
    Trait bound to Maya's matrix utility nodes — ``multMatrix``,
    ``addMatrix``, ``wtAddMatrix``, ``decomposeMatrix``,
    ``composeMatrix``, ``pickMatrix``, ``blendMatrix``, ``aimMatrix``,
    ``parentMatrix``, ``holdMatrix``, ``passMatrix``,
    ``fourByFourMatrix``, ``uvPin`` and ``proximityPin`` (via their
    ``MFn`` constants), plus the plugin-supplied ``inverseMatrix`` and
    ``transposeMatrix`` (by type name, as they only report
    ``kPluginDependNode``).

    Exposes a uniform view over the differing attribute layouts of
    these nodes: the output matrix value and plug, the ordered matrix
    input plugs and their sources, appending inputs, TRS decomposition
    of the output, and wiring the result onto a transform.

    Matrices are flat lists of 16 floats in the same layout as
    ``Transform.get_matrix`` (translation in elements 12-14).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._node_type = om.MFnDependencyNode(self._pointer).typeName
        self._layout = _LAYOUTS.get(self._node_type, _EMPTY_LAYOUT)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if not isinstance(pointer, om.MObject):
            return False

        for fn_type in _MATRIX_NODE_FN_TYPES:
            if pointer.hasFn(fn_type):
                return True

        if pointer.hasFn(om.MFn.kPluginDependNode):
            return om.MFnDependencyNode(pointer).typeName in _PLUGIN_MATRIX_NODE_TYPES

        return False

    def output_matrix_attribute(self, index: int = 0) -> mref.ReferencedItem|None:
        """
        Returns the output matrix attribute of this node, or None if the
        node has no matrix output (``decomposeMatrix``). ``index`` selects
        the element for nodes with array outputs (``uvPin``,
        ``proximityPin``) and is ignored otherwise.
        """
        output = self._layout["output"]
        if output is None:
            return None

        if self._layout["output_array"]:
            output = f"{output}[{index}]"

        return mref.get(f"{self.item.full_name()}.{output}")

    def output_matrix(self, index: int = 0) -> list[float]|None:
        """
        Returns the evaluated output matrix of this node as a flat list
        of 16 floats, or None if the node has no matrix output
        (``decomposeMatrix``). ``index`` selects the element for nodes
        with array outputs.
        """
        attribute = self.output_matrix_attribute(index)
        if attribute is None:
            return None
        return list(cmds.getAttr(attribute.full_name()))

    def input_matrix_attributes(self) -> mref.ReferenceList:
        """
        Returns the matrix input attributes of this node in evaluation
        order — for example ``matrixIn[0..n]`` on a ``multMatrix``, or
        ``inputMatrix`` followed by each ``target[n].targetMatrix`` on a
        ``blendMatrix``. Array inputs contribute their existing elements
        only.
        """
        node_name = self.item.full_name()
        results = mref.ReferenceList()

        for attribute, child, is_array in self._layout["inputs"]:
            if not is_array:
                results.append(mref.get(f"{node_name}.{attribute}"))
                continue

            for index in self._existing_indices(attribute):
                address = f"{node_name}.{attribute}[{index}]"
                if child:
                    address += f".{child}"
                results.append(mref.get(address))

        return results

    def matrix_sources(self) -> mref.ReferenceList:
        """
        Returns the attributes feeding this node's matrix inputs, in
        input order. Unconnected inputs are skipped. Each entry is an
        attribute ReferencedItem (use ``.node()`` for the driving node).
        """
        results = mref.ReferenceList()

        for attribute in self.input_matrix_attributes():
            sources = cmds.listConnections(
                attribute.full_name(),
                source=True,
                destination=False,
                plugs=True,
            ) or []
            if sources:
                results.append(mref.get(sources[0]))

        return results

    def add_matrix_input(
        self,
        source: "mref.ReferencedItem|str|list[float]",
    ) -> mref.ReferencedItem:
        """
        Feeds a matrix into the next free input slot and returns the
        input attribute used. Fixed inputs (``inputMatrix``,
        ``primaryTargetMatrix``, ...) are filled first if unconnected;
        after that a new element is appended to the node's array input
        (``matrixIn``, ``target``, ``wtMatrix``).

        ``source`` may be an attribute (connected directly), a node
        (its ``worldMatrix[0]`` is connected) or a flat list of 16
        floats (set as a static value). New ``wtAddMatrix`` elements
        get a weight of ``1.0``.
        """
        node_name = self.item.full_name()
        target = None

        for attribute, child, is_array in self._layout["inputs"]:
            address = f"{node_name}.{attribute}"

            if not is_array:
                if not cmds.listConnections(address, source=True, destination=False):
                    target = address
                    break
                continue

            indices = self._existing_indices(attribute)
            next_index = (max(indices) + 1) if indices else 0
            target = f"{address}[{next_index}]"

            if self._node_type == "wtAddMatrix":
                cmds.setAttr(f"{target}.weightIn", 1.0)

            if child:
                target += f".{child}"
            break

        if target is None:
            raise RuntimeError(
                f"{node_name} ({self._node_type}) has no free matrix input"
            )

        if isinstance(source, (list, tuple)) and len(source) == 16:
            cmds.setAttr(target, list(source), type="matrix")
        else:
            cmds.connectAttr(_source_plug_name(source), target, force=True)

        return mref.get(target)

    def output_translation(self, index: int = 0) -> list[float]:
        """
        Returns the translation ``[x, y, z]`` of the node's output. For a
        ``decomposeMatrix`` this is its ``outputTranslate``; for other
        nodes the output matrix is decomposed.
        """
        if self._node_type == "decomposeMatrix":
            return list(cmds.getAttr(f"{self.item.full_name()}.outputTranslate")[0])

        translation = self._output_transformation(index).translation(om.MSpace.kTransform)
        return [translation.x, translation.y, translation.z]

    def output_rotation(self, index: int = 0) -> list[float]:
        """
        Returns the rotation ``[x, y, z]`` in degrees of the node's output.
        For a ``decomposeMatrix`` this is its ``outputRotate`` (which
        honours ``inputRotateOrder``); for other nodes the output matrix
        is decomposed using the xyz rotate order.
        """
        if self._node_type == "decomposeMatrix":
            return list(cmds.getAttr(f"{self.item.full_name()}.outputRotate")[0])

        rotation = self._output_transformation(index).rotation(asQuaternion=False)
        return [om.MAngle(value).asDegrees() for value in (rotation.x, rotation.y, rotation.z)]

    def output_scale(self, index: int = 0) -> list[float]:
        """
        Returns the scale ``[x, y, z]`` of the node's output. For a
        ``decomposeMatrix`` this is its ``outputScale``; for other nodes
        the output matrix is decomposed.
        """
        if self._node_type == "decomposeMatrix":
            return list(cmds.getAttr(f"{self.item.full_name()}.outputScale")[0])

        return list(self._output_transformation(index).scale(om.MSpace.kTransform))

    def connect_output_to(
        self,
        transform: "mref.ReferencedItem|str",
        offset_parent_matrix: bool = True,
        index: int = 0,
    ) -> mref.ReferencedItem:
        """
        Drives the given transform with this node's result and returns
        the node that ends up wired to the transform.

        - A ``decomposeMatrix`` connects its translate / rotate / scale /
          shear outputs directly to the transform's channels.
        - Otherwise, by default, the output matrix is connected to the
          transform's ``offsetParentMatrix`` (the transform's own TRS
          then acts as a local offset on top).
        - With ``offset_parent_matrix=False`` a new ``decomposeMatrix`` is
          created between this node and the transform, its rotate order
          driven by the transform's ``rotateOrder``; the new node is
          returned. Note joint orients are not compensated for.
        """
        transform_name = mref.get(transform).full_name()

        if self._node_type == "decomposeMatrix":
            self._connect_trs(self.item.full_name(), transform_name)
            return self.item

        output = self.output_matrix_attribute(index)
        if output is None:
            raise RuntimeError(f"{self.item.full_name()} has no matrix output")

        if offset_parent_matrix:
            cmds.connectAttr(
                output.full_name(),
                f"{transform_name}.offsetParentMatrix",
                force=True,
            )
            return self.item

        decompose = cmds.createNode("decomposeMatrix")
        cmds.connectAttr(output.full_name(), f"{decompose}.inputMatrix", force=True)
        cmds.connectAttr(f"{transform_name}.rotateOrder", f"{decompose}.inputRotateOrder", force=True)
        self._connect_trs(decompose, transform_name)
        return mref.get(decompose)

    def _output_transformation(self, index: int) -> om.MTransformationMatrix:
        """
        Returns the output matrix wrapped in an MTransformationMatrix
        """
        values = self.output_matrix(index)
        if values is None:
            raise RuntimeError(f"{self.item.full_name()} has no matrix output")
        return om.MTransformationMatrix(om.MMatrix(values))

    def _existing_indices(self, attribute: str) -> list[int]:
        """
        Returns the existing logical indices of the given array attribute
        """
        return cmds.getAttr(
            f"{self.item.full_name()}.{attribute}",
            multiIndices=True,
        ) or []

    @staticmethod
    def _connect_trs(decompose_name: str, transform_name: str) -> None:
        """
        Connects a decomposeMatrix's TRS + shear outputs to a transform
        """
        for output, channel in (
            ("outputTranslate", "translate"),
            ("outputRotate", "rotate"),
            ("outputScale", "scale"),
            ("outputShear", "shear"),
        ):
            cmds.connectAttr(
                f"{decompose_name}.{output}",
                f"{transform_name}.{channel}",
                force=True,
            )
