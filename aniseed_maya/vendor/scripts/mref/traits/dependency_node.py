import mref
import typing
from maya import cmds
from maya.api import OpenMaya as om


class DependencyNode(mref.Trait):
    """
    Trait bound to every node in the scene — ``MFn.kDependencyNode`` is
    the root of Maya's node-type hierarchy, so every node has this trait.
    Provides the foundational name, attribute, lock, and connection API.

    Priority ``-1`` (lowest), so higher-priority traits like ``DagNode``
    (priority ``0``) override this trait's methods when they apply. In
    particular, ``DagNode.full_name()`` shadows this trait's
    ``full_name()`` for any node that lives in the DAG hierarchy.
    """
    priority = -1

    def __init__(self, *args, **kwargs):
        super(DependencyNode, self).__init__(*args, **kwargs)

        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kDependencyNode):
            return True
        return False

    def __getattr__(self, name: str) -> typing.Any:
        result = self.attribute(name)
        if result is None:
            raise AttributeError(f"{self} does not have attribute {name}")
        return result

    def name(self) -> str:
        """
        Returns the name of the node which is referenced
        """
        return self._dependency_node.name().split("|")[-1]

    def full_name(self) -> str:
        """
        Returns the full name of the node which is referenced
        """
        return self.name()

    def rename(self, new_name: str) -> None:
        """
        Renames this node to the given name
        """
        cmds.rename(
            self.item.full_name(),
            new_name,
        )

    def attribute(self, attribute_name: str) -> mref.ReferencedItem|None:
        """
        Gets the attribute on this node by name. Returns None if the
        node does not have an attribute with that name.

        Note: this differs from accessing the attribute via property
        syntax (``node.translateX``), which raises ``AttributeError``
        for unknown names. Use this method when you want to test for
        an attribute's existence without exception handling; use the
        property form when an unknown name is a programming error
        you'd like surfaced loudly.
        """
        attribute_address = f"{self.item.full_name()}.{attribute_name}"
        if not cmds.objExists(attribute_address):
            return None
        return mref.get(attribute_address)

    def attr(self, attribute_name: str) -> mref.ReferencedItem|None:
        """
        Gets the attribute on this node by the attribute name
        """
        return self.attribute(attribute_name)

    def attributes(self, **kwargs) -> list[mref.ReferencedItem]:
        """
        Returns a list of all attributes on this node
        """
        results = mref.ReferenceList()

        for attribute in cmds.listAttr(self.item.full_name(), **kwargs) or []:

            if attribute.startswith("."):
                attribute = attribute[1:]

            attribute_address = f"{self.item.full_name()}.{attribute}"
            try:
                results.append(mref.get(attribute_address))
            except Exception as exc:
                print(f"mref: failed to wrap attribute {attribute_address}: {exc}")
        return results

    def add_attribute(self, name: str, value: typing.Any, attribute_type: str, **kwargs) -> mref.ReferencedItem:
        """
        Adds an attribute to this node with the given name and type. If
        ``value`` is not None, the new attribute is also initialised to
        that value; ``None`` means "create the attribute but leave the
        default value in place".

        Note: ``attribute_type="compound"`` is not supported by this
        method — Maya requires a different code path (``numberOfChildren``
        followed by per-child ``addAttr`` calls) which this function
        does not implement. Calling with a compound type raises
        ``KeyError`` from the constants lookup. Use ``cmds.addAttr``
        directly to create compound attributes.
        """
        kwargs[mref.constants.attribute_types[attribute_type]] = attribute_type
        cmds.addAttr(
            self.item.full_name(),
            shortName=name,
            **kwargs
        )
        attribute = mref.get(f"{self.item.full_name()}.{name}")

        if value is not None:
            attribute.set(value)

        return attribute

    def has_attribute(self, attribute_name: str) -> bool:
        """
        Returns True if this node has an attribute with the given name,
        False otherwise.
        """
        return self.attribute(attribute_name) is not None

    def node_type(self) -> str:
        """
        Returns the type of this node
        """
        return cmds.nodeType(self.item.full_name())

    def inputs(self, shapes: bool = True, **kwargs) -> list[mref.ReferencedItem]:
        """
        Returns a list of inputs coming into this node.

        :param shapes: If True (default), shape nodes connected to this
            node are also included. Set to False to match
            ``cmds.listConnections``' default behaviour.
        """
        return [
            mref.get(node)
            for node in cmds.listConnections(
                self.item.full_name(),
                source=True,
                destination=False,
                shapes=shapes,
                **kwargs,
            ) or []
        ]

    def outputs(self, shapes: bool = True, **kwargs) -> list[mref.ReferencedItem]:
        """
        Returns a list of outputs coming out of this node.

        :param shapes: If True (default), shape nodes connected to this
            node are also included. Set to False to match
            ``cmds.listConnections``' default behaviour.
        """
        return [
            mref.get(node)
            for node in cmds.listConnections(
                self.item.full_name(),
                source=False,
                destination=True,
                shapes=shapes,
                **kwargs,
            ) or []
        ]

    def delete(self) -> None:
        """
        This will remove the node from the scene
        """
        if cmds.objExists(self.item.full_name()):
            cmds.delete(self.item.full_name())

    def lock(self) -> None:
        """
        This will lock the node
        """
        cmds.lockNode(self.item.full_name(), lock=True)

    def unlock(self) -> None:
        """
        This will unlock the node
        """
        cmds.lockNode(self.item.full_name(), lock=False)

    def is_locked(self) -> bool:
        """
        This will return whether or not the node is locked
        """
        return cmds.lockNode(self.item.full_name(), query=True)[0]

    def set_lock_state(self, state: bool) -> None:
        """
        This will set the nodes lock state to the given state
        """
        cmds.lockNode(self.item.full_name(), lock=state)

    def lock_attributes(self, attribute_names: list[str]) -> None:
        """
        Lock the named attributes on this node. Each name is resolved
        against this node; raises AttributeError if any name is unknown.
        """
        self._set_attribute_locks(attribute_names, True)

    def unlock_attributes(self, attribute_names: list[str]) -> None:
        """
        Unlock the named attributes on this node. Each name is resolved
        against this node; raises AttributeError if any name is unknown.
        """
        self._set_attribute_locks(attribute_names, False)

    def _set_attribute_locks(self, attribute_names: list[str], state: bool) -> None:
        for name in attribute_names:
            attr = self.attribute(name)
            if attr is None:
                raise AttributeError(
                    f"{self.item.full_name()} does not have attribute {name}"
                )
            attr.set(lock=state)

    def lock_transform_attributes(self) -> None:
        """
        Locks the nine scalar transform channels on this node — translateX/Y/Z,
        rotateX/Y/Z, scaleX/Y/Z. Does not lock visibility, nor the parent
        compound translate/rotate/scale attributes themselves. Has no unlock
        counterpart; call ``unlock_attributes`` with explicit channel names
        to reverse.
        """
        for type_ in ["t", "r", "s"]:
            for axis in ["x", "y", "z"]:
                cmds.setAttr(f"{self.item.full_name()}.{type_}{axis}", lock=True)
