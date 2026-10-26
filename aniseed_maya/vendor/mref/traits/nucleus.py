import mref
from maya import cmds
from maya.api import OpenMaya as om


class Nucleus(mref.Trait):
    """
    Trait bound to any node with ``MFn.kNucleus`` — the Nucleus
    dynamics solver (a transform-derived node). Exposes the active and
    passive objects it solves, adding objects to it, gravity magnitude
    and direction, the simulation start frame, and enabling / disabling
    the solver.

    Note: the ``enable()`` method shadows the solver's ``enable``
    Maya attribute for property-style access; use
    ``item.attribute("enable")`` for the plug itself.
    """

    # -- Sits above the generic Transform trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kNucleus)

    def active_objects(self) -> mref.ReferenceList:
        """
        Returns the active objects (nCloth, nParticle, hair systems...)
        connected to this solver's ``inputActive`` array, in index order.
        """
        return self._objects_on("inputActive")

    def passive_objects(self) -> mref.ReferenceList:
        """
        Returns the passive colliders (nRigid) connected to this
        solver's ``inputPassive`` array, in index order.
        """
        return self._objects_on("inputPassive")

    def objects(self) -> mref.ReferenceList:
        """
        Returns every object solved by this nucleus — active objects
        followed by passive ones.
        """
        return mref.ReferenceList(self.active_objects() + self.passive_objects())

    def add_object(self, nucleus_object: "mref.ReferencedItem|str") -> None:
        """
        Connects the given Nucleus object (nCloth, nRigid, nParticle,
        hair system) to this solver, moving it off any solver it is
        currently connected to. Delegates to the object's
        ``set_solver`` method.
        """
        mref.get(nucleus_object).set_solver(self.item)

    def gravity(self) -> float:
        """
        Returns the gravity magnitude of this solver
        """
        return cmds.getAttr(f"{self.item.full_name()}.gravity")

    def set_gravity(self, value: float) -> None:
        """
        Sets the gravity magnitude of this solver
        """
        cmds.setAttr(f"{self.item.full_name()}.gravity", value)

    def gravity_direction(self) -> list[float]:
        """
        Returns the gravity direction of this solver as ``[x, y, z]``
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.gravityDirection")[0])

    def set_gravity_direction(self, direction: list[float]) -> None:
        """
        Sets the gravity direction of this solver from ``[x, y, z]``
        """
        cmds.setAttr(f"{self.item.full_name()}.gravityDirection", *direction)

    def start_frame(self) -> float:
        """
        Returns the frame at which this solver's simulation starts
        """
        return cmds.getAttr(f"{self.item.full_name()}.startFrame")

    def set_start_frame(self, frame: float) -> None:
        """
        Sets the frame at which this solver's simulation starts
        """
        cmds.setAttr(f"{self.item.full_name()}.startFrame", frame)

    def is_enabled(self) -> bool:
        """
        Returns True if this solver is enabled
        """
        return bool(cmds.getAttr(f"{self.item.full_name()}.enable"))

    def enable(self) -> None:
        """
        Enables this solver
        """
        cmds.setAttr(f"{self.item.full_name()}.enable", True)

    def disable(self) -> None:
        """
        Disables this solver, freezing every object it solves
        """
        cmds.setAttr(f"{self.item.full_name()}.enable", False)

    def _objects_on(self, attribute: str) -> mref.ReferenceList:
        """
        Returns the nodes connected into the given array attribute
        """
        node_name = self.item.full_name()
        results = mref.ReferenceList()

        for index in cmds.getAttr(f"{node_name}.{attribute}", multiIndices=True) or []:
            sources = cmds.listConnections(
                f"{node_name}.{attribute}[{index}]",
                source=True,
                destination=False,
                shapes=True,
            ) or []
            for source in sources:
                item = mref.get(source)
                if item not in results:
                    results.append(item)

        return results
