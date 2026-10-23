"""
Spatial maths between nodes and points: distances, factors, directions,
interpolation and upvector positions.

Vector maths uses OpenMaya's MVector, which some functions also return.
Node positions are read with xform through mref, so components (such as
vertices) can be given as well as transforms.
"""
import logging
import time

from maya.api import OpenMaya as om
import mref

from ..registry import tool

log = logging.getLogger(__name__)


def timed_function_call(func):
    """
    Decorator which logs how long each call of the decorated function
    took, in seconds.

    Args:
        func: The function to time

    Returns:
        The wrapped function, which returns whatever func returns
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        log.info("%s took %s seconds", func.__name__, end_time - start_time)
        return result
    return wrapper


def distance_between(
    node_a: str = "",
    node_b: str = "",
    print_result: bool = False,
) -> float:
    """
    Returns the world space distance between two nodes.

    Args:
        node_a: The node to measure from. Uses the first selected node if
            not given.
        node_b: The node to measure to. Uses the second selected node if
            not given.
        print_result: Unused, kept for compatibility. Nothing is printed.

    Returns:
        The distance between the two nodes
    """
    if not node_a:
        node_a = mref.selected()[0]

    if not node_b:
        node_b = mref.selected()[1]

    point_a = om.MVector(*mref.xform(node_a, query=True, translation=True, worldSpace=True))
    point_b = om.MVector(*mref.xform(node_b, query=True, translation=True, worldSpace=True))

    return (point_b - point_a).length()


def factor_between(node: str = "", from_this: str = "", to_this: str = "", print_result: bool = False) -> float:
    """
    Returns how far the given node is from to_this, as a factor of the
    distance between from_this and to_this, clamped between zero and one.
    A node on top of to_this gives 0, and a node at least as far from
    to_this as from_this is gives 1.

    Args:
        node: The node to measure
        from_this: The first node to compare to
        to_this: The second node to compare to
        print_result: If True, the result is logged

    Returns:
        The clamped factor
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
        log.info(f"Factor of {node} between {from_this} and {to_this} is {distance_factor}")

    return distance_factor


def direction_between(
    node_a: str = "",
    node_b: str = "",
    print_result: bool = False,
) -> list[float]:
    """
    Returns the normalised direction from node_a to node_b, expressed in
    the local space of node_a (so it takes node_a's rotation into account).

    Two temporary transforms (named Xfoo1 and Xfoo2) are created to do the
    calculation and are deleted again.

    Args:
        node_a: The node to measure from
        node_b: The node to measure to
        print_result: If True, the result is logged

    Returns:
        The direction as an MVector
    """
    a = mref.create("transform")
    a.rename("Xfoo1")
    b = mref.create("transform")
    b.rename("Xfoo2")

    a.add_child(b)

    a.set_matrix(
        mref.xform(node_a, query=True, matrix=True, worldSpace=True),
        space="world",
    )

    b.set_matrix(
        mref.xform(node_b, query=True, matrix=True, worldSpace=True),
        space="world",
    )

    # -- xform without a space flag rather than get_position, whose
    # -- explicit objectSpace query differs in the last floating point bits
    n = om.MVector(*b.xform(query=True, translation=True)).normal()

    a.delete()

    if print_result:
        log.info(f"Direction between {node_a} and {node_b} is {n}")

    return n


def calculate_upvector_position(
    point_a: str = "",
    point_b: str = "",
    point_c: str = "",
    length: float = 0.5,
    create: bool = False,
):
    """
    Calculates a position for an upvector (pole vector) from three points,
    such as the joints of a limb. The position lies on the plane of the
    three points, out from point_b, away from the line between point_a and
    point_c.

    Args:
        point_a: Start point, as a node or a position (list of floats). Uses
            the first selected node if not given.
        point_b: Mid point, as a node or a position. Uses the second
            selected node if not given.
        point_c: End point, as a node or a position. Uses the third
            selected node if not given.
        length: The distance from point_b, as a factor of the chain length
            (the distance a->b plus b->c)
        create: If True, a transform is created at the position and
            selected

    Returns:
        The world space position as an MVector
    """
    if not point_a:
        point_a = mref.selected()[0]

    if not point_b:
        point_b = mref.selected()[1]

    if not point_c:
        point_c = mref.selected()[2]

    # -- If we're given nodes we need to convert them to positions
    if isinstance(point_a, (str, mref.ReferencedItem)):
        point_a = mref.xform(point_a, query=True, translation=True, worldSpace=True)

    if isinstance(point_b, (str, mref.ReferencedItem)):
        point_b = mref.xform(point_b, query=True, translation=True, worldSpace=True)

    if isinstance(point_c, (str, mref.ReferencedItem)):
        point_c = mref.xform(point_c, query=True, translation=True, worldSpace=True)

    point_a = om.MVector(*point_a)
    point_b = om.MVector(*point_b)
    point_c = om.MVector(*point_c)

    # -- Create the vectors between the points
    ab = point_b - point_a
    ac = point_c - point_a
    cb = point_c - point_b

    # -- Project point_b onto the line between point_a and point_c
    center = point_a + (((ab * ac) / (ac * ac))) * ac

    # -- Create a normal vector pointing from that point to point_b
    normal = (point_b - center).normal()

    # -- Define the length for the upvector
    vector_length = (ab.length() + cb.length()) * length

    # -- Calculate the final vector position
    result = point_b + (vector_length * normal)

    if create:
        node = mref.create("transform")
        node.set_position(
            [result.x, result.y, result.z],
            space="world",
        )
        node.select()

    return result


def calculate_four_point_spline_positions(
    nodes: [str],
):
    """
    Returns the four control point positions of a single span cubic curve
    which follows the given nodes. A temporary linear curve is built through
    the nodes, rebuilt to one cubic span, read and then deleted.

    Args:
        nodes: The nodes (in order) the curve should pass along

    Returns:
        List of four world space positions, each a list of three floats
    """
    degree = 1

    points = [
        list(mref.xform(node, query=True, translation=True, worldSpace=True))
        for node in nodes
    ]

    knots = [
        i
        for i in range(len(points) + degree - 1)
    ]

    curve = mref.curve(
        point=points,
        degree=degree,
        knot=knots
    )

    quad_curve = mref.rebuildCurve(
        curve,
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

    shape = quad_curve.shape()
    cv_count = shape.attr("spans").get() + shape.attr("degree").get()

    positions = [
        list(mref.xform(f"{quad_curve.full_name()}.cv[{cv_index}]", query=True, translation=True, worldSpace=True))
        for cv_index in range(cv_count)
    ]

    quad_curve.delete()
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
    """
    Linearly interpolates between two vectors (of any length), component
    by component.

    Args:
        vector_a: The vector at a factor of 0
        vector_b: The vector at a factor of 1 (at least as long as
            vector_a)
        factor: How far to interpolate from vector_a to vector_b

    Returns:
        The interpolated vector as a list of floats
    """
    resolved_vector = []

    for component_index in range(len(vector_a)):
        a = vector_a[component_index]
        b = vector_b[component_index]
        resolved_vector.append(a + (b - a) * factor)

    return resolved_vector
