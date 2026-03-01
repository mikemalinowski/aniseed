from pygments.styles.dracula import selection

import aniseed_toolkit
from maya import cmds
import maya.api.OpenMaya as om


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


def first_selected():
    """
    This will return the first selected object
    """
    selection = cmds.ls(selection=True)
    if selection:
        return selection[0]
    return None