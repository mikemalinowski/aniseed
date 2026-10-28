"""
Private helper for resolving caller-supplied nodes to mref items while
keeping the errors maya.cmds gives for bad names.
"""
from maya import cmds
import mref


def resolve(node, error=ValueError):
    """
    Returns the mref item for the given node. mref items are returned
    unchanged.

    Unlike mref.get, a name which matches no node, or more than one node,
    raises an error with the same message cmds gives, rather than returning
    the string or silently picking the first match.

    Args:
        node: A node name (str) or an mref item
        error: The exception type to raise. cmds raises ValueError for most
            commands; pass RuntimeError to match the commands (such as
            setAttr and nodeType) which raise that instead.

    Returns:
        The mref item

    Raises:
        error: If the name matches no node or more than one node
    """
    if isinstance(node, mref.ReferencedItem):
        return node

    matches = cmds.ls(node)

    if not matches:
        raise error(f"No object matches name: {node}")

    if len(matches) > 1:
        raise error(f"More than one object matches name: {node}")

    return mref.get(node)
