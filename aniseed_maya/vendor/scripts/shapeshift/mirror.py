import maya.cmds as mc
import maya.api.OpenMaya as om

AXIS = ["x", "y", "z"]

from . import core
from . import mutils


# --------------------------------------------------------------------------------------
def get_mirror_array(axis):

    scale = [
        1,
        1,
        1,
    ]

    scale[AXIS.index(axis.lower())] = -1

    return scale


# --------------------------------------------------------------------------------------
def mirror_shape(node, axis):
    curves = mc.listRelatives(node, type="nurbsCurve")

    if not curves:
        return

    scale = get_mirror_array(axis)

    for curve in curves:
        mc.xform(
            f"{curve}.cv[:]",
            scale=scale,
        )
    # # -- Apply the shapes to that side
    # crab.utils.shapes.apply(target_node, shape_data)
    #
    # # -- Invert the shape globally
    # for source_shape, target_shape in zip(source_node.getShapes(),
    #                                       target_node.getShapes()):
    #
    #     for idx in range(source_shape.numCVs()):
    #         # -- Get the worldspace position of the current cv
    #         source_pos = source_shape.getCV(
    #             idx,
    #             space="world",
    #         )
    #
    #         # -- Set the position of the cv with the X axis
    #         # -- inverted
    #         target_shape.setCV(
    #             idx,
    #             [
    #                 source_pos[0] * -1,
    #                 source_pos[1],
    #                 source_pos[2],
    #             ],
    #             space="world",
    #         )
    #
    #     # -- Update teh curve to propagate the change
    #     target_shape.updateCurve()
    pass

# ----------------------------------------------------------------------------------
def mirror_across(from_node, to_node, axis):

    scale = get_mirror_array(axis)

    # -- Read the shape data from the current side
    shape_data = core.read(from_node)

    # -- Clear the shapes on the other side
    shapes_to_remove = mc.listRelatives(
        to_node,
        shapes=True,
    ) or list()
    
    for shape in shapes_to_remove:
        mc.delete(shape)

    # -- Apply the shapes to that side
    core.apply(node=to_node, data=shape_data)
    
    source_shapes = mc.listRelatives(from_node, shapes=True) or list()
    target_shapes = mc.listRelatives(to_node, shapes=True) or list()
    
    for shape_idx in range(len(source_shapes)):
        
        source_shape = source_shapes[shape_idx]
        target_shape = target_shapes[shape_idx]

        source_dag = mutils.dag_path(source_shape)
        target_dag = mutils.dag_path(target_shape)
        
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
