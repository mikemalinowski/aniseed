import mref
import typing
from maya import cmds
from maya.api import OpenMaya as om


class Attribute(mref.Trait):
    """
    This trait will bind and represent attributes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._m_plug = self._pointer

        # -- These are resolved lazily on first access to avoid the
        # -- per-Attribute cost of a recursive mref.get and a
        # -- cmds.getAttr at construction time. Many Attribute
        # -- instances are never asked for their node or type.
        self._node_cache = None
        self._attribute_type_cache = None

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
        belongs to. Resolved lazily on first access.
        """
        if self._node_cache is None:
            self._node_cache = mref.get(self._pointer.node())
        return self._node_cache

    def name(self, include_node: bool = False) -> str:
        """
        Returns the short-form name of the attribute.

        :param include_node: If True, the returned string is prefixed
            with the owning node's short name — e.g. ``cube.translateX``
            for a DAG node, or ``multiplyDivide1.outputX`` for a
            dependency node. For an unambiguous address that includes
            the full DAG path (``|foo|bar|cube.translateX``), use
            :meth:`full_name` or :meth:`path` instead — those are the
            safe form to hand to ``cmds`` in scenes that may contain
            duplicate short names.
        """
        if include_node:
            return f"{self.node().name()}.{self._m_plug.partialName(useLongNames=True)}"
        else:
            return self._m_plug.partialName(useLongNames=True)

    def full_name(self) -> str:
        """
        Returns the name of the attribute.

        :param include_node: If True, will return the fully qualified name of the attribute.
        """
        return f"{self.node().full_name()}.{self._m_plug.partialName(useLongNames=True)}"

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
        attribute_type = self.get_type()
        if attribute_type in mref.constants.complex_attribute_types and "type" not in kwargs:
            kwargs["type"] = attribute_type

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
        Returns the data type of this attribute. Cached after the first
        query — the underlying attribute's declared type does not
        change at runtime.
        """
        if self._attribute_type_cache is None:
            self._attribute_type_cache = cmds.getAttr(
                self.path(),
                type=True,
            )
        return self._attribute_type_cache

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

    def disconnect(self, attribute: mref.ReferencedItem | str | None = None) -> None:
        """
        Disconnect this attribute from the given attribute. If no
        attribute is given, every connection to and from this attribute
        is disconnected.
        """
        if attribute is None:
            attributes = self.connections()
        else:
            attributes = [mref.get(attribute)]

        for other in attributes:
            if not other:
                continue
            cmds.disconnectAttr(
                self.path(),
                other.path(),
            )

    def connections(self) -> list[mref.ReferencedItem]:
        """
        This will return a list of connected plugs
        """
        return self.outputs() + self.inputs()

    def inputs(self, node_type=None, skip_converters=True) -> list[mref.ReferencedItem]:
        """
        Returns a list of inputs feeding into this attribute. Unit
        conversion nodes are transparently skipped when
        ``skip_converters`` is True (the default) via Maya's
        ``skipConversionNodes`` flag — no Python-side recursion needed.
        """
        return [
            mref.get(attribute)
            for attribute in cmds.listConnections(
                self.path(),
                source=True,
                destination=False,
                plugs=True,
                skipConversionNodes=skip_converters,
            ) or []
        ]

    def outputs(self, node_type=None, skip_converters=True) -> list[mref.ReferencedItem]:
        """
        Returns a list of outputs being driven by this attribute. Unit
        conversion nodes are transparently skipped when
        ``skip_converters`` is True (the default) via Maya's
        ``skipConversionNodes`` flag — no Python-side recursion needed.
        """
        return [
            mref.get(attribute)
            for attribute in cmds.listConnections(
                self.path(),
                source=False,
                destination=True,
                plugs=True,
                skipConversionNodes=skip_converters,
            ) or []
        ]

    def type(self):
        """
        Returns the type of the attribute value.
        """
        return self.get(type=True)

    def python_type(self):
        """
        Returns the python type that most represents this attribute value.
        :return:
        """
        attribute_type = self.get(type=True)

        if attribute_type in ["doubleLinear", "float", "doubleAngle", "double"]:
            return float

        if attribute_type in ["int", "enum"]:
            return int

        if attribute_type in ["bool"]:
            return bool

        if attribute_type in ["double3", "float3"]:
            return list

        if attribute_type in ["string"]:
            return str

        return None

    def __repr__(self) -> str:
        """
        This string representation of this type
        """
        return self.name(include_node=True)
