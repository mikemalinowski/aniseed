import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- interpType enum on orient / parent constraints, in index order
_INTERPOLATION_TYPES = ["noFlip", "average", "shortest", "longest", "cache"]

# -- worldUpType enum on aim-style constraints, in index order, using
# -- the string values accepted by cmds.aimConstraint(worldUpType=...)
_WORLD_UP_TYPES = ["scene", "object", "objectrotation", "vector", "none"]

# -- Channels a constraint can drive, keyed by the name used in
# -- skipped_axes(), mapped to the constraint's output attribute prefix
_OUTPUT_CHANNELS = {
    "translate": "constraintTranslate",
    "rotate": "constraintRotate",
    "scale": "constraintScale",
}


class Constraint(mref.Trait):
    """
    Trait bound to any node with ``MFn.kConstraint`` — point, orient,
    parent, scale, aim, pole-vector, and any other constraint type
    derived from Maya's constraint base. Exposes the constrained node
    (:meth:`driven`), the nodes driving the constraint
    (:meth:`drivers`), and the per-target weight attributes
    (:meth:`weight_attributes`).

    Also provides target management (add / remove / per-target
    weight), offsets, interpolation type, skipped axes, rest position,
    aim/up vector and world-up settings for aim-style constraints, and
    a simple bake-out helper. Getters for settings a given constraint
    type does not have (e.g. :meth:`aim_vector` on a point constraint)
    return None.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kConstraint)

    def driven(self) -> mref.ReferencedItem|None:
        """
        Returns the node being driven by the constraint
        """
        potential_attributes = [
            "constraintTranslateX",
            "constraintRotateX",
            "constraintScaleX",
        ]
        for attribute_name in potential_attributes:
            if not self._dependency_node.hasAttribute(attribute_name):
                continue

            plug = self._dependency_node.findPlug(attribute_name, False)
            destinations = plug.destinations()

            for destination in destinations:
                return mref.get(destination.node())

        return None

    def drivers(self) -> mref.ReferenceList:
        """
        Returns the list of driver nodes feeding this constraint's
        target inputs. The constraint's own target hierarchy
        connections (``targetParentMatrix``) are excluded — only true
        driver transforms are returned.
        """
        target_plug = self._dependency_node.findPlug("target", False)
        drivers = mref.ReferenceList()

        for i in range(target_plug.numElements()):
            element = target_plug.elementByPhysicalIndex(i)

            for child_index in range(element.numChildren()):
                child = element.child(child_index)

                # -- Skip targetParentMatrix; it's the parent of the
                # -- target transform (metadata) not a driver. Use
                # -- useLongNames=True so the suffix check matches
                # -- the long attribute name rather than the short
                # -- alias (``tpm``).
                if child.partialName(useLongNames=True).endswith("targetParentMatrix"):
                    continue

                source = child.source()

                if source.isNull:
                    continue

                referenced_node = mref.get(source.node())

                if referenced_node == self.item:
                    continue
                if referenced_node not in drivers:
                    drivers.append(referenced_node)

        return drivers

    def weight_attributes(self) -> mref.ReferenceList:
        """
        Returns the per-target weight attributes for the constraint.
        The result is a ``ReferenceList`` of attribute ReferencedItems,
        one entry per target.
        """
        constraint_type = cmds.nodeType(self.item.full_name())

        constraint_func = getattr(cmds, constraint_type)
        attribute_names = constraint_func(self.item.full_name(), query=True, weightAliasList=True)

        return mref.ReferenceList(
            mref.get(f"{self.item.full_name()}.{attribute_name}")
            for attribute_name in attribute_names
        )

    # ------------------------------------------------------------------
    # Target management
    # ------------------------------------------------------------------

    def add_target(
        self,
        driver: mref.ReferencedItem|str,
        weight: float = 1.0,
        maintain_offset: bool = False,
    ) -> mref.ReferencedItem:
        """
        Adds the given node as a new target of this constraint and
        returns its weight attribute. Uses the constraint's own command
        (``cmds.pointConstraint`` etc.), which appends to the existing
        constraint of that type on the driven node. Existing settings
        such as aim vectors are preserved.

        :param weight: The weight of the new target.
        :param maintain_offset: Forwarded as ``maintainOffset``; only
            passed when True since not every constraint command (e.g.
            ``poleVectorConstraint``) supports the flag.
        """
        driver = mref.get(driver)
        kwargs = dict(weight=weight)
        if maintain_offset:
            kwargs["maintainOffset"] = True

        self._command()(driver.full_name(), self._driven_name(), **kwargs)
        return self._weight_attribute(driver)

    def remove_target(self, driver: mref.ReferencedItem|str) -> None:
        """
        Removes the given node as a target of this constraint. Note
        that Maya deletes the constraint node itself when its last
        target is removed.
        """
        driver = mref.get(driver)
        self._command()(
            driver.full_name(),
            self._driven_name(),
            edit=True,
            remove=True,
        )

    def target_weight(self, driver: mref.ReferencedItem|str) -> float:
        """
        Returns the weight of the given target. Raises ValueError if
        the node is not a target of this constraint.
        """
        return self._weight_attribute(mref.get(driver)).get()

    def set_target_weight(self, driver: mref.ReferencedItem|str, weight: float) -> None:
        """
        Sets the weight of the given target. Raises ValueError if the
        node is not a target of this constraint.
        """
        self._weight_attribute(mref.get(driver)).set(weight)

    # ------------------------------------------------------------------
    # Offsets
    # ------------------------------------------------------------------

    def offset_values(self) -> list[float]|None:
        """
        Returns the constraint-level ``offset`` as ``[x, y, z]`` (point,
        orient, aim and scale constraints — this is what
        ``maintainOffset`` writes to). Returns None for constraint types
        without one; parent constraints store offsets per target, see
        :meth:`target_offset`.

        Named ``offset_values`` rather than ``offset`` so that
        ``constraint.offset`` keeps resolving to the Maya attribute.
        """
        if not self._dependency_node.hasAttribute("offset"):
            return None
        return list(cmds.getAttr(f"{self.item.full_name()}.offset")[0])

    def set_offset_values(self, values: list[float]) -> None:
        """
        Sets the constraint-level ``offset`` from ``[x, y, z]``. Raises
        RuntimeError on constraint types without one.
        """
        if not self._dependency_node.hasAttribute("offset"):
            raise RuntimeError(f"{self.item.name()} has no offset attribute")
        cmds.setAttr(f"{self.item.full_name()}.offset", *values)

    def target_offset(self, driver: mref.ReferencedItem|str) -> dict|None:
        """
        Returns the per-target offset of a parent constraint as
        ``{"translate": [x, y, z], "rotate": [x, y, z]}``. Returns None
        for constraint types without per-target offsets. Raises
        ValueError if the node is not a target of this constraint.
        """
        if not self._dependency_node.hasAttribute("targetOffsetTranslate"):
            return None

        index = self._target_index(mref.get(driver))
        base = f"{self.item.full_name()}.target[{index}]"
        return {
            "translate": list(cmds.getAttr(f"{base}.targetOffsetTranslate")[0]),
            "rotate": list(cmds.getAttr(f"{base}.targetOffsetRotate")[0]),
        }

    # ------------------------------------------------------------------
    # Behaviour settings
    # ------------------------------------------------------------------

    def interpolation_type(self) -> str|None:
        """
        Returns the rotation interpolation type of an orient or parent
        constraint — one of ``"noFlip"``, ``"average"``, ``"shortest"``,
        ``"longest"`` or ``"cache"``. Returns None for constraint types
        without one.
        """
        if not self._dependency_node.hasAttribute("interpType"):
            return None
        return _INTERPOLATION_TYPES[cmds.getAttr(f"{self.item.full_name()}.interpType")]

    def set_interpolation_type(self, interpolation_type: str) -> None:
        """
        Sets the rotation interpolation type of an orient or parent
        constraint (see :meth:`interpolation_type` for the names).
        """
        if interpolation_type not in _INTERPOLATION_TYPES:
            raise ValueError(
                f"Unknown interpolation type {interpolation_type!r}; "
                f"expected one of {_INTERPOLATION_TYPES}"
            )
        if not self._dependency_node.hasAttribute("interpType"):
            raise RuntimeError(f"{self.item.name()} has no interpolation type")
        cmds.setAttr(
            f"{self.item.full_name()}.interpType",
            _INTERPOLATION_TYPES.index(interpolation_type),
        )

    def skipped_axes(self) -> dict[str, list[str]]:
        """
        Returns, for each channel this constraint type can drive
        (``"translate"``, ``"rotate"``, ``"scale"``), the axes that are
        NOT connected to the driven node — e.g. ``{"translate": ["y"]}``
        for a point constraint created with ``skip="y"``. Maya does not
        store skip flags, so this is derived from the output
        connections.
        """
        result = {}
        for channel, prefix in _OUTPUT_CHANNELS.items():
            if not self._dependency_node.hasAttribute(f"{prefix}X"):
                continue

            skipped = []
            for axis in "xyz":
                plug = self._dependency_node.findPlug(f"{prefix}{axis.upper()}", False)
                if not plug.destinations():
                    skipped.append(axis)
            result[channel] = skipped
        return result

    def rest_position(self) -> dict|None:
        """
        Returns the rest position settings as a dictionary with an
        ``"enabled"`` bool plus whichever of ``"translate"``,
        ``"rotate"`` and ``"scale"`` this constraint type has, each as
        ``[x, y, z]``. Returns None for constraint types without a rest
        position (e.g. pole vector constraints).
        """
        if not self._dependency_node.hasAttribute("enableRestPosition"):
            return None

        name = self.item.full_name()
        result = {"enabled": cmds.getAttr(f"{name}.enableRestPosition")}
        for key, attribute in self._rest_attributes().items():
            result[key] = list(cmds.getAttr(f"{name}.{attribute}")[0])
        return result

    def set_rest_position(
        self,
        translate: list[float]|None = None,
        rotate: list[float]|None = None,
        scale: list[float]|None = None,
        enabled: bool|None = None,
    ) -> None:
        """
        Sets any of the rest translate / rotate / scale values and
        whether the rest position is enabled. Arguments left as None
        are not changed. Raises RuntimeError if a value is given that
        this constraint type has no rest attribute for.
        """
        name = self.item.full_name()
        rest_attributes = self._rest_attributes()

        for key, values in (("translate", translate), ("rotate", rotate), ("scale", scale)):
            if values is None:
                continue
            if key not in rest_attributes:
                raise RuntimeError(f"{self.item.name()} has no rest {key}")
            cmds.setAttr(f"{name}.{rest_attributes[key]}", *values)

        if enabled is not None:
            if not self._dependency_node.hasAttribute("enableRestPosition"):
                raise RuntimeError(f"{self.item.name()} has no rest position")
            cmds.setAttr(f"{name}.enableRestPosition", enabled)

    # ------------------------------------------------------------------
    # Aim-style constraints (aim, tangent, normal)
    # ------------------------------------------------------------------

    def aim_vector(self) -> list[float]|None:
        """
        Returns the aim vector as ``[x, y, z]``, or None if this
        constraint type has no aim vector.
        """
        return self._get_vector("aimVector")

    def set_aim_vector(self, vector: list[float]) -> None:
        """
        Sets the aim vector from ``[x, y, z]``.
        """
        self._set_vector("aimVector", vector)

    def up_vector(self) -> list[float]|None:
        """
        Returns the up vector as ``[x, y, z]``, or None if this
        constraint type has no up vector.
        """
        return self._get_vector("upVector")

    def set_up_vector(self, vector: list[float]) -> None:
        """
        Sets the up vector from ``[x, y, z]``.
        """
        self._set_vector("upVector", vector)

    def world_up_type(self) -> str|None:
        """
        Returns the world up type as the string used by
        ``cmds.aimConstraint`` — ``"scene"``, ``"object"``,
        ``"objectrotation"``, ``"vector"`` or ``"none"``. Returns None
        if this constraint type has no world up type.
        """
        if not self._dependency_node.hasAttribute("worldUpType"):
            return None
        return _WORLD_UP_TYPES[cmds.getAttr(f"{self.item.full_name()}.worldUpType")]

    def set_world_up_type(
        self,
        world_up_type: str,
        world_up_object: mref.ReferencedItem|str|None = None,
        world_up_vector: list[float]|None = None,
    ) -> None:
        """
        Sets the world up type (see :meth:`world_up_type` for names)
        via the constraint's own command, so the world up object's
        matrix is connected for you.

        :param world_up_object: Required by Maya for the ``"object"``
            and ``"objectrotation"`` types.
        :param world_up_vector: Optional ``[x, y, z]`` world up vector
            (used by ``"vector"`` and ``"objectrotation"``).
        """
        if world_up_type not in _WORLD_UP_TYPES:
            raise ValueError(
                f"Unknown world up type {world_up_type!r}; expected one of {_WORLD_UP_TYPES}"
            )
        if not self._dependency_node.hasAttribute("worldUpType"):
            raise RuntimeError(f"{self.item.name()} has no world up type")

        kwargs = dict(edit=True, worldUpType=world_up_type)
        if world_up_object is not None:
            kwargs["worldUpObject"] = mref.get(world_up_object).full_name()
        if world_up_vector is not None:
            kwargs["worldUpVector"] = list(world_up_vector)

        self._command()(self.item.full_name(), **kwargs)

    def world_up_object(self) -> mref.ReferencedItem|None:
        """
        Returns the node whose matrix feeds the world up of an
        aim-style constraint, or None if there is none.
        """
        if not self._dependency_node.hasAttribute("worldUpMatrix"):
            return None
        source = self._dependency_node.findPlug("worldUpMatrix", False).source()
        if source.isNull:
            return None
        return mref.get(source.node())

    # ------------------------------------------------------------------
    # Baking
    # ------------------------------------------------------------------

    def bake(
        self,
        start: float|None = None,
        end: float|None = None,
        delete_constraint: bool = True,
    ) -> None:
        """
        Bakes the constrained channels of the driven node to keys over
        the given frame range (defaults to the playback range) and, by
        default, deletes this constraint afterwards. Only the channels
        this constraint actually drives are baked.
        """
        if start is None:
            start = cmds.playbackOptions(query=True, minTime=True)
        if end is None:
            end = cmds.playbackOptions(query=True, maxTime=True)

        driven_attributes = []
        for prefix in _OUTPUT_CHANNELS.values():
            for axis in "XYZ":
                if not self._dependency_node.hasAttribute(f"{prefix}{axis}"):
                    continue
                plug = self._dependency_node.findPlug(f"{prefix}{axis}", False)
                for destination in plug.destinations():
                    driven_attributes.append(
                        mref.get(destination).full_name()
                    )

        if not driven_attributes:
            return

        cmds.bakeResults(
            driven_attributes,
            time=(start, end),
            simulation=True,
        )

        if delete_constraint:
            cmds.delete(self.item.full_name())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _command(self):
        """
        Returns the cmds function matching this constraint's node type
        (e.g. ``cmds.pointConstraint``).
        """
        return getattr(cmds, cmds.nodeType(self.item.full_name()))

    def _driven_name(self) -> str:
        """
        Returns the full name of the driven node, raising RuntimeError
        if the constraint is not driving anything.
        """
        driven = self.driven()
        if driven is None:
            raise RuntimeError(f"{self.item.name()} is not driving any node")
        return driven.full_name()

    def _target_index(self, driver: mref.ReferencedItem) -> int:
        """
        Returns the logical ``target`` index fed by the given driver,
        ignoring ``targetParentMatrix`` connections. Raises ValueError
        if the node is not a target.
        """
        target_plug = self._dependency_node.findPlug("target", False)

        for i in range(target_plug.numElements()):
            element = target_plug.elementByPhysicalIndex(i)

            for child_index in range(element.numChildren()):
                child = element.child(child_index)
                if child.partialName(useLongNames=True).endswith("targetParentMatrix"):
                    continue

                source = child.source()
                if source.isNull:
                    continue

                if mref.get(source.node()) == driver:
                    return element.logicalIndex()

        raise ValueError(f"{driver.name()} is not a target of {self.item.name()}")

    def _weight_attribute(self, driver: mref.ReferencedItem) -> mref.ReferencedItem:
        """
        Returns the user-facing weight attribute (e.g. ``driverW0``)
        for the given driver, falling back to ``target[n].targetWeight``
        when no alias attribute feeds it.
        """
        index = self._target_index(driver)
        weight_plug = (
            self._dependency_node.findPlug("target", False)
            .elementByLogicalIndex(index)
            .child(self._dependency_node.attribute("targetWeight"))
        )
        source = weight_plug.source()
        return mref.get(source if not source.isNull else weight_plug)

    def _rest_attributes(self) -> dict[str, str]:
        """
        Returns the rest attributes present on this constraint, keyed
        by ``"translate"`` / ``"rotate"`` / ``"scale"``.
        """
        return {
            key: attribute
            for key, attribute in (
                ("translate", "restTranslate"),
                ("rotate", "restRotate"),
                ("scale", "restScale"),
            )
            if self._dependency_node.hasAttribute(attribute)
        }

    def _get_vector(self, attribute_name: str) -> list[float]|None:
        """
        Returns a double3 attribute as a list, or None if absent.
        """
        if not self._dependency_node.hasAttribute(attribute_name):
            return None
        return list(cmds.getAttr(f"{self.item.full_name()}.{attribute_name}")[0])

    def _set_vector(self, attribute_name: str, vector: list[float]) -> None:
        """
        Sets a double3 attribute from a list, raising RuntimeError if
        the attribute is absent.
        """
        if not self._dependency_node.hasAttribute(attribute_name):
            raise RuntimeError(f"{self.item.name()} has no {attribute_name}")
        cmds.setAttr(f"{self.item.full_name()}.{attribute_name}", *vector)