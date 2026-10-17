import mref
from maya import cmds
from maya.api import OpenMaya as om


class Light(mref.Trait):
    """
    Trait bound to light shape nodes. Native Maya lights (ambient,
    directional, point, spot, area and volume) are matched via
    ``MFn.kLight``. Arnold (mtoa) lights such as ``aiAreaLight`` and
    ``aiSkyDomeLight`` do *not* derive from ``kLight``, so shape nodes
    whose type classification contains the ``light`` token are also
    bound (the classification lookup is cached per node type).

    Exposes colour, intensity, a light type label, shadow casting and
    light-linking (which objects this light illuminates).

    Note: :meth:`intensity` shadows property-style access to the Maya
    ``intensity`` attribute (``light.intensity``); use
    ``light.attribute("intensity")`` to get the plug.
    """

    # -- Sits above the generic Shape trait
    priority = 1

    # -- Cache of node type name -> whether its classification marks
    # -- it as a light. can_bind runs for every ReferencedItem, so
    # -- getClassification must only be called once per type.
    _classified_types = dict()

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if not isinstance(pointer, om.MObject):
            return False

        if pointer.hasFn(om.MFn.kLight):
            return True

        # -- Plugin lights (Arnold etc) are shapes but not kLight
        if not pointer.hasFn(om.MFn.kShape):
            return False

        type_name = om.MFnDependencyNode(pointer).typeName
        result = cls._classified_types.get(type_name)

        if result is None:
            result = _is_light_classification(type_name)
            cls._classified_types[type_name] = result

        return result

    def colour(self) -> list[float]:
        """
        Returns the ``[r, g, b]`` colour of the light
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.color")[0])

    def set_colour(self, colour: list[float]) -> None:
        """
        Sets the ``[r, g, b]`` colour of the light
        """
        cmds.setAttr(f"{self.item.full_name()}.color", *colour, type="double3")

    def intensity(self) -> float:
        """
        Returns the intensity of the light
        """
        return cmds.getAttr(f"{self.item.full_name()}.intensity")

    def set_intensity(self, value: float) -> None:
        """
        Sets the intensity of the light
        """
        cmds.setAttr(f"{self.item.full_name()}.intensity", value)

    def light_type(self) -> str:
        """
        Returns a renderer-agnostic label for the kind of light, derived
        from the node type with any ``ai`` prefix and ``Light`` suffix
        removed — for instance ``"spot"``, ``"point"``, ``"directional"``,
        ``"area"`` (for both ``areaLight`` and ``aiAreaLight``) or
        ``"skyDome"``.
        """
        label = cmds.nodeType(self.item.full_name())

        if label.startswith("ai") and len(label) > 2 and label[2].isupper():
            label = label[2:]

        if label.endswith("Light") and len(label) > 5:
            label = label[:-5]

        return label[0].lower() + label[1:]

    def casts_shadows(self) -> bool:
        """
        Returns True if this light casts shadows. For native Maya lights
        this is True if either raytraced or depth map shadows are on;
        for plugin (Arnold) lights the ``aiCastShadows`` attribute is used.
        """
        name = self.item.full_name()

        for attribute_name in self._shadow_attributes():
            if cmds.getAttr(f"{name}.{attribute_name}"):
                return True

        return False

    def set_casts_shadows(self, state: bool) -> None:
        """
        Turns shadow casting on or off. For native Maya lights, turning
        shadows on enables raytraced shadows and turning them off
        disables both raytraced and depth map shadows. For plugin
        (Arnold) lights ``aiCastShadows`` is set.
        """
        name = self.item.full_name()
        attributes = self._shadow_attributes()

        if state:
            attributes = attributes[:1]

        for attribute_name in attributes:
            cmds.setAttr(f"{name}.{attribute_name}", state)

    def illuminated_objects(self) -> mref.ReferenceList:
        """
        Returns the DAG objects this light illuminates according to
        Maya's light linking. Shading engines and other sets that the
        light-link query also reports are excluded.
        """
        linked = cmds.lightlink(
            query=True,
            light=self.item.full_name(),
            shapes=False,
            transforms=True,
        ) or []

        return mref.ReferenceList(
            mref.get(node)
            for node in cmds.ls(linked, dag=True, long=True) or []
        )

    def link_objects(self, objects: "list|mref.ReferencedItem|str") -> None:
        """
        Makes a light link between this light and the given object(s),
        so the light illuminates them.
        """
        cmds.lightlink(light=self.item.full_name(), object=_names(objects))

    def unlink_objects(self, objects: "list|mref.ReferencedItem|str") -> None:
        """
        Breaks the light link between this light and the given object(s),
        so the light no longer illuminates them.
        """
        cmds.lightlink(light=self.item.full_name(), object=_names(objects), b=True)

    def _shadow_attributes(self) -> list[str]:
        name = self.item.full_name()

        if self._pointer.hasFn(om.MFn.kLight):
            candidates = ["useRayTraceShadows", "useDepthMapShadows"]
        else:
            candidates = ["aiCastShadows"]

        return [
            attribute_name
            for attribute_name in candidates
            if cmds.attributeQuery(attribute_name, node=name, exists=True)
        ]


class SpotLight(mref.Trait):
    """
    Trait bound to any node with ``MFn.kSpotLight`` — Maya spot lights.
    Stacks on top of :class:`Light` to expose the spot-specific cone
    angle, penumbra angle and dropoff. Angles are in degrees.
    """

    # -- Sits above the generic Light trait
    priority = 2

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kSpotLight)

    def cone_angle(self) -> float:
        """
        Returns the cone angle of the spot light in degrees
        """
        return cmds.getAttr(f"{self.item.full_name()}.coneAngle")

    def set_cone_angle(self, degrees: float) -> None:
        """
        Sets the cone angle of the spot light in degrees
        """
        cmds.setAttr(f"{self.item.full_name()}.coneAngle", degrees)

    def penumbra_angle(self) -> float:
        """
        Returns the penumbra angle of the spot light in degrees
        """
        return cmds.getAttr(f"{self.item.full_name()}.penumbraAngle")

    def set_penumbra_angle(self, degrees: float) -> None:
        """
        Sets the penumbra angle of the spot light in degrees
        """
        cmds.setAttr(f"{self.item.full_name()}.penumbraAngle", degrees)

    def dropoff(self) -> float:
        """
        Returns the dropoff (falloff from centre to edge) of the spot light
        """
        return cmds.getAttr(f"{self.item.full_name()}.dropoff")

    def set_dropoff(self, value: float) -> None:
        """
        Sets the dropoff (falloff from centre to edge) of the spot light
        """
        cmds.setAttr(f"{self.item.full_name()}.dropoff", value)


def _is_light_classification(type_name: str) -> bool:
    """
    Returns True if the classification of the given node type contains
    the ``light`` token (e.g. ``"...:light:rendernode/arnold/light"``).
    """
    try:
        classifications = cmds.getClassification(type_name) or []
    except RuntimeError:
        return False

    for classification in classifications:
        for token in classification.split(":"):
            if token == "light":
                return True

    return False


def _names(nodes) -> list[str]:
    if not isinstance(nodes, (list, tuple)):
        nodes = [nodes]
    return [
        node.full_name() if isinstance(node, mref.ReferencedItem) else node
        for node in nodes
    ]
