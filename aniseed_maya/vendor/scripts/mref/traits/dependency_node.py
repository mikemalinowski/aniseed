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

    def add_proxy(self, name, source_attribute, keyable=True, **kwargs):
        """
        Adds a proxy attribute to this node
        """
        cmds.addAttr(
            self.item.full_name(),
            shortName=name,
            proxy=mref.get(source_attribute).name(include_node=True),
            keyable=keyable,
            **kwargs
        )
        return mref.get(f"{self.item.full_name()}.{name}")

    def add_separator_attribute(self):

        character = "_"
        name_to_use = character * 4

        while cmds.objExists(f"{self.item.full_name()}.{name_to_use}"):
            name_to_use += character

        cmds.addAttr(
            self.item.full_name(),
            shortName=name_to_use,
            keyable=True,
        )
        cmds.setAttr(f"{self.item.full_name()}.{name_to_use}", lock=True)

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

    # ------------------------------------------------------------------
    # Identity and scene state
    # ------------------------------------------------------------------

    def uuid(self) -> str:
        """
        Returns the node's UUID as a string. Unlike the name, this stays
        the same when the node is renamed or reparented, and is saved
        with the scene.
        """
        return self._dependency_node.uuid().asString()

    def exists(self) -> bool:
        """
        Returns True if the node this item points at still exists in the
        scene. Returns False once the node has been deleted, even if the
        deletion is still sitting in the undo queue.
        """
        return om.MObjectHandle(self._pointer).isValid()

    def is_referenced(self) -> bool:
        """
        Returns True if this node was brought into the scene by a file
        reference (and so cannot be renamed, deleted or reparented).
        """
        return self._dependency_node.isFromReferencedFile

    def reference_node(self) -> mref.ReferencedItem|None:
        """
        Returns the reference node (``fooRN``) that brought this node
        into the scene, or None if the node is not referenced.
        """
        if not self.is_referenced():
            return None
        return mref.get(
            cmds.referenceQuery(self.item.full_name(), referenceNode=True)
        )

    def is_default_node(self) -> bool:
        """
        Returns True if this is one of the nodes Maya creates in every
        scene (``time1``, ``lambert1``, ``persp`` etc.) and which cannot be
        deleted.
        """
        return self._dependency_node.isDefaultNode

    def node_namespace(self) -> str:
        """
        Returns the namespace this node lives in, without a leading colon
        (``char:rig`` for a nested namespace), or an empty string for the
        root namespace.

        Named ``node_namespace`` rather than ``namespace`` so it does not
        clash with ``Reference.namespace()``, which returns the namespace
        of a reference's *contents* rather than of the node itself.
        """
        short_name = self.name()
        if ":" not in short_name:
            return ""
        return short_name.rsplit(":", 1)[0]

    def set_node_namespace(self, namespace: str) -> None:
        """
        Moves this node into the given namespace, keeping its base name.
        The namespace (and any missing parents of a nested ``a:b``
        namespace) is created if it does not exist. Pass an empty string
        to move the node back to the root namespace.
        """
        namespace = namespace.strip(":")
        base_name = self.name().rsplit(":", 1)[-1]

        if namespace and not cmds.namespace(exists=f":{namespace}"):
            cmds.namespace(add=f":{namespace}")

        cmds.rename(
            self.item.full_name(),
            f":{namespace}:{base_name}" if namespace else f":{base_name}",
        )

    def select(self, add: bool = False) -> None:
        """
        Selects this node, replacing the current selection unless ``add``
        is True.
        """
        if add:
            cmds.select(self.item.full_name(), add=True)
        else:
            cmds.select(self.item.full_name(), replace=True)

    def duplicate(self, name: str = None, **kwargs) -> mref.ReferencedItem:
        """
        Duplicates this node and returns the duplicate. Any additional
        kwargs are passed to ``cmds.duplicate`` (for example
        ``upstreamNodes=True`` or ``inputConnections=True``). For DAG
        nodes the duplicate of this node is returned, not its children.
        """
        if name:
            kwargs["name"] = name

        return mref.get(
            cmds.duplicate(self.item.full_name(), **kwargs)[0]
        )

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def node_notes(self) -> str:
        """
        Returns the text shown in the Notes section of the Attribute
        Editor, or an empty string if the node has no notes.

        Named ``node_notes`` because ``notes`` is the name of the Maya
        attribute that stores them, and a method of that name would
        shadow property-style access to it.
        """
        if not cmds.attributeQuery("notes", node=self.item.full_name(), exists=True):
            return ""
        return cmds.getAttr(f"{self.item.full_name()}.notes") or ""

    def set_node_notes(self, text: str) -> None:
        """
        Sets the text shown in the Notes section of the Attribute Editor,
        creating the ``notes`` attribute if the node does not have one.
        """
        if not cmds.attributeQuery("notes", node=self.item.full_name(), exists=True):
            cmds.addAttr(
                self.item.full_name(),
                longName="notes",
                shortName="nts",
                dataType="string",
            )
        cmds.setAttr(f"{self.item.full_name()}.notes", text, type="string")

    # ------------------------------------------------------------------
    # Connections and history
    # ------------------------------------------------------------------

    def plug_connections(
        self,
        source: bool = True,
        destination: bool = True,
    ) -> list[tuple[mref.ReferencedItem, mref.ReferencedItem]]:
        """
        Returns this node's connections as ``(source_plug,
        destination_plug)`` tuples of attribute ReferencedItems, always
        ordered in the direction data flows.

        :param source: Include incoming connections (where this node's
            plug is the destination).
        :param destination: Include outgoing connections (where this
            node's plug is the source).
        """
        results = []
        seen = set()

        for plug in self._dependency_node.getConnections():

            pairs = []
            if source:
                upstream = plug.source()
                if not upstream.isNull:
                    pairs.append((upstream, plug))

            if destination:
                pairs.extend((plug, downstream) for downstream in plug.destinations())

            for source_plug, destination_plug in pairs:
                key = (source_plug.name(), destination_plug.name())
                if key in seen:
                    continue
                seen.add(key)
                results.append((mref.get(source_plug), mref.get(destination_plug)))

        return results

    def history(self, node_type: str = None, **kwargs) -> mref.ReferenceList:
        """
        Returns the nodes upstream of this node, nearest first, using
        ``cmds.listHistory`` (so a transform's history includes its
        shape's). The node itself is not included. Any additional kwargs
        are passed to ``cmds.listHistory`` (for example
        ``pruneDagObjects=True`` or ``levels=1``).

        :param node_type: Only return nodes of this type, or of a type
            derived from it (``"geometryFilter"`` returns all deformers).
        """
        return self._list_history(node_type, future=False, **kwargs)

    def future(self, node_type: str = None, **kwargs) -> mref.ReferenceList:
        """
        Returns the nodes downstream of this node, nearest first, using
        ``cmds.listHistory(future=True)``. The node itself is not
        included. Any additional kwargs are passed to
        ``cmds.listHistory``.

        :param node_type: Only return nodes of this type, or of a type
            derived from it.
        """
        return self._list_history(node_type, future=True, **kwargs)

    def _list_history(self, node_type: str, future: bool, **kwargs) -> mref.ReferenceList:
        results = mref.ReferenceList()

        for node in cmds.listHistory(self.item.full_name(), future=future, **kwargs) or []:
            if node_type and not cmds.objectType(node, isAType=node_type):
                continue

            item = mref.get(node)
            if item == self.item:
                continue

            results.append(item)
        return results

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

