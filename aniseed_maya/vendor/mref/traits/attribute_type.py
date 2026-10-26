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
    connect/disconnect, type queries, and Python-type mapping, plus
    definition queries (default, min/max, enum names, dynamic),
    keyable / channel box / lock / hidden state, nice name and alias,
    array / compound navigation, and deletion of dynamic attributes.

    Editing an attribute's definition (range, enum names, hidden, nice
    name) is only possible on dynamic attributes; those setters raise
    RuntimeError on static (node-type defined) attributes.

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
        try:
            cmds.connectAttr(
                self.path(),
                attribute.path(),
                force=force,
                **kwargs
            )
        except:
            print(f"Could not connect {self} to {attribute}")

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

    def animation(self) -> mref.ReferencedItem|None:
        """
        This will return any animation curve node that is DIRECTLY connected to
        this attribute.
        """
        for driving_attribute in self.inputs():
            if "animCurve" in driving_attribute.node().node_type():
                return driving_attribute.node()
        return None

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

    # ------------------------------------------------------------------
    # Definition queries (default / range / enum / dynamic)
    # ------------------------------------------------------------------

    def is_dynamic(self) -> bool:
        """
        Returns True if this is a dynamic (user-added) attribute rather
        than one defined by the node type.
        """
        return om.MFnAttribute(self._pointer.attribute()).dynamic

    def default_value(self) -> typing.Any:
        """
        Returns the attribute's default value in UI units — a single
        value for simple attributes or a list for compounds such as
        ``translate``. Returns None for attribute types that have no
        queryable default (strings, matrices, messages, ...).
        """
        result = self._attribute_query(listDefault=True)
        if not result:
            return None
        return result[0] if len(result) == 1 else list(result)

    def minimum(self) -> float|None:
        """
        Returns the hard minimum of a numeric attribute, or None if it
        has no minimum.
        """
        if not self._attribute_query(minExists=True):
            return None
        result = self._attribute_query(minimum=True)
        return result[0] if result and len(result) == 1 else result

    def maximum(self) -> float|None:
        """
        Returns the hard maximum of a numeric attribute, or None if it
        has no maximum.
        """
        if not self._attribute_query(maxExists=True):
            return None
        result = self._attribute_query(maximum=True)
        return result[0] if result and len(result) == 1 else result

    def set_minimum(self, value: float|None) -> None:
        """
        Sets the hard minimum of a dynamic numeric attribute. Pass None
        to remove the minimum. Maya does not allow the range of static
        (node-type defined) attributes to be edited.
        """
        if value is None:
            self._edit_dynamic(hasMinValue=False)
        else:
            self._edit_dynamic(minValue=value)

    def set_maximum(self, value: float|None) -> None:
        """
        Sets the hard maximum of a dynamic numeric attribute. Pass None
        to remove the maximum. Maya does not allow the range of static
        (node-type defined) attributes to be edited.
        """
        if value is None:
            self._edit_dynamic(hasMaxValue=False)
        else:
            self._edit_dynamic(maxValue=value)

    def enum_names(self) -> list[str]|None:
        """
        Returns the field names of an enum attribute ordered by their
        index, or None if this is not an enum attribute. Gaps in the
        index range (e.g. ``a=0:b=5``) are skipped, so the position in
        the list is not necessarily the field's value.
        """
        attribute = self._pointer.attribute()
        if not attribute.hasFn(om.MFn.kEnumAttribute):
            return None

        fn = om.MFnEnumAttribute(attribute)
        names = []
        for index in range(fn.getMin(), fn.getMax() + 1):
            try:
                names.append(fn.fieldName(index))
            except RuntimeError:
                continue
        return names

    def set_enum_names(self, names: list[str]) -> None:
        """
        Replaces the fields of a dynamic enum attribute. Each entry may
        be a plain name (indexed sequentially) or ``"name=index"``.
        """
        self._edit_dynamic(enumName=":".join(names))

    # ------------------------------------------------------------------
    # State (keyable / channel box / lock / hidden)
    # ------------------------------------------------------------------

    def is_keyable(self) -> bool:
        """
        Returns True if the attribute is keyable.
        """
        return self._pointer.isKeyable

    def set_keyable(self, state: bool) -> None:
        """
        Sets whether the attribute is keyable. Keyable attributes are
        always shown in the channel box.
        """
        cmds.setAttr(self.path(), keyable=state)

    def is_in_channel_box(self) -> bool:
        """
        Returns True if the attribute is shown in the channel box —
        either because it is keyable or because it has been flagged as
        a non-keyable channel box attribute.
        """
        return self._pointer.isKeyable or self._pointer.isChannelBox

    def set_in_channel_box(self, state: bool) -> None:
        """
        Shows or hides a non-keyable attribute in the channel box.
        Note Maya ignores this for keyable attributes (always shown);
        use ``set_keyable(False)`` first to hide one.
        """
        cmds.setAttr(self.path(), channelBox=state)

    def is_locked(self) -> bool:
        """
        Returns True if the attribute is locked.
        """
        return self._pointer.isLocked

    def lock(self) -> None:
        """
        Locks the attribute. Equivalent to ``set(lock=True)``.
        """
        cmds.setAttr(self.path(), lock=True)

    def unlock(self) -> None:
        """
        Unlocks the attribute. Equivalent to ``set(lock=False)``.
        """
        cmds.setAttr(self.path(), lock=False)

    def is_hidden(self) -> bool:
        """
        Returns True if the attribute is hidden from the UI (Attribute
        Editor, Channel Box, Connection Editor etc).
        """
        return om.MFnAttribute(self._pointer.attribute()).hidden

    def set_hidden(self, state: bool) -> None:
        """
        Sets whether a dynamic attribute is hidden from the UI. Static
        (node-type defined) attributes cannot be hidden per node.

        ``addAttr`` cannot edit the hidden flag, so this goes through
        ``MFnAttribute`` and is therefore not undoable.
        """
        if not self.is_dynamic():
            raise RuntimeError(
                f"{self.name(include_node=True)} is a static attribute and cannot be edited"
            )
        om.MFnAttribute(self._pointer.attribute()).hidden = state

    # ------------------------------------------------------------------
    # Naming (nice name / alias)
    # ------------------------------------------------------------------

    def nice_name(self) -> str:
        """
        Returns the UI ("nice") name of the attribute, e.g.
        ``"Translate X"``.
        """
        return cmds.attributeName(self.path(), nice=True)

    def set_nice_name(self, nice_name: str) -> None:
        """
        Sets the UI ("nice") name of a dynamic attribute.
        """
        self._edit_dynamic(niceName=nice_name)

    def alias(self) -> str|None:
        """
        Returns the alias of this attribute (e.g. a blendShape target
        name for ``weight[0]``), or None if it has no alias.
        """
        return cmds.aliasAttr(self.path(), query=True) or None

    def set_alias(self, alias: str|None) -> None:
        """
        Sets the alias of this attribute. Pass None to remove the
        current alias.
        """
        if alias is None:
            current = self.alias()
            if current:
                cmds.aliasAttr(f"{self.node().full_name()}.{current}", remove=True)
            return
        cmds.aliasAttr(alias, self.path())

    # ------------------------------------------------------------------
    # Structure (arrays / compounds)
    # ------------------------------------------------------------------

    def is_array(self) -> bool:
        """
        Returns True if this is an array (multi) attribute — the
        array itself, not one of its elements.
        """
        return self._pointer.isArray

    def is_element(self) -> bool:
        """
        Returns True if this plug is an element of an array attribute
        (e.g. ``weight[0]``).
        """
        return self._pointer.isElement

    def is_compound(self) -> bool:
        """
        Returns True if this is a compound attribute (one with
        children, e.g. ``translate``).
        """
        return self._pointer.isCompound

    def index(self) -> int|None:
        """
        Returns the logical index of an array element plug, or None if
        this plug is not an array element.
        """
        if not self._pointer.isElement:
            return None
        return self._pointer.logicalIndex()

    def children(self) -> mref.ReferenceList:
        """
        Returns the child attributes of a compound attribute (e.g.
        ``translateX/Y/Z`` for ``translate``). Returns an empty list for
        non-compounds, and for an array of compounds — ask one of its
        elements for its children instead.
        """
        plug = self._pointer
        if not plug.isCompound or (plug.isArray and not plug.isElement):
            return mref.ReferenceList()
        return mref.ReferenceList(
            mref.get(plug.child(index))
            for index in range(plug.numChildren())
        )

    def parent(self) -> mref.ReferencedItem|None:
        """
        Returns the plug this one sits under — the compound parent for
        a child attribute (``translate`` for ``translateX``), or the
        array plug for an element (``weight`` for ``weight[0]``).
        Returns None for a top-level attribute.
        """
        plug = self._pointer
        if plug.isChild:
            return mref.get(plug.parent())
        if plug.isElement:
            return mref.get(plug.array())
        return None

    def elements(self) -> mref.ReferenceList:
        """
        Returns the existing elements of an array attribute in
        physical (storage) order. Returns an empty list if this is not
        an array.
        """
        plug = self._pointer
        if not plug.isArray:
            return mref.ReferenceList()
        return mref.ReferenceList(
            mref.get(plug.elementByPhysicalIndex(index))
            for index in range(plug.numElements())
        )

    def element(self, index: int) -> mref.ReferencedItem:
        """
        Returns the element of an array attribute at the given logical
        index. The element does not need to exist yet. Raises TypeError
        if this is not an array attribute.
        """
        if not self._pointer.isArray:
            raise TypeError(f"{self.name(include_node=True)} is not an array attribute")
        return mref.get(self._pointer.elementByLogicalIndex(index))

    # ------------------------------------------------------------------
    # Connections (single source)
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        """
        Returns True if this attribute has any incoming or outgoing
        connection.
        """
        return self._pointer.isConnected

    def source(self, skip_converters: bool = True) -> mref.ReferencedItem|None:
        """
        Returns the single attribute driving this one, or None if it
        has no input. Convenience form of :meth:`inputs` — see there for
        ``skip_converters``.
        """
        inputs = self.inputs(skip_converters=skip_converters)
        return inputs[0] if inputs else None

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete(self) -> None:
        """
        Deletes this attribute. For an array element the element is
        removed (breaking its connections); otherwise the attribute must
        be dynamic — static attributes raise RuntimeError.
        """
        if self._pointer.isElement:
            cmds.removeMultiInstance(self.path(), b=True)
            return

        if not self.is_dynamic():
            raise RuntimeError(
                f"Cannot delete static attribute {self.name(include_node=True)}"
            )
        cmds.deleteAttr(self.path())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _attribute_name(self) -> str:
        """
        Returns the long name of the underlying attribute, without any
        parent path or array indices — the form ``attributeQuery`` and
        ``addAttr(edit=True)`` expect.
        """
        return om.MFnAttribute(self._pointer.attribute()).name

    def _attribute_query(self, **kwargs) -> typing.Any:
        """
        Runs ``cmds.attributeQuery`` for this attribute. Returns None
        if Maya rejects the query for this attribute type.
        """
        try:
            return cmds.attributeQuery(
                self._attribute_name(),
                node=self.node().full_name(),
                **kwargs
            )
        except RuntimeError:
            return None

    def _edit_dynamic(self, **kwargs) -> None:
        """
        Runs ``cmds.addAttr(edit=True)`` against this attribute, raising
        RuntimeError up front if it is not a dynamic attribute.
        """
        if not self.is_dynamic():
            raise RuntimeError(
                f"{self.name(include_node=True)} is a static attribute and cannot be edited"
            )
        cmds.addAttr(
            f"{self.node().full_name()}.{self._attribute_name()}",
            edit=True,
            **kwargs
        )

    def __repr__(self) -> str:
        """
        This string representation of this type
        """
        return self.name(include_node=True)
