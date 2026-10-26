import mref
from maya import cmds
from maya.api import OpenMaya as om


class Wire(mref.Trait):
    """
    Trait bound to any node with ``MFn.kWire`` — the wire deformer.
    Exposes the influence wire curves and their base wires, adding
    wires, the per-wire dropoff distance and scale, and the deformer
    wide rotation, tension, crossing effect and local influence.

    Per-wire methods take ``wire`` as either the wire's index (its
    logical index in ``deformedWire[]``) or the wire curve itself
    (transform or shape).

    Input/output geometry, the envelope and the paintable per-component
    weights are provided by the generic ``GeometryFilter`` trait which is
    also bound to every wire deformer.
    """

    # -- Sits above the generic GeometryFilter trait
    priority = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kWire)

    def wires(self) -> mref.ReferenceList:
        """
        Returns the curve shapes acting as influence wires, ordered by
        wire index
        """
        return mref.ReferenceList(
            node for _, node in self._connected_wires("deformedWire")
        )

    def base_wires(self) -> mref.ReferenceList:
        """
        Returns the base wire curve shapes (the rest position of each
        influence wire), ordered by wire index
        """
        return mref.ReferenceList(
            node for _, node in self._connected_wires("baseWire")
        )

    def add_wire(self, curve: mref.ReferencedItem|str) -> None:
        """
        Adds the given curve as an additional influence wire. Maya
        creates a matching base wire for it.
        """
        cmds.wire(
            self.item.full_name(),
            edit=True,
            wire=mref.get(curve).full_name(),
        )

    def dropoff_distance(self, wire: int|mref.ReferencedItem|str = 0) -> float:
        """
        Returns the dropoff distance of the given wire — how far from
        the wire the deformation reaches
        """
        return cmds.getAttr(f"{self.item.full_name()}.dropoffDistance[{self._wire_index(wire)}]")

    def set_dropoff_distance(self, value: float, wire: int|mref.ReferencedItem|str = None) -> None:
        """
        Sets the dropoff distance of the given wire, or of every wire
        when ``wire`` is None
        """
        self._set_per_wire("dropoffDistance", value, wire)

    def wire_scale(self, wire: int|mref.ReferencedItem|str = 0) -> float:
        """
        Returns the scale of the given wire — how much scaling the wire
        curve scales the deformed geometry
        """
        return cmds.getAttr(f"{self.item.full_name()}.scale[{self._wire_index(wire)}]")

    def set_wire_scale(self, value: float, wire: int|mref.ReferencedItem|str = None) -> None:
        """
        Sets the scale of the given wire, or of every wire when ``wire``
        is None
        """
        self._set_per_wire("scale", value, wire)

    def wire_rotation(self) -> float:
        """
        Returns how much of the wires' twisting is applied to the
        deformed geometry, in the range 0 to 1
        """
        return cmds.getAttr(f"{self.item.full_name()}.rotation")

    def set_wire_rotation(self, value: float) -> None:
        """
        Sets how much of the wires' twisting is applied to the deformed
        geometry, in the range 0 to 1
        """
        cmds.setAttr(f"{self.item.full_name()}.rotation", value)

    def tension(self) -> float:
        """
        Returns the tension of the wires where multiple wires meet
        """
        return cmds.getAttr(f"{self.item.full_name()}.tension")

    def set_tension(self, value: float) -> None:
        """
        Sets the tension of the wires where multiple wires meet
        """
        cmds.setAttr(f"{self.item.full_name()}.tension", value)

    def crossing_effect(self) -> float:
        """
        Returns the crossing effect — how deformations combine where
        wires cross (0 adds them, 1 averages them)
        """
        return cmds.getAttr(f"{self.item.full_name()}.crossingEffect")

    def set_crossing_effect(self, value: float) -> None:
        """
        Sets the crossing effect — how deformations combine where wires
        cross (0 adds them, 1 averages them)
        """
        cmds.setAttr(f"{self.item.full_name()}.crossingEffect", value)

    def local_influence(self) -> float:
        """
        Returns the local influence — how much wires' deformations are
        localised where they cross
        """
        return cmds.getAttr(f"{self.item.full_name()}.localInfluence")

    def set_local_influence(self, value: float) -> None:
        """
        Sets the local influence — how much wires' deformations are
        localised where they cross
        """
        cmds.setAttr(f"{self.item.full_name()}.localInfluence", value)

    def _connected_wires(self, attribute_name: str) -> list[tuple]:
        """
        Returns (logical_index, ReferencedItem) pairs for every element
        of the given wire array attribute which has a curve connected
        """
        plug = self._dependency_node.findPlug(attribute_name, False)
        results = []

        for index in plug.getExistingArrayAttributeIndices():
            source = plug.elementByLogicalIndex(index).source()
            if not source.isNull:
                results.append((index, mref.get(source.node())))

        return results

    def _wire_index(self, wire) -> int:
        """
        Resolves a wire index or wire curve (transform or shape) to the
        wire's logical index
        """
        if isinstance(wire, int):
            return wire

        wire = mref.get(wire)
        candidates = [wire]
        if hasattr(wire, "shapes"):
            candidates.extend(wire.shapes())

        for index, node in self._connected_wires("deformedWire"):
            if node in candidates:
                return index

        raise ValueError(f"{wire} is not a wire of {self.item.name()}")

    def _set_per_wire(self, attribute_name: str, value: float, wire) -> None:
        """
        Sets a per-wire array attribute for one wire, or all wires when
        ``wire`` is None
        """
        if wire is None:
            indices = [index for index, _ in self._connected_wires("deformedWire")]
        else:
            indices = [self._wire_index(wire)]

        for index in indices:
            cmds.setAttr(f"{self.item.full_name()}.{attribute_name}[{index}]", value)
