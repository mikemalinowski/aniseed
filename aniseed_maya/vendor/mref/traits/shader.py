import mref
from maya import cmds
from maya.api import OpenMaya as om


class Shader(mref.Trait):
    """
    Trait bound to surface shader nodes — any node type whose
    classification contains ``shader/surface`` (lambert, blinn, phong,
    standardSurface, openPBRSurface, surfaceShader, aiStandardSurface,
    aiFlat, ...). There is no common ``MFn`` constant for surface
    shaders across native and plugin types, so binding uses
    ``cmds.getClassification`` cached per node type name.

    Exposes the shading groups the shader feeds, geometry assignment
    (creating a shading group when needed) and a generic colour accessor.
    """

    # -- Cache of node type name -> whether it is a surface shader.
    # -- can_bind runs for every ReferencedItem, so getClassification
    # -- must only be called once per type.
    _classified_types = dict()

    # -- Attributes tried, in order, when reading or writing the
    # -- shader's main colour. baseColor covers standardSurface,
    # -- openPBRSurface and aiStandardSurface; color covers lambert and
    # -- its derivatives as well as aiFlat; outColor is only used when
    # -- it is writable (surfaceShader).
    _colour_attributes = ["baseColor", "color", "outColor"]

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if not isinstance(pointer, om.MObject) or not pointer.hasFn(om.MFn.kDependencyNode):
            return False

        # -- Shaders are never DAG nodes, which cheaply rules out the
        # -- bulk of scene nodes before any lookup.
        if pointer.hasFn(om.MFn.kDagNode):
            return False

        type_name = om.MFnDependencyNode(pointer).typeName
        result = cls._classified_types.get(type_name)

        if result is None:
            result = _is_surface_shader_type(type_name)
            cls._classified_types[type_name] = result

        return result

    def shading_groups(self) -> mref.ReferenceList:
        """
        Returns the shading groups whose ``surfaceShader`` slot this
        shader is connected to.
        """
        connections = cmds.listConnections(
            f"{self.item.full_name()}.outColor",
            source=False,
            destination=True,
            plugs=True,
        ) or []

        results = mref.ReferenceList()

        for connection in connections:
            node, attribute_name = connection.split(".", 1)
            if attribute_name != "surfaceShader":
                continue
            if not cmds.objectType(node, isAType="shadingEngine"):
                continue

            item = mref.get(node)
            if item not in results:
                results.append(item)

        return results

    def create_shading_group(self) -> mref.ReferencedItem:
        """
        Returns the first shading group this shader feeds, creating and
        connecting a new one (named ``<shader>SG``) if there is none.
        """
        existing = self.shading_groups()
        if existing:
            return existing[0]

        shading_group = cmds.sets(
            renderable=True,
            noSurfaceShader=True,
            empty=True,
            name=f"{self.item.name()}SG",
        )
        cmds.connectAttr(
            f"{self.item.full_name()}.outColor",
            f"{shading_group}.surfaceShader",
            force=True,
        )
        return mref.get(shading_group)

    def assign_to(self, geometry: "list|mref.ReferencedItem|str") -> None:
        """
        Assigns this shader to the given geometry — transforms, shapes
        or face components (``"pCube1.f[0:3]"``). A shading group is
        created if the shader does not have one yet.
        """
        if not isinstance(geometry, (list, tuple)):
            geometry = [geometry]

        names = [
            node.full_name() if isinstance(node, mref.ReferencedItem) else node
            for node in geometry
        ]

        shading_group = self.create_shading_group()
        cmds.sets(names, edit=True, forceElement=shading_group.full_name())

    def assigned_geometry(self) -> mref.ReferenceList:
        """
        Returns the unique shape nodes which have this shader assigned
        (to the whole object or to some faces) via any of its shading
        groups.
        """
        shapes = []

        for shading_group in self.shading_groups():
            members = cmds.sets(shading_group.full_name(), query=True) or []

            for member in members:
                node = member.split(".")[0]

                if cmds.objectType(node, isAType="shape"):
                    node_shapes = cmds.ls(node, long=True)
                else:
                    node_shapes = cmds.listRelatives(
                        node,
                        shapes=True,
                        noIntermediate=True,
                        fullPath=True,
                    ) or []

                for shape in node_shapes:
                    if shape not in shapes:
                        shapes.append(shape)

        return mref.ReferenceList(mref.get(shape) for shape in shapes)

    def colour_attribute(self) -> mref.ReferencedItem|None:
        """
        Returns the attribute holding this shader's main colour —
        ``baseColor`` (standardSurface, openPBRSurface,
        aiStandardSurface), ``color`` (lambert family, aiFlat) or a
        writable ``outColor`` (surfaceShader). Returns None if the
        shader type has none of these.
        """
        name = self._colour_attribute_name()
        if name is None:
            return None
        return mref.get(f"{self.item.full_name()}.{name}")

    def colour(self) -> list[float]|None:
        """
        Returns the ``[r, g, b]`` main colour of this shader (see
        :meth:`colour_attribute`), or None if it has no recognised
        colour attribute.
        """
        name = self._colour_attribute_name()
        if name is None:
            return None
        return list(cmds.getAttr(f"{self.item.full_name()}.{name}")[0])

    def set_colour(self, colour: list[float]) -> None:
        """
        Sets the ``[r, g, b]`` main colour of this shader (see
        :meth:`colour_attribute`). Raises RuntimeError if the shader has
        no recognised colour attribute.
        """
        name = self._colour_attribute_name()
        if name is None:
            raise RuntimeError(
                f"{self.item.full_name()} has no recognised colour attribute"
            )
        cmds.setAttr(f"{self.item.full_name()}.{name}", *colour, type="double3")

    def _colour_attribute_name(self) -> str|None:
        node = self.item.full_name()

        for attribute_name in self._colour_attributes:
            if not cmds.attributeQuery(attribute_name, node=node, exists=True):
                continue
            if not cmds.attributeQuery(attribute_name, node=node, writable=True):
                continue
            # -- Ignore child attributes of compounds/arrays such as
            # -- layeredShader's inputs[].color
            if cmds.attributeQuery(attribute_name, node=node, listParent=True):
                continue
            # -- attributeQuery returns the child count wrapped in a list
            child_count = cmds.attributeQuery(attribute_name, node=node, numberOfChildren=True) or [0]
            if child_count[0] != 3:
                continue
            return attribute_name

        return None


def _is_surface_shader_type(type_name: str) -> bool:
    """
    Returns True if the classification of the given node type marks it
    as a surface shader.
    """
    try:
        classifications = cmds.getClassification(type_name) or []
    except RuntimeError:
        return False

    for classification in classifications:
        for token in classification.split(":"):
            if token.startswith("shader/surface") or "/shader/surface" in token:
                return True

    return False
