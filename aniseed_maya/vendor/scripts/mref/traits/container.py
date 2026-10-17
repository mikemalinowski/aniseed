import mref
from maya import cmds
from maya.api import OpenMaya as om


class Container(mref.Trait):
    """
    Trait bound to any node with ``MFn.kContainerBase`` — asset
    containers (``container``) and DAG containers (``dagContainer``).
    Exposes the member nodes, the published (bound) attributes, and the
    parent / child container hierarchy.

    Note that ``animLayer`` nodes derive from ``containerBase`` in the
    node-type hierarchy but do not report ``kContainerBase``, so they
    are not bound.
    """

    # -- Sits above the generic Transform trait (dagContainer is a transform)
    priority = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._container = om.MFnContainerNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kContainerBase)

    def member_nodes(self) -> mref.ReferenceList:
        """
        Returns the nodes which are direct members of this container.
        Nested containers are returned as members, but not their
        contents.
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in self._container.getMembers()
        )

    def add_member_nodes(self, nodes: list|mref.ReferencedItem|str, include_network: bool = False) -> None:
        """
        Adds the given node(s) to this container. If ``include_network``
        is True then the upstream and downstream nodes connected to them
        are added too, mirroring Maya's "include network" option.
        """
        cmds.container(
            self.item.full_name(),
            edit=True,
            addNode=_names(nodes),
            includeNetwork=include_network,
            force=True,
        )

    def remove_member_nodes(self, nodes: list|mref.ReferencedItem|str) -> None:
        """
        Removes the given node(s) from this container. The nodes
        themselves are kept in the scene.
        """
        cmds.container(
            self.item.full_name(),
            edit=True,
            removeNode=_names(nodes),
        )

    def is_member_node(self, node: mref.ReferencedItem|str) -> bool:
        """
        Returns True if the given node is a direct member of this
        container.
        """
        return mref.get(node) in self.member_nodes()

    def published_attributes(self) -> dict:
        """
        Returns the published attributes of this container as a dict of
        ``{published_name: attribute}`` where ``attribute`` is the
        ReferencedItem of the member-node attribute bound to that name.
        Published names which are not bound to any attribute are
        omitted.
        """
        plugs, names = self._container.getPublishedPlugs()
        return {
            name: mref.get(plug)
            for plug, name in zip(plugs, names)
        }

    def publish_attribute(self, attribute: mref.ReferencedItem|str, published_name: str = None) -> None:
        """
        Publishes the given member-node attribute on this container under
        ``published_name`` (defaulting to the attribute's own long name)
        and binds it.
        """
        attribute = mref.get(attribute)
        plug = attribute.pointer()

        if published_name is None:
            published_name = plug.partialName(useLongNames=True)

        cmds.container(
            self.item.full_name(),
            edit=True,
            publishAndBind=[attribute.full_name(), published_name],
        )

    def unpublish_attribute(self, published_name: str) -> None:
        """
        Unbinds and removes the published attribute with the given
        published name.
        """
        cmds.container(
            self.item.full_name(),
            edit=True,
            unbindAndUnpublish=f"{self.item.full_name()}.{published_name}",
        )

    def parent_container(self) -> mref.ReferencedItem|None:
        """
        Returns the container this container is nested within, or None
        if it is a top-level container.
        """
        parent = self._container.getParentContainer()
        if parent.isNull():
            return None
        return mref.get(parent)

    def child_containers(self) -> mref.ReferenceList:
        """
        Returns the containers nested directly within this container
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in self._container.getSubcontainers()
        )


def _names(nodes) -> list[str]:
    """
    Resolves a node, or list of nodes, given as ReferencedItems or
    strings into a list of node names suitable for cmds.
    """
    if not isinstance(nodes, (list, tuple)):
        nodes = [nodes]
    return [
        node.full_name() if isinstance(node, mref.ReferencedItem) else node
        for node in nodes
    ]
