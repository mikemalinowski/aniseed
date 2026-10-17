import mref
from maya import cmds
from maya.api import OpenMaya as om


class Locator(mref.Trait):
    """
    Trait bound to any node with ``MFn.kLocator`` — locator shape nodes
    (``spaceLocator`` and other locator-derived shapes). Exposes the
    shape-level local position and scale offsets, plus the evaluated
    world position of the locator.
    """

    # -- Sits above the generic Shape trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kLocator)

    def local_position(self) -> list[float]:
        """
        Returns the locator's shape-level position offset (``localPosition``)
        as ``[x, y, z]``, relative to its transform.
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.localPosition")[0])

    def set_local_position(self, position: list[float]) -> None:
        """
        Sets the locator's shape-level position offset (``localPosition``)
        from ``[x, y, z]``.
        """
        cmds.setAttr(f"{self.item.full_name()}.localPosition", *position)

    def local_scale(self) -> list[float]:
        """
        Returns the locator's shape-level display scale (``localScale``)
        as ``[x, y, z]``.
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.localScale")[0])

    def set_local_scale(self, scale: list[float]) -> None:
        """
        Sets the locator's shape-level display scale (``localScale``)
        from ``[x, y, z]``. A single float may be given for a uniform scale.
        """
        if isinstance(scale, (int, float)):
            scale = [scale, scale, scale]
        cmds.setAttr(f"{self.item.full_name()}.localScale", *scale)

    def world_position(self) -> list[float]:
        """
        Returns the evaluated world space position of the locator as
        ``[x, y, z]`` — the transform's world position combined with the
        shape's ``localPosition`` offset.
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.worldPosition[0]")[0])
