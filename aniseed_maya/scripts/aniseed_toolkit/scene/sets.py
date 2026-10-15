"""
Object set helpers.
"""
import mref

from ..core import _nodes


def add_to(nodes: str or list[str], set_name: str) -> None:
    """
    Adds the given node or nodes to the set with the given name. The set
    is created (empty, at the scene level) if it does not exist.

    Args:
        nodes: A node or list of nodes to add to the set
        set_name: The name of the set to add the nodes to

    Raises:
        Exception: If a node with the given set name exists but is not an
            objectSet
    """
    # -- Check we have a set
    if mref.objExists(set_name):
        # -- RuntimeError for an ambiguous name, as cmds.nodeType raised
        if not _nodes.resolve(set_name, error=RuntimeError).node_type() == "objectSet":
            raise Exception(f"{set_name} is not a set!")
    else:
        mref.sets(name=set_name, empty=True)

    # -- sets(add=) rather than the ObjectSet trait's add_members, which
    # -- uses forceElement
    mref.sets(
        nodes,
        add=set_name,
    )
