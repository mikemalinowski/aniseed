import mref
import typing
from maya import cmds
from maya.api import OpenMaya as om


# -- Maya attribute type → Python type. Used by Attribute.python_type().
# -- Lives at module level so adding new mappings is just a dict entry.
# -- Types not in this dict (e.g. ``message``, unrecognised future types)
# -- return None from python_type().
_ATTRIBUTE_TYPE_TO_PYTHON_TYPE = {
    # Floats
    "double":       float,
    "float":        float,
    "doubleLinear": float,
    "doubleAngle":  float,
    "floatLinear":  float,
    "floatAngle":   float,
    "time":         float,

    # Integers
    "long":         int,
    "short":        int,
    "byte":         int,
    "char":         int,
    "enum":         int,

    # Booleans
    "bool":         bool,

    # Strings
    "string":       str,

    # Compound numeric types
    "double2":      list,
    "double3":      list,
    "float2":       list,
    "float3":       list,
    "long2":        list,
    "long3":        list,
    "short2":       list,
    "short3":       list,

    # Array data types
    "doubleArray":  list,
    "floatArray":   list,
    "Int32Array":   list,
    "vectorArray":  list,
    "pointArray":   list,
    "stringArray":  list,

    # Matrices
    "matrix":       list,
    "fltMatrix":    list,
}


class Attribute(mref.Trait):
    """
    Trait bound to any ``om.MPlug`` — every attribute on every node in
    the scene. Exposes name / path resolution, value get/set,
    connect/disconnect, type queries, and Python-type mapping.

    Addressing forms:
      * ``name(include_node=False)`` — bare attribute name
        (``translateX``).
      * ``name(include_node=True)`` — short form including the owning
        node's short name (``cube.translateX``). Display-friendly but
        ambiguous on DAG nodes with duplicate short names.
      * ``full_name()`` / ``path()`` — fully qualified DAG path of the
        owning node joined with the partial attribute name
        (``|root|cube.translateX``). Safe for handing to ``cmds`` in
        any scene. Both methods return the same string; ``path()`` is
        an alias kept for backwards compat.

    The owning node and the attribute's data type are both resolved
    lazily on first access (``node()`` and ``get_type()``) so
    constructing an Attribute is cheap.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._m_plug = self._pointer

        # -- The plug's partial name doesn't change after construction,
        # -- so cache it once. Saves an MPlug call on every name() /
        # -- full_name() / path() invocation.
        self._partial_name = self._pointer.partialName(useLongNames=True)

        # -- These are resolved lazily on first access to avoid the
        # -- per-Attribute cost of a recursive mref.get and a
        # -- cmds.getAttr at construction time. Many Attribute
        # -- instances are never asked for their node or type.
        self._node_cache = None
        self._attribute_type_cache = None

    @classmethod
    def can_bind(cls, pointer: om.MObject | om.MPlug) -> bool:
        """
        Returns True if the given pointer is an MPlug.
        """
        return isinstance(pointer, om.MPlug)

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
            return f"{self.node().name()}.{self._partial_name}"
        else:
            return self._partial_name

    def full_name(self) -> str:
        """
        Returns the fully qualified path of the attribute — the owning
        node's DAG path joined with the attribute's partial name. This
        is the safe, unambiguous form to hand to ``cmds`` in scenes
        that may contain duplicate short names.
        """
        return f"{self.node().full_name()}.{self._partial_name}"

    def path(self) -> str:
        """
        Alias for :meth:`full_name`. Both return the same fully
        qualified attribute path.
        """
        return self.full_name()

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

    def connect_next(
        self,
        attribute: mref.ReferencedItem | str,
        force: bool = False,
        **kwargs,
    ) -> None:
        """
        Connect this attribute to the next free element of the given
        multi-attribute. The target's existing logical indices are
        queried; the new connection goes to ``max(existing) + 1``, or
        ``[0]`` if the multi is currently empty.

        :param attribute: A multi-attribute (or a string addressing one).
            The target must be a multi (array) attribute — non-multi
            attributes will fail at the ``cmds.connectAttr`` step with
            a Maya error referencing the malformed indexed plug.
        :param force: Forwarded to ``cmds.connectAttr``.
        """
        attribute = mref.get(attribute)

        existing_indices = attribute.get(multiIndices=True) or []
        next_index = max(existing_indices) + 1 if existing_indices else 0

        cmds.connectAttr(
            self.path(),
            f"{attribute.path()}[{next_index}]",
            force=force,
            **kwargs,
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
        Returns a list of inputs feeding into this attribute.

        :param node_type: If given, only include inputs whose owning
            node matches this Maya node type (e.g. ``"transform"``,
            ``"multiplyDivide"``). ``None`` (default) returns all
            inputs.
        :param skip_converters: When True (default), unitConversion
            nodes are transparently skipped via Maya's
            ``skipConversionNodes`` flag — no Python-side recursion
            needed.
        """
        kwargs = dict(
            source=True,
            destination=False,
            plugs=True,
            skipConversionNodes=skip_converters,
        )
        if node_type:
            kwargs["type"] = node_type

        return [
            mref.get(attribute)
            for attribute in cmds.listConnections(self.path(), **kwargs) or []
        ]

    def outputs(self, node_type=None, skip_converters=True) -> list[mref.ReferencedItem]:
        """
        Returns a list of outputs being driven by this attribute.

        :param node_type: If given, only include outputs whose owning
            node matches this Maya node type (e.g. ``"transform"``,
            ``"multiplyDivide"``). ``None`` (default) returns all
            outputs.
        :param skip_converters: When True (default), unitConversion
            nodes are transparently skipped via Maya's
            ``skipConversionNodes`` flag — no Python-side recursion
            needed.
        """
        kwargs = dict(
            source=False,
            destination=True,
            plugs=True,
            skipConversionNodes=skip_converters,
        )
        if node_type:
            kwargs["type"] = node_type

        return [
            mref.get(attribute)
            for attribute in cmds.listConnections(self.path(), **kwargs) or []
        ]

    def python_type(self):
        """
        Returns the Python type that most closely represents the value
        of this attribute. Returns ``None`` for attribute types that
        don't have a meaningful Python value (e.g. ``message``) or for
        any attribute type not in the mapping.

        Uses the cached :meth:`get_type` rather than re-querying Maya
        on every call.
        """
        return _ATTRIBUTE_TYPE_TO_PYTHON_TYPE.get(self.get_type())

    def __repr__(self) -> str:
        """
        This string representation of this type
        """
        return self.name(include_node=True)
