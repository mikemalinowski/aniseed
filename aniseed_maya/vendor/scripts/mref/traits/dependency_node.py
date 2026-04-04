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
        return [
            mref.get(f"{self.name()}.{attribute}")
            for attribute in cmds.listAttr(self.item.name(), **kwargs)
        ]

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
        attribute.set(value)
        return attribute

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
            for node in cmds.listConnections(self.full_name(), source=True, destination=False, shapes=True, **kwargs)
        ]

    def outputs(self, **kwargs) -> list[mref.ReferencedItem]:
        """
        Returns a list of outputs coming out of this node
        """
        return [
            mref.get(node)
            for node in cmds.listConnections(self.full_name(), source=False, destination=True, shapes=True, **kwargs)
        ]
