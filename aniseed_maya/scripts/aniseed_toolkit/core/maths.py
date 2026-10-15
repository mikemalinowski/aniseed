"""
Spatial maths between nodes and points: distances, factors, directions,
interpolation and upvector positions.
"""
from maya import cmds
from maya.api import OpenMaya as om

from ..registry import tool


def timed_function_call(func):
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print("{} took {} seconds".format(func.__name__, end_time - start_time))
        return result
    return wrapper


def distance_between(
    node_a: str = "",
    node_b: str = "",
    print_result: bool = False,
) -> float:
    """
    Returns the distance between two objects

    Args:
        node_a: The object to measure from
        node_b: The object to measure to
        print_result: If true, the result will be printed

    Returns:
        The distance between two objects
    """

    if not node_a:
        node_a = cmds.ls(sl=True)[0]

    if not node_b:
        node_b = cmds.ls(sl=True)[1]

    point_a = cmds.xform(
        node_a,
        query=True,
        translation=True,
        worldSpace=True,
    )

    point_b = cmds.xform(
        node_b,
        query=True,
        translation=True,
        worldSpace=True,
    )

    point_a = om.MVector(*point_a)
    point_b = om.MVector(*point_b)

    delta = point_b - point_a

    # if print_result:
    #     print(f"Distance between {node_a} and {node_b} is {delta}")
    return delta.length()


def factor_between(node: str = "", from_this: str = "", to_this: str = "", print_result: bool = False) -> float:
    """
    This will return a factor (between zero and one) for how close the given
    node is between the from_this and to_this nodes.

    Args:
        node: The node to monitor
        from_this: The first node to compare to
        to_this: The second node to compare to

    Returns:
        The factor for how close the given node is between the from_this and to_this
    """
    total_distance = distance_between(from_this, to_this)
    delta = distance_between(node, to_this)

    distance_factor = max(
        0.0,
        min(
            1.0,
            delta / total_distance,
        ),
    )

    if print_result:
        print(f"Factor of {node} between {from_this} and {to_this} is {distance_factor}")

    return distance_factor


def direction_between(
    node_a: str = "",
    node_b: str = "",
    print_result: bool = True,
) -> list[float]:
    """
    This will return a direction vector (normalised vector) between the
    two nodes

    Args:
        node_a: The object to measure from
        node_b: The object to measure to
        print_result: If true, the result will be printed

    Returns:
        The direction vector between the two nodes
    """
    a = cmds.rename(cmds.createNode("transform"), "Xfoo1")
    b = cmds.rename(cmds.createNode("transform"), "Xfoo2")

    cmds.parent(
        b,
        a,
    )

    cmds.xform(
        a,
        matrix=cmds.xform(
            node_a,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    cmds.xform(
        b,
        matrix=cmds.xform(
            node_b,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    tx = cmds.xform(
        b,
        query=True,
        translation=True,
    )

    n = om.MVector(*tx).normal()

    cmds.delete(a)

    if print_result:
        print(f"Direction between {node_a} and {node_b} is {n}")

    return n


def calculate_upvector_position(
    point_a: str = "",
    point_b: str = "",
    point_c: str = "",
    length: float = 0.5,
    create: bool = False,
):
    """
    Based on three points, this will calculate the position for an
    up-vector for the plane.

    Args:
        point_a: Start point (which can be a float list or a node name)
        point_b: End point (which can be a float list or a node name)
        point_c: Start point (which can be a float list or a node name)
        length: By default the vector will be multipled by the chain length
            but you can use this value to multiply that to make it further or
            shorter
        create: If true, a transform node will be created at the specified location

    Returns:
        MVector of the position in worldspace
    """

    if not point_a:
        point_a = cmds.ls(selection=True)[0]

    if not point_b:
        point_b = cmds.ls(selection=True)[1]

    if not point_c:
        point_c = cmds.ls(selection=True)[2]

    # -- If we're given transforms we need to convert them to
    # -- vectors
    if isinstance(point_a, str):
        point_a = cmds.xform(
            point_a,
            query=True,
            translation=True,
            worldSpace=True,
        )

    if isinstance(point_b, str):
        point_b = cmds.xform(
            point_b,
            query=True,
            translation=True,
            worldSpace=True,
        )

    if isinstance(point_c, str):
        point_c = cmds.xform(
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
    center = point_a + (((ab * ac) / (ac * ac))) * ac

    # -- Create a normal vector pointing at the mid point
    normal = (point_b - center).normal()

    # -- Define the length for the upvector
    vector_length = (ab.length() + cb.length()) * length

    # -- Calculate the final vector position
    result = point_b + (vector_length * normal)

    if create:
        node = cmds.createNode('transform')
        cmds.xform(
            node,
            translation=(
                result.x,
                result.y,
                result.z,
            ),
            worldSpace=True,
        )
        cmds.select(node)

    return result


def calculate_four_point_spline_positions(
    nodes: [str],
):
    """
    This will determine the positions for a bezier spline in order
    to keep the joints transforms.

    Args:
        nodes: List of nodes
    """
    positions = list()
    degree = 1

    points = [
        cmds.xform(
            node,
            query=True,
            translation=True,
            worldSpace=True,
        )
        for node in nodes
    ]

    knots = [
        i
        for i in range(len(points) + degree - 1)
    ]

    cmds.curve(
        point=points,
        degree=degree,
        knot=knots
    )

    quad_curve = cmds.rebuildCurve(
        replaceOriginal=True,
        rebuildType=0,  # Uniform
        endKnots=1,
        keepRange=False,
        keepEndPoints=True,
        keepTangents=False,
        spans=1,
        degree=3,
        tolerance=0.01,
    )[0]

    cv_count = cmds.getAttr(f"{quad_curve}.spans") + cmds.getAttr(f"{quad_curve}.degree")

    for cv_index in range(cv_count):
        position = cmds.xform(
            f"{quad_curve}.cv[{cv_index}]",
            query=True,
            translation=True,
            worldSpace=True,
        )
        positions.append(position)

    cmds.delete(quad_curve)
    return positions


@tool(
    "Interpolate Vectors",
    categories=["Transforms"],
    user_facing=False,
)
def interpolate_vector(
    vector_a: list[float],
    vector_b: list[float],
    factor: float,
):
    vector_length = len(vector_a)

    resolved_vector = []

    for component_index in range(vector_length):

        a = vector_a[component_index]
        b = vector_b[component_index]
        interpolated_result = a + (b - a) * factor
        resolved_vector.append(interpolated_result)

    return resolved_vector
