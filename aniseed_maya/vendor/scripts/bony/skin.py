import os
import json
import maya.mel
import maya.cmds as mc

from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as om_anim

from . import utils


# --------------------------------------------------------------------------------------
def disconnect_all_skins():
    for skin in mc.ls(type="skinCluster"):
        mc.skinCluster(
            skin,
            edit=True,
            moveJointsMode=True,
        )

# --------------------------------------------------------------------------------------
def connect_all_skins():
    for skin in mc.ls(type="skinCluster"):
        mc.skinCluster(
            skin,
            edit=True,
            moveJointsMode=False,
        )

# --------------------------------------------------------------------------------------
def copy_skin(skinned_mesh=None, unskinned_meshes=None):

    # -- If we are not given our inputs, then resolve them from the
    # -- current selection
    skinned_mesh = skinned_mesh or mc.ls(sl=True)[0]
    unskinned_meshes = unskinned_meshes or mc.ls(sl=True)[1:]

    if not isinstance(unskinned_meshes, list):
        unskinned_meshes = [unskinned_meshes]

    # -- Look for the mesh
    skin = maya.mel.eval(f'findRelatedSkinCluster "{skinned_mesh}";')

    # -- Get all the joints for the skin
    influences = mc.skinCluster(
        skin,
        query=True,
        influence=True,
    )

    for target in unskinned_meshes:

        # -- Create a skin cluster for the given target
        new_skin = mc.skinCluster(
            influences,
            target,
            toSelectedBones=True,
            maximumInfluences=mc.skinCluster(
                skin,
                query=True,
                maximumInfluences=True,
            ),
        )[0]

        # -- Copy the skin weights between them
        mc.copySkinWeights(
            sourceSkin=skin,
            destinationSkin=new_skin,
            noMirror=True,
            surfaceAssociation="closestPoint",
            influenceAssociation=["name", "closestJoint", "label"],
        )

    # -- Keep the source mesh selected
    mc.select(skinned_mesh)


# --------------------------------------------------------------------------------------
def _get_mesh_components(mesh):

    # -- Get the vertex count
    vertex_count = mc.polyEvaluate(
        mesh,
        v=True,
    )

    # -- Build a list of all the vertices
    vertex_indices = [i for i in range(vertex_count)]
    indices_fn = om.MFnSingleIndexedComponent()
    vertex_component = indices_fn.create(om.MFn.kMeshVertComponent)
    indices_fn.addElements(vertex_indices)

    return vertex_component


# --------------------------------------------------------------------------------------
def save_skin_file(mesh, filepath):

    skin_node = maya.mel.eval(
        f"findRelatedSkinCluster {mesh}",
    )

    # -- Get the skin function set from the mesh
    skin_fn = om_anim.MFnSkinCluster(
        utils.get_object(
            skin_node,
        ),
    )

    # # -- Get the vertex count
    vertex_count = mc.polyEvaluate(
        mesh,
        v=True,
    )

    vertex_component = _get_mesh_components(mesh)

    # -- Now get the weight data
    all_weights, influence_count = skin_fn.getWeights(
        utils.dag_path(mesh),
        vertex_component,
    )

    influences = [
        utils.get_name(dag_path.node())
        for dag_path in skin_fn.influenceObjects()
    ]

    influence_weights = list()

    for influence_index in range(influence_count):
        influence_weights.append(
            [
                c for
                c in all_weights[influence_index * vertex_count: (influence_index + 1) * vertex_count]
            ],
        )

    packaged_data = dict(
        influences=influences,
        weights=influence_weights,
        max_influences=mc.getAttr(
            f"{skin_node}.maxInfluences",
        )
    )

    with open(filepath, "w") as f:
        json.dump(
            packaged_data,
            f,
            indent=4,
            sort_keys=True,
        )


# --------------------------------------------------------------------------------------
def load_skin_file(mesh, filepath):

    # -- Ensure we can access the file
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)

    # -- Read the data
    with open(filepath, "r") as f:
        weight_data = json.load(f)

    # # -- Get the vertex count
    vertex_count = mc.polyEvaluate(
        mesh,
        v=True,
    )

    vertex_component = _get_mesh_components(mesh)

    # -- Check that the filepath exists
    # -- Start by removing any existing skin
    existing_skin = maya.mel.eval(
        f"findRelatedSkinCluster {mesh}",
    )

    if existing_skin:
        mc.skinCluster(
            existing_skin,
            geometry=mesh,
            edit=True,
            remove=True
        )

    # -- Create a new skin cluster
    skin_node = mc.skinCluster(
        weight_data["influences"],
        mesh,
        toSelectedBones=True,
        maximumInfluences=weight_data["max_influences"],
        recacheBindMatrices=True,
    )[0]

    # -- Build up the influence list
    influence_indices = om.MIntArray()
    for i in range(len(weight_data["influences"])):
        influence_indices.append(i)

    # -- Build the weight list
    all_weights = om.MDoubleArray()

    for influence_weights in weight_data["weights"]:
        for value in influence_weights:
            all_weights.append(value)

    # -- Now apply the weights
    skin_fn = om_anim.MFnSkinCluster(
        utils.get_object(
            skin_node,
        ),
    )

    skin_fn.setWeights(
        utils.dag_path(mesh),
        vertex_component,
        influence_indices,
        all_weights,
        True,
    )