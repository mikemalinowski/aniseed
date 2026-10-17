import mref
from maya import cmds
from maya.api import OpenMaya as om


class AnimLayer(mref.Trait):
    """
    Trait bound to any node with ``MFn.kAnimLayer`` — animation layers,
    including the root ``BaseAnimation`` layer. Exposes the layer's
    weight, mute / solo / lock / override state, its place in the layer
    hierarchy, and the attributes which are animated on it.

    ``animLayer`` derives from ``objectSet`` (and reports ``MFn.kSet``),
    so the generic ``ObjectSet`` trait is bound as well. Lock state is
    exposed as ``is_layer_locked`` / ``set_layer_locked`` so it does not
    shadow the node-locking ``lock`` / ``is_locked`` methods of
    ``DependencyNode``.
    """

    # -- Sits above the generic ObjectSet trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kAnimLayer)

    def weight(self) -> float:
        """
        Returns the blend weight of this layer (0.0 - 1.0)
        """
        return cmds.animLayer(self.item.full_name(), query=True, weight=True)

    def set_weight(self, value: float) -> None:
        """
        Sets the blend weight of this layer
        """
        cmds.animLayer(self.item.full_name(), edit=True, weight=value)

    def is_muted(self) -> bool:
        """
        Returns True if this layer is muted
        """
        return bool(cmds.animLayer(self.item.full_name(), query=True, mute=True))

    def set_muted(self, state: bool) -> None:
        """
        Mutes or unmutes this layer
        """
        cmds.animLayer(self.item.full_name(), edit=True, mute=state)

    def is_solo(self) -> bool:
        """
        Returns True if this layer is soloed
        """
        return bool(cmds.animLayer(self.item.full_name(), query=True, solo=True))

    def set_solo(self, state: bool) -> None:
        """
        Solos or un-solos this layer
        """
        cmds.animLayer(self.item.full_name(), edit=True, solo=state)

    def is_layer_locked(self) -> bool:
        """
        Returns True if this layer is locked against keying. This is the
        animation-layer lock, not Maya's node lock (see ``is_locked``).
        """
        return bool(cmds.animLayer(self.item.full_name(), query=True, lock=True))

    def set_layer_locked(self, state: bool) -> None:
        """
        Locks or unlocks this layer against keying
        """
        cmds.animLayer(self.item.full_name(), edit=True, lock=state)

    def is_override(self) -> bool:
        """
        Returns True if this layer is in override mode, or False if it
        is additive.
        """
        return bool(cmds.animLayer(self.item.full_name(), query=True, override=True))

    def set_override(self, state: bool) -> None:
        """
        Sets this layer to override (True) or additive (False) mode
        """
        cmds.animLayer(self.item.full_name(), edit=True, override=state)

    def is_base_layer(self) -> bool:
        """
        Returns True if this is the root animation layer
        (``BaseAnimation``) which all other layers are parented beneath.
        """
        root = cmds.animLayer(query=True, root=True)
        return bool(root) and mref.get(root) == self.item

    def parent_layer(self) -> mref.ReferencedItem|None:
        """
        Returns the layer this layer is parented under, or None for the
        base layer.
        """
        parent = cmds.animLayer(self.item.full_name(), query=True, parent=True)
        if not parent:
            return None
        return mref.get(parent)

    def child_layers(self) -> mref.ReferenceList:
        """
        Returns the layers parented directly beneath this layer
        """
        return mref.ReferenceList(
            mref.get(layer)
            for layer in cmds.animLayer(self.item.full_name(), query=True, children=True) or []
        )

    def layered_attributes(self) -> mref.ReferenceList:
        """
        Returns the attributes which are animated on (members of) this
        layer, as attribute ReferencedItems.
        """
        return mref.ReferenceList(
            mref.get(attribute)
            for attribute in cmds.animLayer(self.item.full_name(), query=True, attribute=True) or []
        )

    def add_layered_attributes(self, attributes: list|mref.ReferencedItem|str) -> None:
        """
        Adds the given attribute(s) to this layer so they can be keyed on
        it. Attributes may be given as ``node.attr`` strings or attribute
        ReferencedItems.
        """
        cmds.animLayer(self.item.full_name(), edit=True, attribute=_attribute_names(attributes))

    def remove_layered_attributes(self, attributes: list|mref.ReferencedItem|str) -> None:
        """
        Removes the given attribute(s) from this layer, deleting any
        animation they had on it.
        """
        cmds.animLayer(self.item.full_name(), edit=True, removeAttribute=_attribute_names(attributes))


def _attribute_names(attributes) -> list[str]:
    """
    Resolves an attribute, or list of attributes, given as
    ReferencedItems or strings into ``node.attr`` strings.
    """
    if not isinstance(attributes, (list, tuple)):
        attributes = [attributes]
    return [
        attribute.full_name() if isinstance(attribute, mref.ReferencedItem) else attribute
        for attribute in attributes
    ]
