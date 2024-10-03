import json
import qute
import typing

import maya.cmds as mc
import maya.api.OpenMaya as om

from . import library
from . import mutils
from . import colors


# --------------------------------------------------------------------------------------
def write(node: str = None, filepath: str = None) -> typing.Dict:
    """
    Writes the curve data of the given node to the given filepath

    :param node: Node to read from
    :type node: pm.nt.DagNode

    :param filepath: Path to write the data into
    :type filepath: str

    :return: Data being stored
    """
    if not node:
        node = mc.ls(sl=True)[0]

    if not filepath:
        filepath = qute.utilities.request.filepath(
            title="Shape Writing",
            filter_="*.json (*.json)",
            save=True,
            parent=None,
        )

    if not filepath:
        return dict()

    data = read(node)

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


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def read(node: str) -> typing.Dict:
    """
    Looks at all the NurbsCurve shape nodes under  the given node
    and attempts to read them
    """
    if mc.nodeType(node) == "transform" or mc.nodeType(node) == "joint":
        shapes = mc.listRelatives(node, type="nurbsCurve")

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

        pointer = mutils.get_object(shape)
        nurbs_fn = om.MFnNurbsCurve(pointer)

        node_data = dict(
            form=mc.getAttr(f"{shape}.form"),
            degree=mc.getAttr(f"{shape}.degree"),
            knots=[n for n in nurbs_fn.knots()],
            cvs=[list(p)[:3] for p in nurbs_fn.cvPositions(om.MSpace.kObject)],
        )

        data["curves"].append(node_data)

    return data


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def scale(node: str, scale_by: float, x=1, y=1, z=1):
    """
    This will do an in-place scaling of the shapes for a given node
    """
    curves = mc.listRelatives(node, type="nurbsCurve")

    if not curves:
        return

    for curve in curves:
        mc.xform(
            f"{curve}.cv[:]",
            scale=[
                scale_by * x,
                scale_by * y,
                scale_by * z,
            ],
        )

# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def offset(node: str, offset_by: float, x=1, y=1, z=1):
    """
    This will do an in-place scaling of the shapes for a given node
    """
    curves = mc.listRelatives(node, type="nurbsCurve")

    if not curves:
        return

    for curve in curves:
        mc.xform(
            f"{curve}.cv[:]",
            translation=[
                offset_by * x,
                offset_by * y,
                offset_by * z,
            ],
            relative=True,
        )


# --------------------------------------------------------------------------------------
# noinspection PyTypeChecker,PyUnresolvedReferences
def apply(node: str, data: typing.Dict or str, clear: bool = True, color=None, scale_by=1) -> typing.List[str]:
    """
    Applies the given shape data to the given node.

    Returning a list of shape nodes that have been added
    """
    if isinstance(data, str):
        data = library.shape_data(data)

        if not data:
            print(f"Could not find shape for {data}")
            return False

    if clear:
        curves = mc.listRelatives(node, type="nurbsCurve")

        if curves:
            mc.delete(curves)

    # -- Define a list which we will collate all the shapes
    # -- in
    shape_list = list()

    # -- Cycle over each curve element in the data
    for curve_data in data["curves"]:
        # -- Create a curve with the given cv"s
        transform = mc.curve(
            p=[
                p # refine_from_up_axis(p, up_axis=data.get("up_axis", "z"))
                for p in curve_data["cvs"]
            ],
            d=curve_data["degree"],
            k=curve_data["knots"],
            # per=curve_data["form"],
        )

        # -- Parent the shape under the node
        curve = mc.listRelatives(transform, type="nurbsCurve")[0]

        mc.parent(
            curve,
            node,
            shape=True,
            r=True,
        )

        # -- Delete the transform
        mc.delete(transform)

        shape_list.append(curve)

    scale(
        node,
        scale_by,
    )

    if color:
        colors.apply(
            node,
            *color
        )

    mc.select(node)

    return shape_list


# --------------------------------------------------------------------------------------
def combine(nodes: typing.List[str] = None):
    """
    Parents all the shapes under all the given nodes under the first given node
    """
    if not nodes:
        nodes = mc.ls(sl=True)

    if not nodes:
        return

    if len(nodes) < 2:
        print("At least two nodes must be given")
        return

    base_node = nodes[0]

    for node in nodes[1:]:

        for shape in mc.listRelatives(node, type="nurbsCurve"):
            mc.parent(
                shape,
                base_node,
                shape=True,
                r=True,
            )

        mc.delete(node)


# --------------------------------------------------------------------------------------
def rotate_shape(node, x=0.0, y=0.0, z=0.0, pivot=None):
    """
    Spins the shape around by the given x, y, z (local values)

    :param node: The node whose shapes should be spun
    :type node: pm.nt.Transform or shape

    :param x: Amount to spin on the shapes local X axis in degrees
    :type x: float

    :param y: Amount to spin on the shapes local Y axis in degrees
    :type y: float

    :param z: Amount to spin on the shapes local Z axis in degrees
    :type z: float

    :param pivot: Optional alternate pivot to rotate around. This can
        either be a vector (pm.dt.Vector) or an actual object (pm.nt.Transform)
    :type pivot: pm.dt.Vector or pm.nt.Transform

    :return: None
    """
    # -- If we"re not given a pivot, then default
    # -- to a zero vector.
    pivot = pivot or list()

    # -- Get a list of all the curves we need to modify
    all_curves = list()

    if mc.nodeType(node) == "transform" or mc.nodeType(node) == "joint":
        all_curves.extend(
            mc.listRelatives(
                node,
                shapes=True,
            )
        )

    elif mc.nodeType(node) == "nurbsCurve":
        all_curves.append(node)

    # -- Validate that all entries are nurbs curves
    all_curves = [
        curve
        for curve in all_curves
        if mc.nodeType(curve) == "nurbsCurve"
    ]

    for curve in all_curves:

        dag = mutils.dag_path(curve)
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


# --------------------------------------------------------------------------------------
def apply_colour(node, r, g, b):

    # -- Get a list of all the curves we need to modify
    all_curves = list()

    if mc.nodeType(node) == "transform" or mc.nodeType(node) == "joint":
        all_curves.extend(
            mc.listRelatives(
                node,
                shapes=True,
            )
        )

    elif mc.nodeType(node) == "nurbsCurve":
        all_curves.append(node)

    for curve in all_curves:
        mc.setAttr(f"{curve}.overrideEnabled", True)
        mc.setAttr(f"{curve}.overrideRGBColors", True)

        mc.setAttr(f"{curve}.overrideColorR", r)
        mc.setAttr(f"{curve}.overrideColorG", g)
        mc.setAttr(f"{curve}.overrideColorB", b)
