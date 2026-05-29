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
    connected.
    """

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