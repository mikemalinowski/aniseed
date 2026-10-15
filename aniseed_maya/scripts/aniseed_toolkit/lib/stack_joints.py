"""
Helpers for components which create their own joint when they are first
added to the stack.
"""
import mref


def create_from_selection(name: str, match_to_parent: bool = False) -> mref.ReferencedItem:
    """
    Creates a joint as a child of the first selected node, or at the world
    if nothing is selected.

    Args:
        name: The name to give the joint
        match_to_parent: If True, the joint is matched to the world
            transform of its parent

    Returns:
        The created joint
    """
    selection = mref.selected()
    parent = selection[0] if selection else None

    joint = mref.create("joint", parent=parent)
    joint.rename(name)

    if parent and match_to_parent:
        joint.match_to(parent)

    return joint
