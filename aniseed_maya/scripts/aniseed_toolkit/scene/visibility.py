"""
Showing and hiding nodes, using the draw style for joints.
"""
import mref

from ..core import _nodes


def hide(items: list[str] = None) -> None:
    """
    Hides the given nodes. Joints are hidden by setting their draw style to
    None (so their children stay visible); other nodes have their
    visibility turned off.

    Args:
        items: A node or list of nodes to hide. Uses the selection if not
            given.

    Returns:
        None
    """
    if not items:
        items = mref.selected()

    if not isinstance(items, list):
        items = [items]

    for item in items:
        # -- RuntimeError, as cmds.nodeType raised for a bad name
        item = _nodes.resolve(item, error=RuntimeError)

        if item.node_type() == "joint":
            item.attr("drawStyle").set(2)  # None (invisible)

        else:
            item.hide()


def show(items: list[str] = None) -> None:
    """
    Shows the given nodes. Joints are shown by setting their draw style to
    Bone; other nodes have their visibility turned on.

    Args:
        items: A node or list of nodes to show. Uses the selection if not
            given.

    Returns:
        None
    """
    if not items:
        items = mref.selected()

    if not isinstance(items, list):
        items = [items]

    for item in items:
        # -- RuntimeError, as cmds.nodeType raised for a bad name
        item = _nodes.resolve(item, error=RuntimeError)

        if item.node_type() == "joint":
            item.attr("drawStyle").set(0)  # Bone

        else:
            item.show()
