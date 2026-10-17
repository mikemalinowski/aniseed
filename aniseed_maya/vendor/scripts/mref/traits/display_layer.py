import mref
from maya import cmds
from maya.api import OpenMaya as om


class DisplayLayer(mref.Trait):
    """
    Trait bound to any node with ``MFn.kDisplayLayer`` — display layers.
    Exposes layer membership along with the layer's visibility, display
    type (normal / template / reference), hide-on-playback flag and
    colour index.

    Display layers are not ``kSet`` nodes, so the ``ObjectSet`` trait
    never binds alongside this one and the ``members`` /
    ``add_members`` / ``remove_members`` names are free to use here.
    """

    # -- Index -> label for the displayType enum
    display_types = ["normal", "template", "reference"]

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kDisplayLayer)

    def members(self) -> mref.ReferenceList:
        """
        Returns the nodes which belong to this display layer
        """
        members = cmds.editDisplayLayerMembers(
            self.item.full_name(),
            query=True,
            fullNames=True,
        ) or []

        return mref.ReferenceList(mref.get(member) for member in members)

    def add_members(self, members: "list|mref.ReferencedItem|str") -> None:
        """
        Adds the given node(s) to this display layer. A node can only be
        in one display layer, so they are removed from any other layer.
        """
        cmds.editDisplayLayerMembers(
            self.item.full_name(),
            *_names(members),
            noRecurse=True,
        )

    def remove_members(self, members: "list|mref.ReferencedItem|str") -> None:
        """
        Removes the given node(s) from this display layer by moving them
        back to the ``defaultLayer``. Nodes that are not members of this
        layer are left untouched.
        """
        fn = om.MFnDisplayLayer(self._pointer)
        to_remove = []

        for name in _names(members):
            selection = om.MSelectionList()
            selection.add(name)
            if fn.contains(selection.getDagPath(0)):
                to_remove.append(name)

        if to_remove:
            cmds.editDisplayLayerMembers("defaultLayer", *to_remove, noRecurse=True)

    def is_visible(self) -> bool:
        """
        Returns True if the layer's visibility (V) toggle is on
        """
        return cmds.getAttr(f"{self.item.full_name()}.visibility")

    def set_visible(self, state: bool) -> None:
        """
        Sets the layer's visibility (V) toggle
        """
        cmds.setAttr(f"{self.item.full_name()}.visibility", state)

    def display_type(self) -> str:
        """
        Returns the layer's display type: ``"normal"``, ``"template"``
        or ``"reference"``.
        """
        return self.display_types[cmds.getAttr(f"{self.item.full_name()}.displayType")]

    def set_display_type(self, display_type: str) -> None:
        """
        Sets the layer's display type: ``"normal"``, ``"template"`` or
        ``"reference"``.
        """
        if display_type not in self.display_types:
            raise ValueError(
                f"Unknown display type {display_type!r}; expected one of {self.display_types}"
            )
        cmds.setAttr(
            f"{self.item.full_name()}.displayType",
            self.display_types.index(display_type),
        )

    def hide_on_playback(self) -> bool:
        """
        Returns True if the layer's members are hidden during playback
        (the layer editor's P toggle being off)
        """
        return cmds.getAttr(f"{self.item.full_name()}.hideOnPlayback")

    def set_hide_on_playback(self, state: bool) -> None:
        """
        Sets whether the layer's members are hidden during playback
        """
        cmds.setAttr(f"{self.item.full_name()}.hideOnPlayback", state)

    def colour_index(self) -> int:
        """
        Returns the layer's colour index (``0`` means no colour)
        """
        return cmds.getAttr(f"{self.item.full_name()}.color")

    def set_colour_index(self, index: int) -> None:
        """
        Sets the layer's colour index (``0`` to ``31``; ``0`` means no
        colour). RGB layer colours are switched off so the index is used.
        """
        node = self.item.full_name()
        cmds.setAttr(f"{node}.overrideRGBColors", False)
        cmds.setAttr(f"{node}.color", index)


def _names(nodes) -> list[str]:
    if not isinstance(nodes, (list, tuple)):
        nodes = [nodes]
    return [
        node.full_name() if isinstance(node, mref.ReferencedItem) else node
        for node in nodes
    ]
