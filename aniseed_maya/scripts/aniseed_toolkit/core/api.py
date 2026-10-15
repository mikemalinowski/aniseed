"""
OpenMaya helpers for getting MObjects, MDagPaths and names. These are used by
the modules which work through the OpenMaya api (such as shapes and skin);
most code should prefer mref.
"""
from maya import cmds
import maya.api.OpenMaya as om

from ..registry import tool


@tool(
    "MObject Name",
    classification="Rigging",
    categories=["Misc"],
    user_facing=False,
)
def get_name(mobject: om.MObject = None):
    """
    This will return the name of the MObject pointer

    Args:
        mobject: MObject pointer

    Returns:
        Name of the node
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
    Given the name of a node, this will return the MObject representation. This means
    we can track the node easily without having to worry about name changes.

    Args:
        name: Name of the node to get a pointer to

    Returns:
        MObject reference
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
    This will return the name of the MObject pointer

    Args:
        name: Name of the node to resolve the dagpath for

    Returns:
        OpenMaya.DagPath
    """
    if not cmds.objExists(name):
        return None

    slist = om.MSelectionList()
    slist.add(name)

    return slist.getDagPath(0)
