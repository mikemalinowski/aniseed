import os
import json
import typing
from maya import cmds
from . import mutils
from . import rig
import maya.api.OpenMaya as om

from .. import resources

def apply_color(node: str = "", r: float = 0, g: float = 0, b: float = 0) -> None:
    """
    This will apply the given rgb values to the shapes of the selected nodes
    and ensure that their colour overrides are set.

    Args:
        node: The node to apply the colour to
        r: The red channel value (between zero and one)
        g: The green channel value (between zero and one)
        b: The blue channel value (between zero and one)

    Returns:
        None
    """
    rgb = [r, g, b]
    all_shapes = list()

    if cmds.nodeType(node) == "transform" or cmds.nodeType(node) == "joint":
        all_shapes.extend(
            cmds.listRelatives(
                node,
                shapes=True,
            )
        )

    elif cmds.nodeType(node) == "nurbsCurve":
        all_shapes.append(node)

    cmds.setAttr(f"{node}.overrideEnabled", True)
    cmds.setAttr(f"{node}.overrideRGBColors", True)
    cmds.setAttr(f"{node}.useOutlinerColor", True)

    for idx, channel in enumerate(["R", "G", "B"]):
        cmds.setAttr(f"{node}.overrideColor{channel}", rgb[idx] / 255.0)
        cmds.setAttr(f"{node}.outlinerColor{channel}", rgb[idx] / 255.0)

    for shape in all_shapes:

        cmds.setAttr(f"{shape}.overrideEnabled", True)
        cmds.setAttr(f"{shape}.overrideRGBColors", True)
        cmds.setAttr(f"{shape}.useOutlinerColor", True)

        for idx, channel in enumerate(["R", "G", "B"]):
            cmds.setAttr(f"{shape}.overrideColor{channel}", rgb[idx] / 255.0)
            cmds.setAttr(f"{shape}.outlinerColor{channel}", rgb[idx] / 255.0)


def combine(nodes: typing.List[str] = None):
    """
    Parents all the shapes under all the given nodes under the first given node

    Args:
        nodes: List of nodes to combine, with the first one being the node where
            all the resulting shapes will be applied

    Returns:
        None
    """
    if len(nodes) < 2:
        print("At least two nodes must be given")
        return

    base_node = nodes[0]
    for node in nodes[1:]:
        for shape in cmds.listRelatives(node, type="nurbsCurve"):
            cmds.parent(
                shape,
                base_node,
                shape=True,
                relative=True,
            )

        cmds.delete(node)


def rotate(
    node: str = "",
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    pivot: list[float] or str = None,
) -> None:
    """
    Spins the shape around by the given x, y, z (local values)

    Args:
        node: The node whose shapes should be spun
        x: Amount to spin on the shapes local X axis in degrees
        y: Amount to spin on the shapes local Y axis in degrees
        z: Amount to spin on the shapes local Z axis in degrees
        pivot: Optional alternate pivot to rotate around. This can
            either be a vector (list[float]) or an actual object (str)

    Returns:
        None
    """
    # -- If we"re not given a pivot, then default
    # -- to a zero vector.
    pivot = pivot or list()

    # -- Get a list of all the curves we need to modify
    all_curves = list()

    if cmds.nodeType(node) == "transform" or cmds.nodeType(node) == "joint":
        all_curves.extend(
            cmds.listRelatives(
                node,
                shapes=True,
            )
        )

    elif cmds.nodeType(node) == "nurbsCurve":
        all_curves.append(node)

    # -- Validate that all entries are nurbs curves
    all_curves = [
        curve
        for curve in all_curves
        if cmds.nodeType(curve) == "nurbsCurve"
    ]

    for curve in all_curves:
        dag = mutils.get_dagpath(curve)
        nurbs_fn = om.MFnNurbsCurve(dag)

        for idx in range(nurbs_fn.numCVs):
            worldspace_cv = nurbs_fn.cvPosition(idx, om.MSpace.kObject)

            worldspace_vector = om.MVector(worldspace_cv)
            # -- Get the relative vector between the cv and pivot
            relative_cv = worldspace_vector #- pivot

            # -- Rotate our relative vector by the rotation values
            # -- given to us
            rotated_position = relative_cv.rotateBy(
                om.MEulerRotation(x * 0.017453, y * 0.017453, z * 0.017453),
            )

            # -- Add the worldspace pivot vector onto our rotated vector
            # -- to give ourselves the final vector
            final_position = rotated_position# + pivot

            nurbs_fn.setCVPosition(
                idx,
                om.MPoint(
                    final_position.x,
                    final_position.y,
                    final_position.z,
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
    This will do an in-place scaling of the shapes for a given node

    Args:
        node: The node whose shapes should be offset
        offset_by: The amount to offset the shapes by
        x: A multiplier for the offset amount specifically on the x axis
        y: A multiplier for the offset amount specifically on the y axis
        z: A multiplier for the offset amount specifically on the z axis

    Returns:
        None
    """

    if not node:
        node = cmds.ls(selection=True)[0]

    curves = cmds.listRelatives(node, type="nurbsCurve")

    if not curves:
        return

    for curve in curves:
        cmds.xform(
            f"{curve}.cv[:]",
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
    This will do an in-place scaling of the shapes for a given node

    Args:
        node: The node whose shapes should be offset
        scale_by: The amount to offset the shapes by
        x: A multiplier for the offset amount specifically on the x axis
        y: A multiplier for the offset amount specifically on the y axis
        z: A multiplier for the offset amount specifically on the z axis

    Returns:
        None
    """
    if cmds.nodeType(node) == "nurbsCurve":
        curves = [node]
    else:
        curves = cmds.listRelatives(node, type="nurbsCurve")

    if not curves:
        return

    for curve in curves:
        cmds.xform(
            f"{curve}.cv[:]",
            scale=(
                scale_by * x,
                scale_by * y,
                scale_by * z,
            ),
        )


def mirror(nodes: list[str] = None, axis: str = "") -> None:
    """
    This will mirror the shapes for a given node across a specific axis (x, y, z)

    Args:
        nodes: List of nodes to perform the mirror on
        axis: What axis should be mirrored (x, y, z)

    Returns: None
    """
    if isinstance(nodes, str):
        nodes = [nodes]

    if not axis:
        return

    for node in nodes:
        curves = cmds.listRelatives(node, type="nurbsCurve")

        if not curves:
            return

        scale = _get_mirror_array(axis)

        for curve in curves:
            cmds.xform(
                f"{curve}.cv[:]",
                scale=scale,
            )


def _get_mirror_array(axis):
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
    This will attempt to mirror (globally) the shape from the from_node to the
    to_node across the specified axis.

    Args:
        from_nodes: What node should be the mirror from
        to_nodes: What node should be the mirror to
        axis: What axis should be mirrored (x, y, z)

    Returns:
        None
    """
    for idx, from_node in enumerate(from_nodes):

        to_node = to_nodes[idx]
        if not cmds.objExists(to_node):
            print("Could not find node with name : %s" % to_node)
            continue


        scale = _get_mirror_array(axis)

        # -- Read the shape data from the current side
        shape_data = shape_to_dict(from_node)

        # -- Clear the shapes on the other side
        shapes_to_remove = cmds.listRelatives(
            to_node,
            shapes=True,
        ) or list()

        for shape in shapes_to_remove:
            cmds.delete(shape)

        # -- Apply the shapes to that side
        load_shape(node=to_node, data=shape_data)

        source_shapes = cmds.listRelatives(from_node, shapes=True) or list()
        target_shapes = cmds.listRelatives(to_node, shapes=True) or list()

        for shape_idx in range(len(source_shapes)):

            source_shape = source_shapes[shape_idx]
            target_shape = target_shapes[shape_idx]

            source_dag = mutils.get_dagpath(source_shape)
            target_dag = mutils.get_dagpath(target_shape)

            source_nurbs_fn = om.MFnNurbsCurve(source_dag)
            target_nurbs_fn = om.MFnNurbsCurve(target_dag)

            for cv_idx in range(source_nurbs_fn.numCVs):

                source_worldspace_cv = source_nurbs_fn.cvPosition(cv_idx, om.MSpace.kWorld)

                worldspace_vector = om.MVector(source_worldspace_cv)

                worldspace_vector.x = worldspace_vector.x * scale[0]
                worldspace_vector.y = worldspace_vector.y * scale[1]
                worldspace_vector.z = worldspace_vector.z * scale[2]

                target_nurbs_fn.setCVPosition(
                    cv_idx,
                    om.MPoint(
                        worldspace_vector.x,
                        worldspace_vector.y,
                        worldspace_vector.z,
                    ),
                    space=om.MSpace.kWorld,
                )

            target_nurbs_fn.updateCurve()


def global_mirror(mapping: str = "_LF:_RT", axis="x"):

    from_tag = mapping.split(":")[0]
    to_tag = mapping.split(":")[1]

    for node in rig.all_controls():
        if from_tag not in node:
            continue

        to_node = node.replace(from_tag, to_tag)

        if not cmds.objExists(to_node):
            continue

        mirror_across(
            from_nodes=[node],
            to_nodes=[to_node],
            axis=axis,
        )


def shape_to_dict(node: str = "") -> typing.Dict:
    """
    Looks at all the NurbsCurve shape nodes under  the given node
    and attempts to read them into a dictionary format.

    Args:
        node: The node to seralise the shape data for

    Returns:
        dictionary
    """
    if cmds.nodeType(node) == "transform" or cmds.nodeType(node) == "joint":
        shapes = cmds.listRelatives(node, type="nurbsCurve")

    else:
        shapes = [node]
    if not shapes:
        print("no shapes found")
        return {}

    # -- Define out output data. Right now we"re only storing
    # -- cv"s, but we wrap it in a dict so we can expand it
    # -- later without compatibility issues.
    data = dict(
        node=node,
        curves=list(),
    )

    # -- Cycle the shapes and store thm
    for shape in shapes:
        pointer = mutils.get_mobject(shape)
        nurbs_fn = om.MFnNurbsCurve(pointer)

        node_data = dict(
            form=cmds.getAttr(f"{shape}.form"),
            degree=cmds.getAttr(f"{shape}.degree"),
            knots=[n for n in nurbs_fn.knots()],
            cvs=[list(p)[:3] for p in nurbs_fn.cvPositions(om.MSpace.kObject)],
        )

        data["curves"].append(node_data)

    return data

def shape_data_from_file(shape_file: str = "") -> typing.Dict or None:
    """
    This will attempt to get the shape dictionary data from a shape file.
    The shape file can either be the local name of a shape in the shapes
    directory or an absolute path to a shape file.

    Args:
        shape_file: The shape file to read (either absolute path or the name
            of a shape in the shapes directory)

    Returns:
        dict
    """
    if not shape_file.endswith(".json"):
        shape_file = shape_file + ".json"

    if not os.path.exists(shape_file):
        shape_file = resources.get("shapes/" + shape_file)

    if not os.path.exists(shape_file):
        print("could not find shape : %s" % shape_file)
        return None

    with open (shape_file, "r") as f:
        return json.load(f)


def save_to_file(node: str = "", filepath: str = "") -> typing.Dict:
    """
    Writes the curve data of the given node to the given filepath

    Args:
        node: Node to read from
        filepath: Path to write the data into

    Returns:
        Dict of the data stored in the filepath
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
    Applies the given shape data to the given node.

    Args:
        node: Node to apply the shape data to
        data: Either a dictionary of shape data, or the absolute path
            to a shape file, or the name of a shape in the shapes directory
        clear: If true, any pre-existing shapes will be removed before this applies
            the shape.
        color: Optional list [r, g, b] which will be used to colour the shape
            on creation
        scale_by: Optional multiplier for scaling the shape at the time of it
            being applied.

    Returns:
        List of shape nodes created
    """

    if isinstance(data, str):
        data = shape_data_from_file(data)

    if not data:
        print("Could not find shape : %s" % data)
        return []

    if clear:
        for curve in cmds.listRelatives(node, type="nurbsCurve") or list():
            cmds.delete(curve)

    # -- Define a list which we will collate all the shapes
    # -- in
    shape_list = list()

    # -- Cycle over each curve element in the data
    for curve_data in data["curves"]:
        # -- Create a curve with the given cv"s
        transform = cmds.curve(
            point=[
                p
                for p in curve_data["cvs"]
            ],
            degree=curve_data["degree"],
            knot=curve_data["knots"],
        )

        # -- Parent the shape under the node
        curve = cmds.listRelatives(transform, type="nurbsCurve")[0]

        scale(curve, scale_by)

        cmds.parent(
            curve,
            node,
            shape=True,
            relative=True,
        )

        # -- Delete the transform
        cmds.delete(transform)

        shape_list.append(curve)

    if color:
        apply_color(node, *color)

    cmds.select(node)

    return shape_list


def select_shapes(nodes=None) -> None:
    """
    This will return a list of shape files which are present in the
    aniseed toolkit shapes directory

    Returns:
        List of absolute paths to the json shape files
    """
    shapes = []

    for node in nodes:
        shapes.extend(
            cmds.listRelatives(
                node,
                shapes=True,
            ) or list()
        )

    cmds.select(shapes)
