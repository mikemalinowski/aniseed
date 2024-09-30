import maya.cmds as mc
import maya.api.OpenMaya as om


# ------------------------------------------------------------------------------
def calculate_upvector_position(point_a, point_b, point_c, length=0.5):
    """
    Based on three points, this will calculate the position for an
    up-vector for the plane.

    :param point_a: Start point
    :type point_a: pm.dt.Vector or pm.nt.Transform

    :param point_b: Mid Point
    :type point_b: pm.dt.Vector or pm.nt.Transform

    :param point_c: End Point
    :type point_c: pm.dt.Vector or pm.nt.Transform

    :param length: Optional multiplier for the length of the vector. By
        default this is 0.5 of the sum of the points ab and bc.
    :type length: float

    :return: pm.nt.Vector
    """

    # -- If we're given transforms we need to convert them to
    # -- vectors
    if isinstance(point_a, str):
        point_a = mc.xform(
            point_a,
            query=True,
            translation=True,
            worldSpace=True,
        )

    if isinstance(point_b, str):
        point_b = mc.xform(
            point_b,
            query=True,
            translation=True,
            worldSpace=True,
        )

    if isinstance(point_c, str):
        point_c = mc.xform(
            point_c,
            query=True,
            translation=True,
            worldSpace=True,
        )

    point_a = om.MVector(*point_a)
    point_b = om.MVector(*point_b)
    point_c = om.MVector(*point_c)

    # -- Create the vectors between the points
    ab = point_b - point_a
    ac = point_c - point_a
    cb = point_c - point_b

    # -- Get the center point between the end points
    center = point_a + (((ab*ac) / (ac*ac))) * ac

    # -- Create a normal vector pointing at the mid point
    normal = (point_b - center).normal()

    # -- Define the length for the upvector
    vector_length = (ab.length() + cb.length()) * length

    # -- Calculate the final vector position
    result = point_b + (vector_length * normal)

    return result


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


# ------------------------------------------------------------------------------
def direction_between(node_a, node_b):

    a = mc.rename(mc.createNode("transform"), "Xfoo1")
    b = mc.rename(mc.createNode("transform"), "Xfoo2")

    mc.parent(
        b,
        a,
    )

    mc.xform(
        a,
        matrix=mc.xform(
            node_a,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    mc.xform(
        b,
        matrix=mc.xform(
            node_b,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    tx = mc.xform(
        b,
        query=True,
        translation=True,
    )

    n = om.MVector(*tx).normal()

    mc.delete(a)
    # mc.delete(b)

    return n


# ------------------------------------------------------------------------------
def lerp(v1, v2, a):
    """
    Returns a vector which is the interpolation between v1 and v2

    :param v1: Vector to lerp from
    :type v1: pm.dt.Vector

    :param v2: Vector to lerp to
    :type v2: pm.dt.Vector

    :param a: How much alpha to lerp
    :type a: float
    """
    result = (v2 * a) + (v1 * (1.0 - a))
    return result
