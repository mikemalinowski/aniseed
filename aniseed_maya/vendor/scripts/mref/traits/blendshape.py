import mref
import maya
from maya import cmds
from maya.api import OpenMaya as om


class Blendshape(mref.Trait):

    def __init__(self, *args, **kwargs):
        super(Blendshape, self).__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kBlendShape):
            return True
        return False

    def geometry(self):
        return mref.get(
            cmds.blendShape(
                self.item.full_name(),
                query=True,
                geometry=True,
            )[0],
        ).parent()

    def scene_targets(self):
        """
        Returns a list of meshes in the scene for this target
        :return:
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
            [
                mref.get(target).parent()
                for target in targets
            ]
        )

    def unpack(self):
        blendshape = self.item.full_name()

        base_geo = cmds.blendShape(blendshape, q=True, g=True)
        if not base_geo:
            raise RuntimeError("No base geometry connected")

        self.disconnect_driving_inputs()

        base_geo = base_geo[0]

        alias_list = cmds.aliasAttr(blendshape, q=True) or []
        weights = cmds.blendShape(blendshape, q=True, w=True)

        created = []

        for i in range(len(weights)):
            # Resolve target name
            target_name = None
            for j in range(0, len(alias_list), 2):
                if alias_list[j + 1] == f"weight[{i}]":
                    target_name = alias_list[j]
                    break
            if not target_name:
                target_name = f"target_{i}"

            # 🔍 Check if a mesh is already connected
            plug = f"{blendshape}.inputTarget[0].inputTargetGroup[{i}].inputTargetItem[6000].inputGeomTarget"
            connections = cmds.listConnections(plug, s=True, d=False) or []

            if connections:
                # Already has a source mesh → skip
                continue

            # Store current weights
            current_weights = [cmds.getAttr(f"{blendshape}.w[{j}]") for j in range(len(weights))]

            # Zero all weights
            for j in range(len(weights)):
                cmds.setAttr(f"{blendshape}.w[{j}]", 0)

            # Activate only this target
            cmds.setAttr(f"{blendshape}.w[{i}]", 1)

            # --- Extract target ---
            dup = cmds.duplicate(base_geo, name=target_name)[0]

            # Bake deformation
            cmds.delete(dup, ch=True)

            # Restore weights
            for j, val in enumerate(current_weights):
                cmds.setAttr(f"{blendshape}.w[{j}]", val)

            # Connect reconstructed mesh back
            cmds.blendShape(
                blendshape,
                e=True,
                t=(base_geo, i, dup, 1.0)
            )

            # 🔧 Force alias back to original name (prevents "name1")
            cmds.aliasAttr(target_name, f"{blendshape}.w[{i}]")

            created.append(dup)

        return created

    def disconnect_driving_inputs(self):
        blendshape = self.item.full_name()
        alias_list = cmds.aliasAttr(blendshape, q=True) or []

        for j in range(0, len(alias_list), 2):
            alias = alias_list[j]
            maya.mel.eval(f"CBdeleteConnection \"{blendshape}.{alias}\";")

    def alias_attributes(self):
        aliases = cmds.aliasAttr(self.item.name(), q=True)[::2]
        return mref.ReferenceList(
            [
                mref.get(f"{self.item.name()}.{alias}")
                for alias in aliases
            ]
        )

    def weight_mapping(self):
        output = dict()

        aliases = cmds.aliasAttr(self.item.name(), q=True)
        for i in range(0, len(aliases), 2):
            alias = aliases[i]
            weight = aliases[i + 1]
            output[alias] = weight
        return output
