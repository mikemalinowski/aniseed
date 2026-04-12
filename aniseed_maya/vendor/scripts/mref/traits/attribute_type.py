import mref
import typing
from maya import cmds
from maya.api import OpenMaya as om


class Attribute(mref.Trait):
    """
    This trait will bind and represent attributes.
    """

    def __init__(self, *args, **kwargs):
        super(Attribute, self).__init__(*args, **kwargs)

        self._node = mref.get(self._pointer.node())
        self._m_plug = self._pointer
        self._attribute_type = cmds.getAttr(self.name(include_node=True), type=True)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MPlug):
            return True
        return False

    def node(self) -> mref.ReferencedItem:
        """
        This will return the mref.ReferencedItem object which this attribute
        belongs to.
        """
        return self._node

    def name(self, include_node: bool = False) -> str:
        """
        Returns the name of the attribute.

        :param include_node: If True, will return the fully qualified name of the attribute.
        """
        if include_node:
            return f"{self.node().name()}.{self._m_plug.partialName(useLongNames=True)}"
        else:
            return self._m_plug.partialName(useLongNames=True)

    def path(self) -> str:
        """
        This will return the hierarchical path of the attribute (i.e, the objects full name
        prefixing the attribute).
        """
        return f"{self.node().full_name()}.{self._m_plug.partialName(useLongNames=True)}"

    def set(self, *args, **kwargs) -> None:
        """
        This will set the value of the attribute. If the type is not declared
        then the type will attempted to be resolved automatically using the value
        type.
        """
        if self._attribute_type in mref.constants.complex_attribute_types and "type" not in kwargs:
            kwargs["type"] = self._attribute_type

        cmds.setAttr(
            self.path(),
            *args,
            **kwargs
        )

    def get(self, **kwargs) -> typing.Any:
        """
        This will return the attribute value. The value type is determined by
        the attribute type.
        """
        return cmds.getAttr(
            self.path(),
            **kwargs
        )

    def get_type(self) -> str:
        """
        Returns the data type of this attribute
        """
        return self._attribute_type

    def connect(self, attribute: mref.ReferencedItem|str, force: bool = False, **kwargs) -> None:
        """
        This will connect this attribute to the given attribute - making this attribute
        drive the value of the other attribute.
        """
        attribute = mref.get(attribute)
        cmds.connectAttr(
            self.path(),
            attribute.path(),
            force=force,
            **kwargs
        )

    def connect_next(self, attribute: mref.ReferencedItem|str, force: bool = False, **kwargs) -> None:

        existing_plugs = attribute.get(multiIndices=True) or []
        next_index = max(existing_plugs) + 1 if existing_plugs else 0
        cmds.connectAttr(
            self.path(),
            f"{attribute.path()}[{next_index}]",
            force=force,
            **kwargs
        )

    def disconnect(self, attribute: mref.ReferencedItem|str = None) -> None:
        """
        This will disconnect this attribute from the given attribute. If no other attribute
        has been given then all connections to and from this attribute will be disconnected.
        """
        if attribute:
            attributes = mref.get(attribute)

        else:
            attributes = self.connections()

        for attribute in attributes:
            if not attribute:
                continue

            cmds.disconnectAttr(
                self.path(),
                attribute.path(),
            )

    def connections(self) -> list[mref.ReferencedItem]:
        """
        This will return a list of connected plugs
        """
        return self.outputs() + self.inputs()

    def inputs(self, node_type=None) -> list[mref.ReferencedItem]:
        """
        This will return a list of inputs coming into the node
        """
        return [
            mref.get(attribute)
            for attribute in
            cmds.listConnections(self.path(), source=True, destination=False, plugs=True) or []
        ]

    def outputs(self, node_type=None) -> list[mref.ReferencedItem]:
        """
        This will return a list of outputs coming from the node
        """
        return [
            mref.get(attribute)
            for attribute in
            cmds.listConnections(self.path(), source=False, destination=True, plugs=True) or []
        ]

    def __repr__(self) -> str:
        """
        This string representation of this type
        """
        return self.name(include_node=True)
