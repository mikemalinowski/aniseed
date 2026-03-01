import maya.api.OpenMaya as om


def _get_surface_fn(node_name):
    sel = om.MSelectionList()
    sel.add(node_name)
    dag = sel.getDagPath(0)

    if dag.node().hasFn(om.MFn.kTransform):
        dag.extendToShape()

    if not dag.node().hasFn(om.MFn.kNurbsSurface):
        raise RuntimeError("Node is not a nurbsSurface")

    return om.MFnNurbsSurface(dag)



def serialise(surface, relative_to=None):
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
        sel = om.MSelectionList()
        sel.add(relative_to)
        ref_dag = sel.getDagPath(0)
        ref_transform = om.MFnTransform(ref_dag)
        inv_matrix = ref_transform.transformation().asMatrix().inverse()
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


def construct(data, name="reconstructedSurface", parent_transform=None):
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

    # If a parent transform is given, apply its world matrix
    if parent_transform:
        sel = om.MSelectionList()
        sel.add(parent_transform)
        dag = sel.getDagPath(0)
        parent_fn = om.MFnTransform(dag)
        parent_matrix = parent_fn.transformation().asMatrix()
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
