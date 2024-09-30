import maya.cmds as mc
import maya.api.OpenMaya as om


# ------------------------------------------------------------------------------
def distance_between(node_a, node_b):
    """
    Returns the distance between two objects

    :param node_a: First object to measure from
    :type node_a: pm.nt.Transform

    :param node_b: Second object to measure to
    :type node_b: pm.nt.Transform

    :return: float
    """

    point_a = mc.xform(
        node_a,
        query=True,
        translation=True,
        worldSpace=True,
    )

    point_b = mc.xform(
        node_b,
        query=True,
        translation=True,
        worldSpace=True,
    )

    point_a = om.MVector(*point_a)
    point_b = om.MVector(*point_b)

    delta = point_b - point_a
    return delta.length()
