import traceback

import mref
import typing
from maya import cmds
from maya.api import OpenMaya as om


class DependencyNode(mref.Trait):
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
        try:
            return self.attribute(name)
        except:
            raise AttributeError(f"{self} does not have attribute {name}")

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
            self.full_name(),
            new_name,
        )

    def attribute(self, attribute_name: str) -> mref.ReferencedItem|None:
        """
        Gets the attribute on this node by the attribute name
        """
        attribute_address = f"{self.name()}.{attribute_name}"
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
        for attribute in cmds.listAttr(self.item.name(), **kwargs) or []:
            if attribute.startswith("."):
                attribute = attribute[1:]

            attribute_address = f"{self.name()}.{attribute}"
            try:
                mref.get(attribute_address)
            except:
                import traceback
                traceback.print_exc()
        return mref.ReferenceList()

    def add_attribute(self, name: str, value: typing.Any, attribute_type: str, **kwargs) -> mref.ReferencedItem:
        """
        Adds an attribute to this node with the given name, value and type.
        """
        kwargs[mref.constants.attribute_types[attribute_type]] = attribute_type
        cmds.addAttr(
            self.full_name(),
            shortName=name,
            **kwargs
        )
        attribute = mref.get(f"{self.full_name()}.{name}")

        try:
            attribute.set(value)
        except:
            pass

        return attribute

    def has_attribute(self, attribute_name: str) -> bool:
        return self.attribute(attribute_name) is not None

    def node_type(self) -> str:
        """
        Returns the type of this node
        """
        return cmds.nodeType(self.item.full_name())

    def inputs(self, **kwargs) -> list[mref.ReferencedItem]:
        """
        Returns a list of inputs coming into this node
        """
        return [
            mref.get(node)
            for node in cmds.listConnections(self.full_name(), source=True, destination=False, shapes=True, **kwargs) or []
        ]

    def outputs(self, **kwargs) -> list[mref.ReferencedItem]:
        """
        Returns a list of outputs coming out of this node
        """
        return [
            mref.get(node)
            for node in cmds.listConnections(self.full_name(), source=False, destination=True, shapes=True, **kwargs) or []
        ]

    def delete(self):
        """
        This will remove the node from the scene
        """
        if cmds.objExists(self.full_name()):
            cmds.delete(self.full_name())

    def lock(self):
        """
        This will lock the node
        """
        cmds.lockNode(self.full_name(), lock=True)

    def unlcok(self):
        """
        This will unlock the node
        """
        cmds.lockNode(self.full_name(), lock=False)

    def is_locked(self):
        """
        This will return whether or not the node is locked
        """
        return cmds.lockNode(self.full_name(), lock=True, query=True)[0]

    def set_lock_state(self, state: bool):
        """
        This will set the nodes lock state to the given state
        """
        cmds.lockNode(self.full_name(), lock=state)
