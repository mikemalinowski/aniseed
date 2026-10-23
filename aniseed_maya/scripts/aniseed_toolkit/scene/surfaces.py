"""
Serialising and constructing nurbs surfaces.

This module works through OpenMaya (MFnNurbsSurface) by design: it reads and
writes the whole cv/knot description of a surface in single api calls, which
mref does not expose.
"""
import maya.api.OpenMaya as om

from ..registry import tool


def _get_surface_fn(node_name):
    """
    Returns an MFnNurbsSurface for the given surface shape, or for the
    shape of the given transform. Raises a RuntimeError if it is not a
    nurbs surface.
    """
    sel = om.MSelectionList()
    sel.add(node_name)
    dag = sel.getDagPath(0)

    if dag.node().hasFn(om.MFn.kTransform):
        dag.extendToShape()

    if not dag.node().hasFn(om.MFn.kNurbsSurface):
        raise RuntimeError("Node is not a nurbsSurface")

    return om.MFnNurbsSurface(dag)


def _local_matrix(node_name):
    """
    Returns the local transformation matrix (MMatrix) of the given
    transform.
    """
    sel = om.MSelectionList()
    sel.add(node_name)
    return om.MFnTransform(sel.getDagPath(0)).transformation().asMatrix()


@tool(
    "Serialise Nurbs Surface",
    classification="Rigging",
    categories=["Surfaces"],
)
def serialise(surface, relative_to=None):
    """
    Returns a json friendly description of a nurbs surface, which construct
    can rebuild it from.

    Args:
        surface: The nurbs surface shape, or its transform
        relative_to: Optional transform. If given, the world space cv
            positions are multiplied by the inverse of this node's local
            transformation matrix (not its world matrix).

    Returns:
        Dictionary with the keys degreeU, degreeV, formU, formV, knotsU,
        knotsV, cvs (a list per u of [x, y, z] lists per v), weights (a
        flat list) and relativeTo (the relative_to argument)

    Raises:
        RuntimeError: If the node is not a nurbs surface
    """
    fn = _get_surface_fn(surface)

    degree_u = fn.degreeInU
    degree_v = fn.degreeInV
    form_u = fn.formInU
    form_v = fn.formInV
    knots_u = list(fn.knotsInU())
    knots_v = list(fn.knotsInV())
    num_u = fn.numCVsInU
    num_v = fn.numCVsInV

    # Get CVs in world space
    cvs = fn.cvPositions(om.MSpace.kWorld)

    # Compute transform relative to another object if given
    if relative_to:
        inv_matrix = _local_matrix(relative_to).inverse()
    else:
        inv_matrix = None

    cv_grid = []
    weights = []

    index = 0
    for u in range(num_u):
        row = []
        for v in range(num_v):
            p = cvs[index]
            if inv_matrix:
                p = p * inv_matrix  # transform to relative space
            row.append([p.x, p.y, p.z])
            weights.append(p.w)
            index += 1
        cv_grid.append(row)

    return {
        "degreeU": degree_u,
        "degreeV": degree_v,
        "formU": form_u,
        "formV": form_v,
        "knotsU": knots_u,
        "knotsV": knots_v,
        "cvs": cv_grid,
        "weights": weights,
        "relativeTo": relative_to
    }


@tool(
    "Construct Nurbs Surface",
    classification="Rigging",
    categories=["Surfaces"],
)
def construct(data, name="reconstructedSurface", parent_transform=None):
    """
    Creates a nurbs surface from data returned by serialise. The surface is
    created under a new transform at the scene root.

    Args:
        data: The serialised surface description
        name: The name to give the new transform
        parent_transform: Optional transform. If given, the cv positions are
            multiplied by this node's local transformation matrix. The new
            surface is not parented to it.

    Returns:
        The full path of the new surface transform
    """
    degree_u = data["degreeU"]
    degree_v = data["degreeV"]
    form_u = data["formU"]
    form_v = data["formV"]
    knots_u = om.MDoubleArray(data["knotsU"])
    knots_v = om.MDoubleArray(data["knotsV"])
    cvs = data["cvs"]
    weights = data["weights"]

    num_u = len(cvs)
    num_v = len(cvs[0])

    points = om.MPointArray()
    index = 0

    # If a parent transform is given, apply its matrix
    if parent_transform:
        parent_matrix = _local_matrix(parent_transform)
    else:
        parent_matrix = None

    for u in range(num_u):
        for v in range(num_v):
            x, y, z = cvs[u][v]
            w = weights[index]
            pt = om.MPoint(x, y, z, w)
            if parent_matrix:
                pt = pt * parent_matrix
            points.append(pt)
            index += 1

    fn = om.MFnNurbsSurface()
    surface_obj = fn.create(
        points,
        knots_u,
        knots_v,
        degree_u,
        degree_v,
        form_u,
        form_v,
        False
    )

    dag_fn = om.MFnDagNode(surface_obj)
    dag_fn.setName(name)
    return dag_fn.fullPathName()
