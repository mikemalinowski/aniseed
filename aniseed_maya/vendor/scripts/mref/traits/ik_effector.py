import mref
from maya import cmds
from maya.api import OpenMaya as om


class IkEffector(mref.Trait):
    """
    Trait bound to any node with ``MFn.kIkEffector`` — the end effector
    which sits at the tip of an IK chain. Exposes the IK handle(s) the
    effector serves and the joints at either end of the chain.

    ``IkHandle.effector()`` provides the reverse lookup, from handle to
    effector.
    """

    # -- Sits above the generic Transform trait
    priority = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kIkEffector)

    def ik_handle(self) -> mref.ReferencedItem|None:
        """
        Returns the IK handle this effector serves, or None if the
        effector is not connected to a handle.
        """
        handles = self.ik_handles()
        if handles:
            return handles[0]
        return None

    def ik_handles(self) -> mref.ReferenceList:
        """
        Returns every IK handle this effector serves. ``handlePath`` is
        a multi attribute, so an effector can feed more than one handle.
        """
        handles = mref.ReferenceList()

        # -- Each handlePath element feeds a handle's endEffector
        plug = self._dependency_node.findPlug("handlePath", False)
        for element_index in range(plug.numElements()):
            for destination in plug.elementByPhysicalIndex(element_index).destinations():
                node = destination.node()
                if not node.hasFn(om.MFn.kIkHandle):
                    continue

                handle = mref.get(node)
                if handle not in handles:
                    handles.append(handle)

        return handles

    def end_joint(self) -> mref.ReferencedItem|None:
        """
        Returns the joint the effector sits on (the last joint of the
        chain), or None if the effector is not driven by a joint.
        """
        # -- The effector's translation is driven by the end joint
        sources = cmds.listConnections(
            f"{self.item.full_name()}.translateX",
            source=True,
            destination=False,
            type="joint",
        ) or []
        if sources:
            return mref.get(sources[0])
        return None

    def start_joint(self) -> mref.ReferencedItem|None:
        """
        Returns the first joint of the chain driven by this effector's
        IK handle, or None if the effector has no handle.
        """
        handle = self.ik_handle()
        if handle is None:
            return None
        return handle.start_joint()
