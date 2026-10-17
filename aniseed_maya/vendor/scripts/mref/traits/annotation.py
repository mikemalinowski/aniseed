import mref
from maya import cmds
from maya.api import OpenMaya as om


class Annotation(mref.Trait):
    """
    Trait bound to any node with ``MFn.kAnnotation`` — annotation
    shapes (``annotationShape``), the text labels with an optional arrow
    pointing at another DAG object. Exposes the label text, the object
    the arrow points at (and retargeting it), the arrow display toggle,
    and the world-space point the arrow is aimed at.
    """

    # -- Sits above the generic Shape trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kAnnotation)

    def text(self) -> str:
        """
        Returns the annotation's label text
        """
        return cmds.getAttr(f"{self.item.full_name()}.text") or ""

    def set_text(self, text: str) -> None:
        """
        Sets the annotation's label text
        """
        cmds.setAttr(f"{self.item.full_name()}.text", text, type="string")

    def target(self) -> mref.ReferencedItem|None:
        """
        Returns the DAG node the annotation points at (the node whose
        ``worldMatrix`` feeds ``dagObjectMatrix[0]``), or None if it is
        not pointing at anything. ``cmds.annotate`` connects the target's
        shape when it has one, so this is often a shape node.
        """
        sources = cmds.listConnections(
            f"{self.item.full_name()}.dagObjectMatrix[0]",
            source=True,
            destination=False,
            shapes=True,
        ) or []
        if sources:
            return mref.get(sources[0])
        return None

    def set_target(self, node: "mref.ReferencedItem|str|None") -> None:
        """
        Points the annotation at the given DAG node by connecting its
        ``worldMatrix[0]`` into ``dagObjectMatrix[0]``. Passing None
        disconnects the current target.
        """
        destination = f"{self.item.full_name()}.dagObjectMatrix[0]"

        if node is None:
            for source in cmds.listConnections(destination, source=True, destination=False, plugs=True) or []:
                cmds.disconnectAttr(source, destination)
            return

        cmds.connectAttr(
            f"{mref.get(node).full_name()}.worldMatrix[0]",
            destination,
            force=True,
        )

    def target_position(self) -> list[float]|None:
        """
        Returns the world-space position ``[x, y, z]`` the arrow points
        at (the translation of the target's world matrix), or None if
        the annotation has no target.
        """
        if self.target() is None:
            return None
        matrix = cmds.getAttr(f"{self.item.full_name()}.dagObjectMatrix[0]")
        return list(matrix[12:15])

    def display_arrow(self) -> bool:
        """
        Returns True if the annotation draws its arrow to the target
        """
        return bool(cmds.getAttr(f"{self.item.full_name()}.displayArrow"))

    def set_display_arrow(self, state: bool) -> None:
        """
        Sets whether the annotation draws its arrow to the target
        """
        cmds.setAttr(f"{self.item.full_name()}.displayArrow", state)
