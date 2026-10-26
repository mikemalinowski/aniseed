import mref
from maya import cmds
from maya.api import OpenMaya as om


def _locator_shape(node: "mref.ReferencedItem|str") -> str:
    """
    Resolves a locator transform or locator shape to the shape's full
    name, as distance dimensions read ``worldPosition`` from the shape.
    """
    node = mref.get(node)
    if node.pointer().hasFn(om.MFn.kLocator):
        return node.full_name()

    for shape in cmds.listRelatives(node.full_name(), shapes=True, fullPath=True, type="locator") or []:
        return shape

    raise RuntimeError(f"{node.full_name()} is not a locator")


class DistanceDimension(mref.Trait):
    """
    Trait bound to any node with ``MFn.kDistance`` — distance dimension
    shapes (``distanceDimShape``) which measure the distance between two
    points, usually driven by two locators. Exposes the measured
    distance, the start / end locators (and rewiring them), and the
    start / end point positions.
    """

    # -- Sits above the generic Shape trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kDistance)

    def distance(self) -> float:
        """
        Returns the measured distance between the start and end points
        """
        return cmds.getAttr(f"{self.item.full_name()}.distance")

    def start_locator(self) -> mref.ReferencedItem|None:
        """
        Returns the locator shape driving the start point, or None
        """
        return self._point_source("startPoint")

    def end_locator(self) -> mref.ReferencedItem|None:
        """
        Returns the locator shape driving the end point, or None
        """
        return self._point_source("endPoint")

    def set_start_locator(self, locator: "mref.ReferencedItem|str") -> None:
        """
        Drives the start point from the given locator (transform or
        shape) by connecting its ``worldPosition[0]``.
        """
        self._connect_point("startPoint", locator)

    def set_end_locator(self, locator: "mref.ReferencedItem|str") -> None:
        """
        Drives the end point from the given locator (transform or shape)
        by connecting its ``worldPosition[0]``.
        """
        self._connect_point("endPoint", locator)

    def start_position(self) -> list[float]:
        """
        Returns the world-space start point ``[x, y, z]``
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.startPoint")[0])

    def end_position(self) -> list[float]:
        """
        Returns the world-space end point ``[x, y, z]``
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.endPoint")[0])

    def _point_source(self, attribute: str) -> mref.ReferencedItem|None:
        sources = cmds.listConnections(
            f"{self.item.full_name()}.{attribute}",
            source=True,
            destination=False,
            shapes=True,
        ) or []
        if sources:
            return mref.get(sources[0])
        return None

    def _connect_point(self, attribute: str, locator: "mref.ReferencedItem|str") -> None:
        cmds.connectAttr(
            f"{_locator_shape(locator)}.worldPosition[0]",
            f"{self.item.full_name()}.{attribute}",
            force=True,
        )
