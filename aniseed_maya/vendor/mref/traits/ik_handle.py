import mref
from maya import cmds
from maya.api import OpenMaya as om


class IkHandle(mref.Trait):
    """
    Trait bound to any node with ``MFn.kIkHandle`` — IK handles (RP, SC,
    spline and spring solvers). Exposes the start / end joints, the end
    effector, the joint chain being driven, the solver type, and the
    pole vector and twist controls.

    The OpenMaya 2.0 API has no ``MFnIkHandle``, so this trait works
    through ``cmds.ikHandle`` and the handle's plugs.
    """

    # -- Sits above the generic Transform trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kIkHandle)

    def start_joint(self) -> mref.ReferencedItem|None:
        """
        Returns the first joint of the chain driven by this handle, or
        None if the handle is not connected to a chain.
        """
        result = cmds.ikHandle(self.item.full_name(), query=True, startJoint=True)
        if result:
            return mref.get(result)
        return None

    def end_joint(self) -> mref.ReferencedItem|None:
        """
        Returns the last joint of the chain driven by this handle (the
        joint the end effector sits on), or None if there is no effector.
        """
        effector = self.effector()
        if not effector:
            return None

        # -- The effector's translation is driven by the end joint
        sources = cmds.listConnections(
            f"{effector.full_name()}.translateX",
            source=True,
            destination=False,
            type="joint",
        ) or []
        if sources:
            return mref.get(sources[0])
        return None

    def effector(self) -> mref.ReferencedItem|None:
        """
        Returns the end effector node of this handle, or None if the
        handle has no effector.
        """
        result = cmds.ikHandle(self.item.full_name(), query=True, endEffector=True)
        if result:
            return mref.get(result)
        return None

    def joint_chain(self) -> mref.ReferenceList:
        """
        Returns the joints driven by this handle, ordered from the start
        joint to the end joint (inclusive of both).
        """
        joints = cmds.ikHandle(self.item.full_name(), query=True, jointList=True) or []
        chain = mref.ReferenceList(mref.get(joint) for joint in joints)

        # -- cmds.ikHandle -jointList omits the end joint
        end = self.end_joint()
        if end is not None and end not in chain:
            chain.append(end)
        return chain

    def solver_type(self) -> str|None:
        """
        Returns the node type of the solver driving this handle, such as
        ``"ikRPsolver"``, ``"ikSCsolver"`` or ``"ikSplineSolver"``, or None
        if no solver is connected.
        """
        solvers = cmds.listConnections(
            f"{self.item.full_name()}.ikSolver",
            source=True,
            destination=False,
        ) or []
        if solvers:
            return cmds.nodeType(solvers[0])
        return None

    def set_solver_type(self, solver: str) -> None:
        """
        Switches this handle to the given solver type, e.g. ``"ikRPsolver"``
        or ``"ikSCsolver"``. The solver node is created if it does not yet
        exist in the scene.
        """
        cmds.ikHandle(self.item.full_name(), edit=True, solver=solver)

    def pole_vector(self) -> list[float]:
        """
        Returns the pole vector as ``[x, y, z]``. Only meaningful for
        rotate-plane style solvers.
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.poleVector")[0])

    def set_pole_vector(self, vector: list[float]) -> None:
        """
        Sets the pole vector from ``[x, y, z]``. Only meaningful for
        rotate-plane style solvers.
        """
        cmds.setAttr(f"{self.item.full_name()}.poleVector", *vector)

    def add_pole_vector_constraint(self, target: mref.ReferencedItem|str) -> mref.ReferencedItem:
        """
        Creates a pole vector constraint driving this handle from the given
        target transform and returns the constraint node.
        """
        target = mref.get(target)
        constraint = cmds.poleVectorConstraint(target.full_name(), self.item.full_name())[0]
        return mref.get(constraint)

    def twist(self) -> float:
        """
        Returns the twist value of the handle in degrees.
        """
        return cmds.getAttr(f"{self.item.full_name()}.twist")

    def set_twist(self, value: float) -> None:
        """
        Sets the twist value of the handle in degrees.
        """
        cmds.setAttr(f"{self.item.full_name()}.twist", value)
