import maya.cmds as mc
import maya.api.OpenMaya as om


# ----------------------------------------------------------------------------------
def dag_path(name):
    if not mc.objExists(name):
        return None

    slist = om.MSelectionList()
    slist.add(name)

    return slist.getDagPath(0)
    return dagpath


# --------------------------------------------------------------------------------------
def get_name(mobject):
    """
    This will return the name of the MObject pointer

    Args:
        pointer: MObject pointer

    Returns:
        Name of the node
    """
    if isinstance(mobject, str):
        return mobject

    try:
        return om.MFnDependencyNode(mobject).name()

    except ValueError:
        raise ValueError(f"Could not get dependency node for {mobject}")



# --------------------------------------------------------------------------------------
def get_object(object_name: str) -> om.MObject:
    """
    Given the name of a node, this will return the MObject representation. This means
    we can track the node easily without having to worry about name changes.

    Args:
        node_name: Name of the node to get a pointer to

    Returns:
        MObject reference
    """
    if isinstance(object_name, om.MObject):
        return object_name

    try:
        selection_list = om.MSelectionList()
        selection_list.add(object_name)

        return selection_list.getDependNode(0)

    except RuntimeError:
        raise RuntimeError(f"Could not find node {object_name}")
