import mref
from maya import cmds
from maya.api import OpenMaya as om


class ShadingEngine(mref.Trait):
    """
    Trait bound to any node with ``MFn.kShadingEngine`` — shading groups.
    Stacks on top of the generic ``ObjectSet`` trait (a shading engine is
    an object set), so membership edits use ``members`` /
    ``add_members`` / ``remove_members`` from there; assigning geometry
    to a shading group is ``add_members``. This trait adds the shader
    slots (surface, displacement, volume) and geometry-level assignment
    queries.
    """

    # -- Sits above the generic ObjectSet trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kShadingEngine)

    def surface_shader(self) -> mref.ReferencedItem|None:
        """
        Returns the shader connected to this shading group's
        ``surfaceShader`` slot, or None if nothing is connected.
        """
        return self._slot("surfaceShader")

    def set_surface_shader(self, shader: "mref.ReferencedItem|str|None") -> None:
        """
        Connects the given shader's ``outColor`` into this shading
        group's ``surfaceShader`` slot. Passing None disconnects the slot.
        """
        self._set_slot("surfaceShader", shader, "outColor")

    def displacement_shader(self) -> mref.ReferencedItem|None:
        """
        Returns the node connected to this shading group's
        ``displacementShader`` slot, or None if nothing is connected.
        """
        return self._slot("displacementShader")

    def set_displacement_shader(self, shader: "mref.ReferencedItem|str|None") -> None:
        """
        Connects the given displacement node's ``displacement`` output
        into this shading group's ``displacementShader`` slot. Passing
        None disconnects the slot.
        """
        self._set_slot("displacementShader", shader, "displacement")

    def volume_shader(self) -> mref.ReferencedItem|None:
        """
        Returns the shader connected to this shading group's
        ``volumeShader`` slot, or None if nothing is connected.
        """
        return self._slot("volumeShader")

    def set_volume_shader(self, shader: "mref.ReferencedItem|str|None") -> None:
        """
        Connects the given shader's ``outColor`` into this shading
        group's ``volumeShader`` slot. Passing None disconnects the slot.
        """
        self._set_slot("volumeShader", shader, "outColor")

    def assigned_geometry(self) -> mref.ReferenceList:
        """
        Returns the unique shape nodes which have this shading group
        assigned, either to the whole object or to some of its faces.
        Unlike ``members`` this never returns component strings.
        """
        members = cmds.sets(self.item.full_name(), query=True) or []
        shapes = []

        for member in members:
            # -- Resolve components and transforms down to their shapes
            node = member.split(".")[0]
            if not cmds.objectType(node, isAType="shape"):
                node_shapes = cmds.listRelatives(
                    node,
                    shapes=True,
                    noIntermediate=True,
                    fullPath=True,
                ) or []
            else:
                node_shapes = cmds.ls(node, long=True)

            for shape in node_shapes:
                if shape not in shapes:
                    shapes.append(shape)

        return mref.ReferenceList(mref.get(shape) for shape in shapes)

    def assigned_components(self) -> list[str]:
        """
        Returns only the per-face (component) assignments of this shading
        group, as long-named component strings such as
        ``"|pCube1|pCubeShape1.f[0:2]"``. Whole-object assignments are
        not included.
        """
        members = cmds.sets(self.item.full_name(), query=True) or []
        return [
            member
            for member in cmds.ls(members, long=True) or []
            if "." in member
        ]

    def _slot(self, attribute_name: str) -> mref.ReferencedItem|None:
        plug = om.MFnDependencyNode(self._pointer).findPlug(attribute_name, False)
        source = plug.source()

        if source.isNull:
            return None

        return mref.get(source.node())

    def _set_slot(self, attribute_name: str, shader, output_attribute: str) -> None:
        destination = f"{self.item.full_name()}.{attribute_name}"

        if shader is None:
            sources = cmds.listConnections(destination, source=True, destination=False, plugs=True) or []
            for source in sources:
                cmds.disconnectAttr(source, destination)
            return

        if isinstance(shader, mref.ReferencedItem):
            shader = shader.full_name()

        cmds.connectAttr(f"{shader}.{output_attribute}", destination, force=True)
