import mref
from maya import cmds
from maya.api import OpenMaya as om


def _next_solver_index(nucleus_name: str) -> int:
    """
    Returns the next free logical index across the nucleus solver's
    input / output arrays, so that an object's ``inputActive[n]`` and
    ``outputObjects[n]`` slots line up.
    """
    used = []
    for attribute in ("inputActive", "inputActiveStart", "inputPassive", "inputPassiveStart", "outputObjects"):
        used.extend(cmds.getAttr(f"{nucleus_name}.{attribute}", multiIndices=True) or [])
    return (max(used) + 1) if used else 0


class NucleusObject(mref.Trait):
    """
    Trait bound to any Nucleus-simulated shape — nodes with
    ``MFn.kNBase`` (``nCloth``, ``nRigid``, ``nParticle``) and hair
    systems (``MFn.kHairSystem``, which is not ``kNBase``-derived but is
    solved by nucleus in the same way). Exposes the nucleus solver the
    object belongs to (and moving it to another solver), whether it is a
    passive collider, enabling / disabling simulation, the input and
    output meshes of cloth and rigid objects, and the follicles feeding
    a hair system.
    """

    # -- Sits above the generic Shape trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and (
            pointer.hasFn(om.MFn.kNBase) or pointer.hasFn(om.MFn.kHairSystem)
        )

    def solver(self) -> mref.ReferencedItem|None:
        """
        Returns the nucleus solver node this object is connected to, or
        None if it is not connected to one.
        """
        solvers = cmds.listConnections(
            f"{self.item.full_name()}.currentState",
            source=False,
            destination=True,
            type="nucleus",
        ) or []
        if solvers:
            return mref.get(solvers[0])
        return None

    def is_passive(self) -> bool:
        """
        Returns True if this object is connected to its solver as a
        passive collider (``inputPassive``) — typically an ``nRigid``.
        """
        destinations = cmds.listConnections(
            f"{self.item.full_name()}.currentState",
            source=False,
            destination=True,
            plugs=True,
            type="nucleus",
        ) or []
        return any(".inputPassive[" in destination for destination in destinations)

    def set_solver(self, nucleus: "mref.ReferencedItem|str") -> None:
        """
        Connects this object to the given nucleus solver, disconnecting
        it from its current solver first. Passive objects (``nRigid``)
        are connected to the solver's passive inputs; everything else is
        connected as an active object, including the solver's
        ``outputObjects`` feeding back into ``nextState``.
        """
        nucleus_name = mref.get(nucleus).full_name()
        node_name = self.item.full_name()
        passive = self.is_passive() or self._pointer.hasFn(om.MFn.kNRigid)

        self._disconnect_solver()

        index = _next_solver_index(nucleus_name)
        prefix = "inputPassive" if passive else "inputActive"

        cmds.connectAttr(f"{node_name}.currentState", f"{nucleus_name}.{prefix}[{index}]", force=True)
        cmds.connectAttr(f"{node_name}.startState", f"{nucleus_name}.{prefix}Start[{index}]", force=True)
        if not passive:
            cmds.connectAttr(f"{nucleus_name}.outputObjects[{index}]", f"{node_name}.nextState", force=True)

        if cmds.attributeQuery("startFrame", node=node_name, exists=True):
            cmds.connectAttr(f"{nucleus_name}.startFrame", f"{node_name}.startFrame", force=True)

    def is_enabled(self) -> bool:
        """
        Returns True if this object is being simulated. For nBase
        objects this is ``isDynamic``; for hair systems it is a
        ``simulationMethod`` other than Off.
        """
        if self._is_hair_system():
            return cmds.getAttr(f"{self.item.full_name()}.simulationMethod") != 0
        return bool(cmds.getAttr(f"{self.item.full_name()}.isDynamic"))

    def enable(self) -> None:
        """
        Enables simulation of this object. For hair systems this sets
        ``simulationMethod`` to All Follicles (3) if it is currently Off;
        any other non-off method is left untouched.
        """
        if self._is_hair_system():
            if not self.is_enabled():
                cmds.setAttr(f"{self.item.full_name()}.simulationMethod", 3)
            return
        cmds.setAttr(f"{self.item.full_name()}.isDynamic", True)

    def disable(self) -> None:
        """
        Disables simulation of this object (``isDynamic`` off, or
        ``simulationMethod`` Off for hair systems).
        """
        if self._is_hair_system():
            cmds.setAttr(f"{self.item.full_name()}.simulationMethod", 0)
            return
        cmds.setAttr(f"{self.item.full_name()}.isDynamic", False)

    def input_mesh(self) -> mref.ReferencedItem|None:
        """
        Returns the mesh shape feeding this object's ``inputMesh`` (the
        source geometry of an ``nCloth`` or ``nRigid``), or None if there
        is none or the object type has no mesh input.
        """
        return self._connected_shape("inputMesh", source=True)

    def output_mesh(self) -> mref.ReferencedItem|None:
        """
        Returns the mesh shape driven by this object's ``outputMesh``
        (the simulated result of an ``nCloth``), or None if there is none
        or the object type has no mesh output.
        """
        return self._connected_shape("outputMesh", source=False)

    def hair_follicles(self) -> mref.ReferenceList:
        """
        Returns the follicle shapes feeding this hair system's
        ``inputHair`` array, in index order. Empty for non-hair objects.
        """
        results = mref.ReferenceList()
        if not self._is_hair_system():
            return results

        node_name = self.item.full_name()
        for index in cmds.getAttr(f"{node_name}.inputHair", multiIndices=True) or []:
            sources = cmds.listConnections(
                f"{node_name}.inputHair[{index}]",
                source=True,
                destination=False,
                shapes=True,
            ) or []
            for source in sources:
                results.append(mref.get(source))
        return results

    def _is_hair_system(self) -> bool:
        return self._pointer.hasFn(om.MFn.kHairSystem)

    def _connected_shape(self, attribute: str, source: bool) -> mref.ReferencedItem|None:
        """
        Returns the first shape connected to the given attribute in the
        given direction, or None.
        """
        node_name = self.item.full_name()
        if not cmds.attributeQuery(attribute, node=node_name, exists=True):
            return None

        connections = cmds.listConnections(
            f"{node_name}.{attribute}",
            source=source,
            destination=not source,
            shapes=True,
        ) or []
        if connections:
            return mref.get(connections[0])
        return None

    def _disconnect_solver(self) -> None:
        """
        Breaks every connection between this object and any nucleus
        solver (state outputs, nextState and startFrame inputs).
        """
        node_name = self.item.full_name()
        connections = cmds.listConnections(
            node_name,
            connections=True,
            plugs=True,
            type="nucleus",
        ) or []

        for own_plug, other_plug in zip(connections[::2], connections[1::2]):
            if cmds.isConnected(own_plug, other_plug):
                cmds.disconnectAttr(own_plug, other_plug)
            elif cmds.isConnected(other_plug, own_plug):
                cmds.disconnectAttr(other_plug, own_plug)
