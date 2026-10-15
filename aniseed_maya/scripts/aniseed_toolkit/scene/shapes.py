"""
Curve shapes: applying shapes from the shape library or from data, editing
(rotating, offsetting, scaling, mirroring, colouring) and saving shapes.

Nodes are handled through mref. Two things deliberately stay outside it:

- CV edits go through ``cmds.xform`` on ``<curve>.cv[:]`` strings, as mref
  items wrap nodes and attributes but not components.
- Per-CV vector maths (rotating, world space mirroring) uses
  ``OpenMaya.MFnNurbsCurve`` directly, as it reads and writes the CVs with
  exact double precision and has no mref equivalent.
"""
import functools
import json
import os
import typing

from maya import cmds
import maya.api.OpenMaya as om
import mref

from ..registry import tool
from .. import resources
from ..core import units as _units


def _get_node(node, error=ValueError) -> mref.ReferencedItem:
    """
    Returns the given node (a name or an mref item) as an mref item.

    A name which matches no node, or more than one node, raises the error
    the cmds command this lookup replaces would raise:

    - listRelatives (error=ValueError): "No object matches name: x" or
      "More than one object matches name: x".
    - nodeType (error=RuntimeError): "No object matches name: x" in both
      cases, as nodeType does not distinguish them.

    Args:
        node: Name or mref item of the node
        error: The exception type of the cmds command being replaced
            (ValueError for listRelatives, RuntimeError for nodeType).

    Returns:
        mref.ReferencedItem
    """
    # -- mref.get would silently resolve an ambiguous name to its first match
    if isinstance(node, str) and len(cmds.ls(node)) > 1:
        if error is ValueError:
            raise ValueError(f"More than one object matches name: {node}")
        raise error(f"No object matches name: {node}")

    item = mref.get(node)
    if not isinstance(item, mref.ReferencedItem):
        raise error(f"No object matches name: {node}")
    return item


def _set_override_colour(item: mref.ReferencedItem, rgb: typing.List[float]) -> None:
    """
    Enables the rgb override and outliner colours on the given item and sets
    them to the given (0-1) rgb values.
    """
    item.attr("overrideRGBColors").set(True)
    item.attr("useOutlinerColor").set(True)

    for channel, value in zip(("R", "G", "B"), rgb):
        item.attr(f"overrideColor{channel}").set(value)
        item.attr(f"outlinerColor{channel}").set(value)


def apply_color(node: str = "", r: float = 0, g: float = 0, b: float = 0) -> None:
    """
    Applies the given rgb colour to the node and, if the node is a transform
    or joint, to all of its shapes. The drawing override (rgb mode) and the
    outliner colour are both enabled and set.

    Args:
        node: The node to apply the colour to. This may be a transform, a
            joint or a nurbsCurve shape.
        r: The red channel value (between 0 and 255)
        g: The green channel value (between 0 and 255)
        b: The blue channel value (between 0 and 255)

    Returns:
        None

    Raises:
        TypeError: If node is a transform or joint without any shapes.
    """
    item = _get_node(node, RuntimeError)
    node_type = item.node_type()

    all_shapes = list()

    if node_type in ("transform", "joint"):
        # -- listRelatives returns None for a node without shapes, which
        # -- (as it always has) makes this raise a TypeError.
        all_shapes.extend(mref.listRelatives(item, shapes=True))

    elif node_type == "nurbsCurve":
        all_shapes.append(item)

    rgb = [r / 255.0, g / 255.0, b / 255.0]

    # -- The override may be locked or driven (e.g. by a display layer)
    try:
        item.attr("overrideEnabled").set(True)
    except Exception:
        pass

    _set_override_colour(item, rgb)

    for shape in all_shapes:
        shape.attr("overrideEnabled").set(True)
        _set_override_colour(shape, rgb)


def combine(nodes: typing.List[str] = None):
    """
    Moves the nurbsCurve shapes of all the given nodes under the first given
    node and then deletes those other nodes. If fewer than two nodes are
    given a message is printed and nothing is changed.

    Args:
        nodes: List of nodes to combine, with the first one being the node
            where all the resulting shapes will be placed

    Returns:
        None

    Raises:
        TypeError: If one of the nodes to merge in has no nurbsCurve shapes.
    """
    if len(nodes) < 2:
        print("At least two nodes must be given")
        return

    base_node = nodes[0]
    for node in nodes[1:]:
        # -- listRelatives returns None for a node without curve shapes,
        # -- which (as it always has) makes this raise a TypeError.
        for shape in mref.listRelatives(node, type="nurbsCurve"):
            mref.parent(
                shape,
                base_node,
                shape=True,
                relative=True,
            )

        mref.delete(node)


def rotate(
    node: str = "",
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    pivot: list[float] or str = None,
) -> None:
    """
    Spins the CVs of the node's nurbsCurve shapes around the shape's local
    origin by the given x, y, z rotation (in object space).

    Args:
        node: The node whose shapes should be spun. This may be a transform,
            a joint or a nurbsCurve shape.
        x: Amount to spin on the shapes local X axis in degrees
        y: Amount to spin on the shapes local Y axis in degrees
        z: Amount to spin on the shapes local Z axis in degrees
        pivot: Currently ignored. The shapes always rotate around their
            local origin.

    Returns:
        None

    Raises:
        TypeError: If node is a transform or joint without any shapes.
    """
    item = _get_node(node, RuntimeError)
    node_type = item.node_type()

    # -- Get a list of all the curves we need to modify
    all_curves = list()

    if node_type in ("transform", "joint"):
        # -- listRelatives returns None for a node without shapes, which
        # -- (as it always has) makes this raise a TypeError.
        all_curves.extend(mref.listRelatives(item, shapes=True))

    elif node_type == "nurbsCurve":
        all_curves.append(item)

    # -- Validate that all entries are nurbs curves
    all_curves = [
        curve
        for curve in all_curves
        if curve.node_type() == "nurbsCurve"
    ]

    # -- Degrees to radians. The truncated constant is kept as changing it
    # -- would change the resulting cv positions.
    rotation = om.MEulerRotation(x * 0.017453, y * 0.017453, z * 0.017453)

    for curve in all_curves:
        # -- OpenMaya for the per-CV vector maths, which has no mref equivalent
        nurbs_fn = om.MFnNurbsCurve(curve.dag_path())

        for idx in range(nurbs_fn.numCVs):
            cv_vector = om.MVector(nurbs_fn.cvPosition(idx, om.MSpace.kObject))
            rotated_position = cv_vector.rotateBy(rotation)

            nurbs_fn.setCVPosition(
                idx,
                om.MPoint(
                    rotated_position.x,
                    rotated_position.y,
                    rotated_position.z,
                ),
                space=om.MSpace.kObject,
            )

        nurbs_fn.updateCurve()


def offset(
    node: str = "",
    offset_by: float = 0,
    x: float = 1.0,
    y: float = 1.0,
    z: float = 1.0,
) -> None:
    """
    Moves the CVs of all the nurbsCurve shapes directly under the given node
    by offset_by, multiplied per axis by x, y and z (a relative move).

    Args:
        node: The node whose shapes should be offset. If not given, the first
            selected node is used.
        offset_by: The amount to offset the shapes by
        x: A multiplier for the offset amount specifically on the x axis
        y: A multiplier for the offset amount specifically on the y axis
        z: A multiplier for the offset amount specifically on the z axis

    Returns:
        None
    """
    if not node:
        node = mref.selected()[0]

    curves = _get_node(node).children(node_type="nurbsCurve")

    if not curves:
        return

    for curve in curves:
        cmds.xform(
            f"{curve.full_name()}.cv[:]",
            translation=(
                offset_by * x,
                offset_by * y,
                offset_by * z,
            ),
            relative=True,
        )


def scale(
    node: str = "",
    scale_by: float = 1,
    x: float = 1.0,
    y: float = 1.0,
    z: float = 1.0,
) -> None:
    """
    Scales the CVs of the node's nurbsCurve shapes in place by scale_by,
    multiplied per axis by x, y and z.

    Args:
        node: The node whose shapes should be scaled. This may be a
            nurbsCurve shape, or a node whose nurbsCurve shapes are scaled.
        scale_by: The amount to scale the shapes by
        x: A multiplier for the scale amount specifically on the x axis
        y: A multiplier for the scale amount specifically on the y axis
        z: A multiplier for the scale amount specifically on the z axis

    Returns:
        None
    """
    item = _get_node(node, RuntimeError)

    if item.node_type() == "nurbsCurve":
        curves = [item]
    else:
        curves = item.children(node_type="nurbsCurve")

    if not curves:
        return

    for curve in curves:
        cmds.xform(
            f"{curve.full_name()}.cv[:]",
            scale=(
                scale_by * x,
                scale_by * y,
                scale_by * z,
            ),
        )


def mirror(nodes: list[str] = None, axis: str = "") -> None:
    """
    Mirrors the nurbsCurve shapes of each given node across the given local
    axis, by scaling their CVs by -1 on that axis. Nothing happens if no axis
    is given.

    Note that processing stops at the first node which has no nurbsCurve
    shapes; nodes after it are not mirrored.

    Args:
        nodes: Node, or list of nodes, to perform the mirror on
        axis: What axis should be mirrored (x, y or z, any case)

    Returns:
        None
    """
    if isinstance(nodes, str):
        nodes = [nodes]

    if not axis:
        return

    for node in nodes:
        curves = _get_node(node).children(node_type="nurbsCurve")

        if not curves:
            return

        mirror_scale = _get_mirror_array(axis)

        for curve in curves:
            cmds.xform(
                f"{curve.full_name()}.cv[:]",
                scale=mirror_scale,
            )


def _get_mirror_array(axis):
    """
    Returns a [x, y, z] scale which is 1 on every axis apart from the given
    axis (x, y or z, any case), which is -1.
    """
    core_axis = ["x", "y", "z"]
    scale = [
        1,
        1,
        1,
    ]

    scale[core_axis.index(axis.lower())] = -1

    return scale


def mirror_across(from_nodes: list[str] = "", to_nodes: list[str] = "", axis: str = ""):
    """
    For each pair of nodes, replaces the shapes of the to_node with a copy of
    the shapes of the from_node, mirrored in world space across the given
    axis. Pairs whose to_node does not exist are skipped with a message.

    The to_node is left selected (see load_shape).

    Args:
        from_nodes: The nodes to mirror the shapes from
        to_nodes: The nodes to mirror the shapes onto, matched to from_nodes
            by index
        axis: What world axis should be mirrored (x, y or z, any case)

    Returns:
        None
    """
    for idx, from_node in enumerate(from_nodes):

        to_node = to_nodes[idx]
        if not mref.objExists(to_node):
            print("Could not find node with name : %s" % to_node)
            continue

        mirror_scale = _get_mirror_array(axis)

        # -- Read the shape data from the current side
        shape_data = shape_to_dict(from_node)

        # -- Clear the shapes on the other side
        for shape in _get_node(to_node).shapes():
            shape.delete()

        # -- Apply the shapes to that side
        load_shape(node=to_node, data=shape_data)

        source_shapes = _get_node(from_node).shapes()
        target_shapes = _get_node(to_node).shapes()

        for shape_idx in range(len(source_shapes)):

            # -- OpenMaya for the world space CV maths, which has no
            # -- mref equivalent
            source_nurbs_fn = om.MFnNurbsCurve(source_shapes[shape_idx].dag_path())
            target_nurbs_fn = om.MFnNurbsCurve(target_shapes[shape_idx].dag_path())

            for cv_idx in range(source_nurbs_fn.numCVs):

                source_worldspace_cv = source_nurbs_fn.cvPosition(cv_idx, om.MSpace.kWorld)

                worldspace_vector = om.MVector(source_worldspace_cv)

                target_nurbs_fn.setCVPosition(
                    cv_idx,
                    om.MPoint(
                        worldspace_vector.x * mirror_scale[0],
                        worldspace_vector.y * mirror_scale[1],
                        worldspace_vector.z * mirror_scale[2],
                    ),
                    space=om.MSpace.kWorld,
                )

            target_nurbs_fn.updateCurve()


@tool(
    "Read Shape From Node",
    classification="Rigging",
    categories=["Shapes"],
    user_facing=False,
)
def shape_to_dict(node: str = "") -> typing.Dict:
    """
    Reads the nurbsCurve shapes under the given node (or the given curve shape
    itself) into a dictionary which can be stored as json and re-applied with
    load_shape.

    Args:
        node: The transform or joint whose curve shapes should be read, or a
            nurbsCurve shape

    Returns:
        A dictionary of the form {"node": node, "curves": [...]}, where each
        curve holds its form, degree, knots and object space cvs. An empty
        dictionary is returned (and a message printed) if there are no
        shapes.

    Raises:
        AttributeError: If node is a shape which is not a nurbsCurve (for
            example a mesh).
    """
    item = _get_node(node, RuntimeError)

    if item.node_type() in ("transform", "joint"):
        shapes = item.children(node_type="nurbsCurve")

    else:
        shapes = [item]

    if not shapes:
        print("no shapes found")
        return {}

    # -- Define out output data. Right now we're only storing
    # -- cv's, but we wrap it in a dict so we can expand it
    # -- later without compatibility issues.
    data = dict(
        node=node,
        curves=list(),
    )

    # -- Cycle the shapes and store them
    for shape in shapes:
        node_data = dict(
            form=shape.attr("form").get(),
            degree=shape.attr("degree").get(),
            knots=shape.knots(),
            cvs=shape.cv_positions(space="object"),
        )

        data["curves"].append(node_data)

    return data


@functools.lru_cache(maxsize=None)
def shape_data_from_file(shape_file: str = "") -> typing.Dict or None:
    """
    This will attempt to get the shape dictionary data from a shape file.
    The shape file can either be the local name of a shape in the shapes
    directory or an absolute path to a shape file. The ".json" extension is
    optional.

    The parsed shape data is cached per input string — subsequent calls
    with the same argument return the cached dict without touching
    disk. Call ``shape_data_from_file.cache_clear()`` to invalidate.
    Callers are expected to treat the returned dict as read-only.

    Args:
        shape_file: The shape file to read (either absolute path or the name
            of a shape in the shapes directory)

    Returns:
        dict, or None (and a message is printed) if the file cannot be found
    """
    if not shape_file.endswith(".json"):
        shape_file = shape_file + ".json"

    if not os.path.exists(shape_file):
        shape_file = resources.get("shapes/" + shape_file)

    if not os.path.exists(shape_file):
        print("could not find shape : %s" % shape_file)
        return None

    with open(shape_file, "r") as f:
        return json.load(f)


def save_to_file(node: str = "", filepath: str = "") -> typing.Dict:
    """
    Writes the curve data of the given node (see shape_to_dict) to the given
    filepath as json. Nothing is written if the node has no curve shapes.

    Args:
        node: Node to read from
        filepath: Path to write the data into

    Returns:
        Dict of the data stored in the filepath, or an empty dict if nothing
        was written
    """
    data = shape_to_dict(node)

    if not data:
        return {}

    with open(filepath, "w") as f:
        json.dump(
            data,
            f,
            indent=4,
            sort_keys=True,
        )

    return data


def load_shape(
        node: str = "",
        data: typing.Dict or str = "",
        clear: bool = True,
        color=None,
        scale_by=1,
) -> typing.List[str]:
    """
    Applies the given shape data to the given node, creating one nurbsCurve
    shape under the node per curve in the data. The cvs in the data are in
    centimetres and are converted to the scene's units.

    The node is left selected afterwards.

    Args:
        node: Node to apply the shape data to
        data: Either a dictionary of shape data, or the absolute path
            to a shape file, or the name of a shape in the shapes directory
        clear: If true, any pre-existing curve shapes will be removed before
            this applies the shape.
        color: Optional list [r, g, b] (0-255) which will be used to colour
            the node and its shapes on creation (see apply_color)
        scale_by: Optional multiplier for scaling the shape at the time of it
            being applied.

    Returns:
        List of the names of the shape nodes created. An empty list is
        returned (and a message printed) if the shape cannot be found, in
        which case nothing is changed.
    """

    if isinstance(data, str):
        data = shape_data_from_file(data)

    if not data:
        print("Could not find shape : %s" % data)
        return []

    if clear:
        for curve in _get_node(node).children(node_type="nurbsCurve"):
            curve.delete()

    # -- Define a list which we will collate all the shapes
    # -- in
    shape_list = list()

    # -- Cycle over each curve element in the data
    for curve_data in data["curves"]:
        # -- Create a curve with the given cv's
        points = [
            [
                _units.from_cm(v)
                for v in p
            ]
            for p in curve_data["cvs"]
        ]

        transform = mref.curve(
            point=points,
            degree=curve_data["degree"],
            knot=curve_data["knots"],
        )

        # -- Maya gives a new curve shape a unique name, so its short
        # -- name is the name cmds would report for it.
        curve = transform.children(node_type="nurbsCurve")[0]
        curve_name = curve.name()

        scale(curve, scale_by)

        # -- Parent the shape under the node
        mref.parent(
            curve,
            node,
            shape=True,
            relative=True,
        )

        # -- Delete the transform
        transform.delete()

        shape_list.append(curve_name)

    if color:
        apply_color(node, *color)

    mref.select(node)

    return shape_list


def select_shapes(nodes=None) -> None:
    """
    Selects the shapes of all the given nodes, replacing the current
    selection. If none of the nodes have shapes, the selection is cleared.

    Args:
        nodes: List of nodes whose shapes should be selected

    Returns:
        None
    """
    shapes = []

    for node in nodes:
        shapes.extend(_get_node(node).shapes())

    mref.select(shapes)
