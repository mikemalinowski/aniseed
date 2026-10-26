import mref
from maya import cmds
from maya import mel
from maya.api import OpenMaya as om


# -- Maya encodes in-between target weights as ``int(weight * 1000) + 5000``,
# -- so the "full" target at weight 1.0 lives at index 6000 in the
# -- ``inputTargetItem`` multi-attribute.
_FULL_TARGET_INDEX = 6000


class Blendshape(mref.Trait):
    """
    Trait bound to any node with ``MFn.kBlendShape``. Exposes the
    blendshape's geometry, scene-side target meshes, alias attributes,
    and a utility (:meth:`unpack`) to extract deformed result meshes
    for any targets that don't currently have an explicit source mesh
    connected. Also provides target management (add / remove / rename /
    in-betweens) addressed by name or index, target weights, and the
    blendshape-specific paintable base and per-target weights.
    """

    # -- Sits above the generic GeometryFilter trait
    priority = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        Returns True if the given pointer is a blendShape node.
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kBlendShape)

    def geometry(self) -> mref.ReferencedItem | None:
        """
        Returns the transform that owns the first geometry this
        blendshape deforms, or None if no geometry is connected.
        """
        geo = cmds.blendShape(
            self.item.full_name(),
            query=True,
            geometry=True,
        ) or []

        if not geo:
            return None

        return mref.get(geo[0]).parent()

    def scene_targets(self) -> mref.ReferenceList:
        """
        Returns the transforms of every mesh in the scene that's
        connected as a source for one of this blendshape's targets.
        Walks the
        ``inputTarget[*].inputTargetGroup[*].inputTargetItem[*].inputGeomTarget``
        plug tree and collects any upstream meshes.

        Only mesh shapes (``MFn.kMesh``) are returned — NURBS surface
        targets, if any, are not included.
        """
        targets = []

        input_target_plug = self._dependency_node.findPlug("inputTarget", True)

        for i in range(input_target_plug.numElements()):
            geom_elem = input_target_plug.elementByPhysicalIndex(i)

            input_target_group = geom_elem.child(0)  # inputTargetGroup

            for j in range(input_target_group.numElements()):
                group_elem = input_target_group.elementByPhysicalIndex(j)

                input_target_item = group_elem.child(0)  # inputTargetItem

                for k in range(input_target_item.numElements()):
                    item_elem = input_target_item.elementByPhysicalIndex(k)

                    input_geom = item_elem.child(0)  # inputGeomTarget

                    connections = input_geom.connectedTo(True, False)
                    for conn in connections:
                        node = conn.node()
                        if node.hasFn(om.MFn.kMesh):
                            targets.append(node)

        return mref.ReferenceList(
            mref.get(target).parent()
            for target in targets
        )

    def unpack(self) -> list:
        """
        Extracts a deformed result mesh for every target that doesn't
        currently have an explicit source mesh connected. Each
        extracted mesh is created by activating its target's weight
        in isolation, duplicating the base geometry to bake the
        result, and reconnecting that duplicate as the target's
        input mesh.

        Targets that already have a source mesh connected are
        skipped — only the "missing source" cases are extracted.

        Original blendshape weights are restored after extraction,
        even if an error occurs partway through (via try/finally).

        :return: List of names of the newly created mesh transforms.
        :raises RuntimeError: If the blendshape has no base geometry
            connected.
        """
        blendshape = self.item.full_name()

        base_geo = cmds.blendShape(blendshape, q=True, g=True)
        if not base_geo:
            raise RuntimeError("No base geometry connected")

        self.disconnect_driving_inputs()

        base_geo = base_geo[0]

        alias_list = cmds.aliasAttr(blendshape, q=True) or []
        weights = cmds.blendShape(blendshape, q=True, w=True) or []

        # -- One-pass lookup of weight-plug-name → alias name. The
        # -- alias list is laid out as
        # -- [alias_name, weight[i], alias_name, weight[j], ...].
        alias_by_weight = {
            alias_list[j + 1]: alias_list[j]
            for j in range(0, len(alias_list), 2)
        }

        # -- Snapshot the current weights once so they can be
        # -- restored after extraction completes (or on failure, via
        # -- the finally clause below).
        current_weights = [
            cmds.getAttr(f"{blendshape}.w[{j}]")
            for j in range(len(weights))
        ]

        created = []

        try:
            for i in range(len(weights)):
                target_name = alias_by_weight.get(
                    f"weight[{i}]",
                    f"target_{i}",
                )

                # -- Skip targets that already have a mesh connected.
                plug = (
                    f"{blendshape}.inputTarget[0].inputTargetGroup[{i}]"
                    f".inputTargetItem[{_FULL_TARGET_INDEX}].inputGeomTarget"
                )
                if cmds.listConnections(plug, s=True, d=False):
                    continue

                # -- Zero every weight, then activate only this one
                # -- so the duplicated base reflects this target's
                # -- contribution in isolation.
                for j in range(len(weights)):
                    cmds.setAttr(f"{blendshape}.w[{j}]", 0)
                cmds.setAttr(f"{blendshape}.w[{i}]", 1)

                # -- Duplicate the deformed base, then strip its
                # -- construction history to bake the deformation.
                dup = cmds.duplicate(base_geo, name=target_name)[0]
                cmds.delete(dup, ch=True)

                # -- Reconnect the baked mesh back as this target's
                # -- source.
                cmds.blendShape(
                    blendshape,
                    e=True,
                    t=(base_geo, i, dup, 1.0),
                )

                # -- Force the alias back to the original name —
                # -- without this, the new connection produces a
                # -- numbered duplicate alias like "name1".
                cmds.aliasAttr(target_name, f"{blendshape}.w[{i}]")

                created.append(dup)

        finally:
            # -- Always restore the weights, even if extraction
            # -- failed partway through. Leaves the scene in a
            # -- predictable state.
            for j, val in enumerate(current_weights):
                cmds.setAttr(f"{blendshape}.w[{j}]", val)

        return created

    def disconnect_driving_inputs(self) -> None:
        """
        Disconnects every external connection driving this
        blendshape's weight aliases. Used by :meth:`unpack` to
        isolate each target before extraction; safe to call
        standalone if you want to freeze the blendshape in its
        current driven state.

        Uses MEL's ``CBdeleteConnection`` because that's the only
        idiom that properly tears down breakdown-style connections
        (anim curves, set driven keys, animation layers, plain
        connections) without leaving residue.

        ``CBdeleteConnection`` lives in ``channelBoxCommand.mel`` and
        isn't auto-sourced until the user first interacts with Maya's
        channel box, so we source it defensively up-front. MEL's
        ``source`` is idempotent, and we swallow load errors so this
        works in environments where the file doesn't exist (e.g.
        headless installs); if the proc still isn't available
        afterwards the subsequent ``CBdeleteConnection`` call will
        fail loudly, which is the right behaviour.
        """
        try:
            mel.eval('source "channelBoxCommand";')
        except RuntimeError:
            pass

        blendshape = self.item.full_name()
        alias_list = cmds.aliasAttr(blendshape, q=True) or []

        for j in range(0, len(alias_list), 2):
            alias = alias_list[j]
            mel.eval(f'CBdeleteConnection "{blendshape}.{alias}";')

    def alias_attributes(self) -> mref.ReferenceList:
        """
        Returns a ReferenceList of the blendshape's aliased weight
        attributes — one entry per target, addressed by its alias
        name rather than ``weight[i]``.
        """
        aliases = cmds.aliasAttr(self.item.full_name(), q=True) or []
        return mref.ReferenceList(
            mref.get(f"{self.item.full_name()}.{alias}")
            for alias in aliases[::2]
        )

    def weight_mapping(self) -> dict:
        """
        Returns a dict mapping each target's alias name to its
        underlying weight plug, e.g.::

            {"smile": "weight[0]", "frown": "weight[1]", ...}
        """
        aliases = cmds.aliasAttr(self.item.full_name(), q=True) or []
        return {
            aliases[i]: aliases[i + 1]
            for i in range(0, len(aliases), 2)
        }

    # ------------------------------------------------------------------
    # Targets
    # ------------------------------------------------------------------

    def target_indices(self) -> list[int]:
        """
        Returns the (sparse) logical weight indices of every target, in
        ascending order.
        """
        return list(self._dependency_node.findPlug("weight", False).getExistingArrayAttributeIndices())

    def target_names(self) -> list[str]:
        """
        Returns the name (weight alias) of every target in index order.
        A target with no alias is reported as ``"weight[i]"``.
        """
        names_by_index = self._names_by_index()
        return [
            names_by_index.get(index, f"weight[{index}]")
            for index in self.target_indices()
        ]

    def target_index(self, name: str) -> int:
        """
        Returns the weight index of the target with the given name.

        :raises ValueError: If no target has that name.
        """
        return self._resolve_index(name)

    def target_weight(self, target: str|int) -> float:
        """
        Returns the current weight of a target, given by name or index.
        """
        return cmds.getAttr(f"{self.item.full_name()}.weight[{self._resolve_index(target)}]")

    def set_target_weight(self, target: str|int, value: float) -> None:
        """
        Sets the weight of a target, given by name or index.
        """
        cmds.setAttr(f"{self.item.full_name()}.weight[{self._resolve_index(target)}]", value)

    def zero_weights(self) -> None:
        """
        Sets every target weight to zero. Weights that are driven by a
        connection or locked are left untouched.
        """
        weight_plug = self._dependency_node.findPlug("weight", False)
        for index in weight_plug.getExistingArrayAttributeIndices():
            element = weight_plug.elementByLogicalIndex(index)
            if element.isDestination or element.isLocked:
                continue
            element.setFloat(0.0)

    def add_target(self, mesh: mref.ReferencedItem|str, name: str = None, index: int = None) -> int:
        """
        Adds the given mesh as a new target, at the next free index
        unless ``index`` is given, and returns that index. The target is
        named after the mesh unless ``name`` is given.
        """
        mesh = mref.get(mesh)

        if index is None:
            indices = self.target_indices()
            index = (max(indices) + 1) if indices else 0

        cmds.blendShape(
            self.item.full_name(),
            edit=True,
            target=(self._base_geometry_name(), index, mesh.full_name(), 1.0),
        )

        if name:
            self.rename_target(index, name)

        return index

    def remove_target(self, target: str|int) -> None:
        """
        Removes a target (given by name or index) entirely, including its
        weight, alias, in-betweens and paintable weights. Works whether or
        not a source mesh is still connected.
        """
        index = self._resolve_index(target)

        # -- blendShapeDeleteTargetGroup is the same proc the Shape Editor
        # -- uses; it also cleans up the target directory bookkeeping.
        mel.eval('source "blendShapeDeleteTargetGroup";')
        mel.eval(f'blendShapeDeleteTargetGroup "{self.item.full_name()}" {index};')

    def rename_target(self, target: str|int, new_name: str) -> None:
        """
        Renames a target (given by name or index) by re-aliasing its
        weight plug.
        """
        index = self._resolve_index(target)
        cmds.aliasAttr(new_name, f"{self.item.full_name()}.weight[{index}]")

    def add_in_between(self, target: str|int, mesh: mref.ReferencedItem|str, weight: float) -> None:
        """
        Adds the given mesh as an in-between of a target (given by name
        or index), triggered at the given weight (e.g. ``0.5``).
        """
        cmds.blendShape(
            self.item.full_name(),
            edit=True,
            inBetween=True,
            target=(self._base_geometry_name(), self._resolve_index(target), mref.get(mesh).full_name(), weight),
        )

    def in_between_weights(self, target: str|int) -> list[float]:
        """
        Returns the weights at which a target's in-betweens trigger,
        sorted ascending. The full target (weight ``1.0``) is excluded.
        """
        item_plug = self._target_group_plug(self._resolve_index(target)).child(0)  # inputTargetItem
        return [
            round((item_index - 5000) / 1000.0, 3)
            for item_index in sorted(item_plug.getExistingArrayAttributeIndices())
            if item_index != _FULL_TARGET_INDEX
        ]

    # ------------------------------------------------------------------
    # Paintable weights
    # ------------------------------------------------------------------

    def base_weights(self, shape: mref.ReferencedItem|str = None) -> list[float]:
        """
        Returns the per-component base weights painted on the
        blendshape for the given shape (default: first output shape).

        Where Maya stores these changed between versions — up to 2024
        they live in ``inputTarget[n].baseWeights``, from 2025 in the
        generic ``weightList`` (``baseWeights`` is then ignored). This
        is an alias of ``GeometryFilter.deformer_weights``, which reads
        whichever one drives the deformation.
        """
        return self.item.deformer_weights(shape)

    def set_base_weights(self, weights: list[float], shape: mref.ReferencedItem|str = None) -> None:
        """
        Sets the per-component base weights for the given shape (default:
        first output shape). ``weights`` must have one entry per component.
        See :meth:`base_weights` for where they are stored.
        """
        self.item.set_deformer_weights(weights, shape)

    def target_component_weights(self, target: str|int, shape: mref.ReferencedItem|str = None) -> list[float]:
        """
        Returns the per-component paintable weights of a single target
        (``inputTargetGroup[i].targetWeights``) for the given shape
        (default: first output shape).
        """
        shape, geometry_plug = self._input_target_plug(shape)
        group_plug = self._target_group_plug(self._resolve_index(target), geometry_plug)
        return _read_sparse_weights(group_plug.child(self._dependency_node.attribute("targetWeights")), shape)

    def set_target_component_weights(
            self,
            target: str|int,
            weights: list[float],
            shape: mref.ReferencedItem|str = None,
    ) -> None:
        """
        Sets the per-component paintable weights of a single target for
        the given shape (default: first output shape). ``weights`` must
        have one entry per component.
        """
        shape, geometry_plug = self._input_target_plug(shape)
        group_plug = self._target_group_plug(self._resolve_index(target), geometry_plug)
        _write_weights(group_plug.child(self._dependency_node.attribute("targetWeights")), shape, weights)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _names_by_index(self) -> dict:
        """
        Returns ``{weight_index: alias_name}`` for every aliased target.
        """
        return {
            int(plug_name[len("weight["):-1]): alias
            for alias, plug_name in self.weight_mapping().items()
            if plug_name.startswith("weight[")
        }

    def _resolve_index(self, target: str|int) -> int:
        """
        Resolves a target given by index, alias name or ``"weight[i]"``
        to its weight index.
        """
        if isinstance(target, int):
            return target

        if target.startswith("weight[") and target.endswith("]"):
            return int(target[len("weight["):-1])

        for index, name in self._names_by_index().items():
            if name == target:
                return index

        raise ValueError(f"{self.item.name()} has no target named {target!r}")

    def _base_geometry_name(self) -> str:
        """
        Returns the name of the first base geometry, as required by the
        ``blendShape -target`` flag.
        """
        geometry = cmds.blendShape(self.item.full_name(), query=True, geometry=True) or []
        if not geometry:
            raise RuntimeError(f"{self.item.name()} has no base geometry connected")
        return geometry[0]

    def _input_target_plug(self, shape) -> tuple:
        """
        Resolves the shape (default: first output shape) and returns it
        with its ``inputTarget[n]`` element plug.
        """
        if shape is None:
            outputs = self.item.output_geometry()
            if not outputs:
                raise RuntimeError(f"{self.item.name()} is not deforming any geometry")
            shape = outputs[0]

        shape = mref.get(shape)
        index = self.item.geometry_index(shape)
        plug = self._dependency_node.findPlug("inputTarget", False).elementByLogicalIndex(index)
        return shape, plug

    def _target_group_plug(self, index: int, geometry_plug: om.MPlug = None) -> om.MPlug:
        """
        Returns the ``inputTarget[n].inputTargetGroup[index]`` plug,
        defaulting to the first geometry.
        """
        if geometry_plug is None:
            geometry_plug = self._dependency_node.findPlug("inputTarget", False).elementByLogicalIndex(0)
        return geometry_plug.child(0).elementByLogicalIndex(index)


def _read_sparse_weights(plug: om.MPlug, shape: mref.ReferencedItem) -> list[float]:
    """
    Reads a sparse per-component float array plug, reporting Maya's
    default of ``1.0`` for components with no stored value.
    """
    weights = [1.0] * shape.component_count()
    for index in plug.getExistingArrayAttributeIndices():
        if index < len(weights):
            weights[index] = plug.elementByLogicalIndex(index).asFloat()
    return weights


def _write_weights(plug: om.MPlug, shape: mref.ReferencedItem, weights: list[float]) -> None:
    """
    Writes a full per-component weight list to a float array plug in a
    single ranged ``setAttr`` call.
    """
    count = shape.component_count()
    if len(weights) != count:
        raise ValueError(
            f"Number of components ({count}) does not "
            f"match length of weights ({len(weights)})"
        )
    if count:
        cmds.setAttr(f"{plug.name()}[0:{count - 1}]", *weights)