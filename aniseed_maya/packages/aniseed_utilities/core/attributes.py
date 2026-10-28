"""
Attribute helpers: separator attributes and locking/hiding attributes.
"""
import mref

from . import _nodes


def add_separator(node: str = "") -> None:
    """
    Adds a locked, keyable attribute named with underscores, which shows as
    a separator line in the channel box. The name starts at eight
    underscores and grows by one until it is unique on the node.

    Args:
        node: Node to add the separator to. Uses the first selected node if
            no node is given.

    Returns:
        None
    """
    node = _nodes.resolve(node) if node else mref.selected()[0]

    character = "_"
    name_to_use = character * 8

    while node.has_attribute(name_to_use):
        name_to_use += character

    mref.addAttr(
        node,
        shortName=name_to_use,
        keyable=True,
    )
    node.attr(name_to_use).lock()


def lock_and_hide(nodes: list, attributes: list, lock=True, hide=True) -> None:
    """
    Sets the lock state and channel box visibility of the given attributes
    on each of the given nodes.

    Args:
        nodes: The nodes to edit
        attributes: The names of the attributes to edit on each node
        lock: If True the attributes are locked, if False they are unlocked
        hide: If True the attributes are made non-keyable and removed from
            the channel box, if False they are made keyable (and so shown)

    Returns:
        None
    """
    for node in nodes:
        # -- Names are used as given rather than resolved: setAttr edits
        # -- every node an ambiguous name matches, and raises Maya's own
        # -- RuntimeError for a missing one
        node_name = node if isinstance(node, str) else node.full_name()
        for attribute in attributes:
            # -- One setAttr call with all three flags, as Maya applies
            # -- them together
            mref.setAttr(
                f"{node_name}.{attribute}",
                lock=lock,
                channelBox=not hide,
                keyable=not hide,
            )
