import mref
from maya import cmds
from maya.api import OpenMaya as om


class ObjectSet(mref.Trait):
    """
    Trait bound to any node with ``MFn.kSet`` — object sets, shading
    engines, deformer sets and any other set-derived node. Exposes
    membership queries and edits.

    Members which are components (``pCube1.vtx[0:3]``) cannot be cast
    to a ReferencedItem, so they are returned as plain strings within
    the ``ReferenceList``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set = om.MFnSet(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kSet)

    def members(self, flatten: bool = False) -> mref.ReferenceList:
        """
        Returns the members of this set. If ``flatten`` is True then
        component ranges are expanded into individual components.
        """
        members = cmds.sets(self.item.full_name(), query=True) or []

        if flatten:
            members = cmds.ls(members, flatten=True, long=True) or []
        else:
            members = cmds.ls(members, long=True) or []

        return mref.ReferenceList(
            mref.get(member)
            for member in members
        )

    def add_members(self, members: list|mref.ReferencedItem|str) -> None:
        """
        Adds the given node(s) or component(s) to this set
        """
        cmds.sets(
            self._names(members),
            edit=True,
            forceElement=self.item.full_name(),
        )

    def remove_members(self, members: list|mref.ReferencedItem|str) -> None:
        """
        Removes the given node(s) or component(s) from this set
        """
        cmds.sets(
            self._names(members),
            edit=True,
            remove=self.item.full_name(),
        )

    def is_member(self, member: mref.ReferencedItem|str) -> bool:
        """
        Returns True if the given node or component is in this set
        """
        return cmds.sets(
            self._names(member),
            isMember=self.item.full_name(),
        )

    def clear(self) -> None:
        """
        Removes every member from this set
        """
        cmds.sets(clear=self.item.full_name())

    @staticmethod
    def _names(members) -> list[str]:
        if not isinstance(members, list):
            members = [members]
        return [
            member.full_name() if isinstance(member, mref.ReferencedItem) else member
            for member in members
        ]
