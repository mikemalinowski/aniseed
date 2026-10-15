"""
OpenMaya helpers for getting MObjects, MDagPaths and names. These are used by
the modules which work through the OpenMaya api (such as shapes and skin);
most code should prefer mref.

This module is OpenMaya based by design: its purpose is to hand out api
objects, which mref does not expose in these forms.
"""
import maya.api.OpenMaya as om
import mref

from ..registry import tool


@tool(
    "MObject Name",
    classification="Rigging",
    categories=["Misc"],
    user_facing=False,
)
def get_name(mobject: om.MObject = None):
    """
    Returns the name of the node the given MObject points to. If a string
    is given it is returned unchanged.

    Args:
        mobject: The MObject to get the name of (or a node name)

    Returns:
        The name of the node

    Raises:
        ValueError: If the MObject is not a dependency node (for instance a
            null MObject)
    """
    if isinstance(mobject, str):
        return mobject

    try:
        return om.MFnDependencyNode(mobject).name()

    except ValueError:
        raise ValueError(f"Could not get dependency node for {mobject}")


@tool(
    "Get MObject",
    categories=["Misc"],
    user_facing=False,
)
def get_mobject(name: str = "") -> om.MFnDependencyNode:
    """
    Returns the MObject for the node with the given name. An MObject keeps
    pointing at the node even if it is renamed. If an MObject is given it is
    returned unchanged.

    Args:
        name: Name of the node to get the MObject for

    Returns:
        The MObject of the node

    Raises:
        RuntimeError: If no node with the given name exists
    """
    if isinstance(name, om.MObject):
        return name

    try:
        selection_list = om.MSelectionList()
        selection_list.add(name)

        return selection_list.getDependNode(0)

    except RuntimeError:
        raise RuntimeError(f"Could not find node {name}")


@tool(
    "Get DagPath",
    user_facing=False,
)
def get_dagpath(name: str = "") -> om.MDagPath or None:
    """
    Returns the MDagPath for the node with the given name.

    Args:
        name: Name of the node to resolve the dag path for

    Returns:
        The MDagPath of the node, or None if no node with that name exists
    """
    if not mref.objExists(name):
        return None

    slist = om.MSelectionList()
    slist.add(name)

    return slist.getDagPath(0)
