import os
import json
from maya import cmds
import maya
from maya import cmds
from maya import mel
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as om_anim

from . import mutils


def copy_skin_to_unbound_meshes(skinned_mesh: str = "", unbound_meshes: list[str] = None) -> None:
    """
    This will copy the skin weights from the skinned_mesh object
    to all the unskinned_meshes.

    Args:
        skinned_mesh: the name of the skinned mesh
        unbound_meshes: A list of meshes you want to copy the skinweights
            to.

    Returns:
         None
    """
    # -- Look for the mesh
    skin = mel.eval(f'findRelatedSkinCluster "{skinned_mesh}";')

    # -- Get all the joints for the skin
    influences = cmds.skinCluster(
        skin,
        query=True,
        influence=True,
    )

    for target in unbound_meshes:
        # -- Create a skin cluster for the given target
        new_skin = cmds.skinCluster(
            influences,
            target,
            toSelectedBones=True,
            maximumInfluences=cmds.skinCluster(
                skin,
                query=True,
                maximumInfluences=True,
            ),
        )[0]

        # -- Copy the skin weights between them
        cmds.copySkinWeights(
            sourceSkin=skin,
            destinationSkin=new_skin,
            noMirror=True,
            surfaceAssociation="closestPoint",
            influenceAssociation=["name", "closestJoint", "label"],
        )

    # -- Keep the source mesh selected
    cmds.select(skinned_mesh)

def disconnect_all_skins() -> None:
    """
    This will disconnect all the skinCluster nodes in the scene. It does not
    remove them, and does not disconnect them.
    """
    for skin in cmds.ls(type="skinCluster"):
        cmds.skinCluster(
            skin,
            edit=True,
            moveJointsMode=True,
        )

def reconnect_all_skins() -> None:
    """
    This will reconnect all skin clusters in the scene which have previously
    been disconnected.
    """
    for skin in cmds.ls(type="skinCluster"):
        cmds.skinCluster(
            skin,
            edit=True,
            moveJointsMode=False,
        )


class LocalisedSkinCopy(object):

    _STORED_MESH = []
    _STORED_VERTICES = []

    @classmethod
    def snapshot_vertices(cls):

        LocalisedSkinCopy._STORED_MESH = cmds.selected(o=True)[0]
        LocalisedSkinCopy._STORED_VERTICES = list()

        for vtx in cmds.selected(flatten=True):
            LocalisedSkinCopy._STORED_VERTICES.append(vtx.index())

    @classmethod
    def copy_skinweights(cls):

        if not cmds.selected():
            print('No mesh to copy weights from')

        if not LocalisedSkinCopy._STORED_MESH:
            print('No mesh to copy to')

        if not LocalisedSkinCopy._STORED_VERTICES:
            print('No vertices to copy to')

        source_mesh = cmds.selected()[0]
        cmds.select(clear=True)

        # -- Duplicate the mesh
        new_mesh = cmds.duplicate(LocalisedSkinCopy._STORED_MESH)[0]

        # -- Copy the skin weights
        copy_skin_to_unbound_meshes(
            skinned_mesh=str(source_mesh),
            unskinned_meshes=[str(new_mesh)],
        )

        # -- Now we need to copy the weights of the stored vertices
        # -- onto the stored mesh
        for vtx_id in LocalisedSkinCopy._STORED_VERTICES:

            cmds.select('%s.vtx[%s]' % (new_mesh, vtx_id))
            mel.CopyVertexWeights()
            mel.artAttrSkinWeightCopy()

            cmds.select('%s.vtx[%s]' % (cls._STORED_MESH, vtx_id))
            mel.PasteVertexWeights()
            mel.artAttrSkinWeightPaste()

        cmds.delete(new_mesh)


class SkinLerper:

    target_a_weights = []
    target_b_weights = []
    destination_vertices = []
    destination_mesh = None

    @classmethod
    def get_interpolated_value(cls, interp, a, b):
        return a + ((b - a) * interp)

    @classmethod
    def set_by_interpolation_factor(cls, interpolation_factor):
        skin = mel.eval(f'findRelatedSkinCluster "{cls.destination_mesh}";')
        influences = cmds.skinCluster(skin, query=True, influence=True)
        interpolated_values = []

        for idx in range(len(SkinLerper.target_a_weights)):
            interpolated_values.append(
                cls.get_interpolated_value(
                    interp=interpolation_factor,
                    a=SkinLerper.target_a_weights[idx],
                    b=SkinLerper.target_b_weights[idx]
                ),
            )

        paired_data = []
        for idx in range(len(interpolated_values)):
            paired_data.append((influences[idx], interpolated_values[idx]))

        for vertex in cls.destination_vertices:
            cmds.skinPercent(
                skin,
                vertex,
                transformValue=paired_data,
            )

    @classmethod
    def set_target_a_weights(cls, vertex):
        mesh = vertex.split(".")[0]
        skin = mel.eval(f'findRelatedSkinCluster "{mesh}";')
        SkinLerper.target_a_weights = cmds.skinPercent(skin, vertex, query=True, value=True)

    @classmethod
    def set_target_b_weights(cls, vertex):
        mesh = vertex.split(".")[0]
        skin = mel.eval(f'findRelatedSkinCluster "{mesh}";')
        SkinLerper.target_b_weights = cmds.skinPercent(skin, vertex, query=True, value=True)

    @classmethod
    def set_destination_vertices(cls, vertices):
        SkinLerper.destination_mesh = vertices[0].split(".")[0]
        SkinLerper.destination_vertices = [n for n in vertices]


def skin_to_dict(mesh: str = "") -> dict:
    """
    This will save the skin weights of the given mesh to the given
    filepath.

    Args:
        mesh: The node to save the skin weights for

    Returns:
        dictionary of skin data
    """
    skin_node = maya.mel.eval(
        f"findRelatedSkinCluster {mesh}",
    )

    # -- Get the skin function set from the mesh
    skin_fn = om_anim.MFnSkinCluster(
        mutils.get_mobject(skin_node)
    )

    # # -- Get the vertex count
    vertex_count = cmds.polyEvaluate(
        mesh,
        vertex=True,
    )
    if isinstance(vertex_count, int):
        vertex_component = _get_mesh_components(mesh)
    else:
        # -- Fall back to surface
        vertex_count = len(cmds.ls(f"{mesh}.cv[*]", flatten=True))
        vertex_component = _get_nurbs_cv_components(mesh)
    # -- Now get the weight data
    all_weights, influence_count = skin_fn.getWeights(
        mutils.get_dagpath(mesh),
        vertex_component,
    )

    influences = [
        mutils.get_name(dag_path.node())
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
        max_influences=cmds.getAttr(
            f"{skin_node}.maxInfluences",
        )
    )

    return packaged_data

def save(mesh: str = "", filepath: str = ""):
    """
    This will save the skin weights of the given mesh to the given
    filepath.

    Args:
        mesh: The node to save the skin weights for
        filepath: The location to save the skinweights

    Returns:
        None
    """
    packaged_data = skin_to_dict(mesh)

    with open(filepath, "w") as f:
        json.dump(
            packaged_data,
            f,
            indent=4,
            sort_keys=True,
        )


def dict_to_skin(mesh, weight_data) -> str:

    # # -- Get the vertex count
    vertex_count = cmds.polyEvaluate(
        mesh,
        vertex=True,
    )
    if isinstance(vertex_count, int):
        vertex_component = _get_mesh_components(mesh)
    else:
        # -- Fall back to surface
        vertex_count = len(cmds.ls(f"{mesh}.cv[*]", flatten=True))
        vertex_component = _get_nurbs_cv_components(mesh)

    # -- Check that the filepath exists
    # -- Start by removing any existing skin
    existing_skin = mel.eval(
        f"findRelatedSkinCluster {mesh}",
    )

    if existing_skin:
        cmds.skinCluster(
            existing_skin,
            geometry=mesh,
            edit=True,
            remove=True
        )

    # -- Create a new skin cluster
    skin_node = cmds.skinCluster(
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
    skin_fn = om_anim.MFnSkinCluster(mutils.get_mobject(skin_node))

    skin_fn.setWeights(
        mutils.get_dagpath(mesh),
        vertex_component,
        influence_indices,
        all_weights,
        True,
    )

    return skin_node


def load(mesh="", filepath="") -> str:
    """
    This will load the given skin weights file onto the given mesh. If a skin
    is already applied, it will be removed.

    Args:
        mesh: The node to apply the skin weights to
        filepath: The location to load the skinweights from

    Returns:
        The skinCluster node
    """
    # -- Ensure we can access the file
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)

    # -- Read the data
    with open(filepath, "r") as f:
        weight_data = json.load(f)

    dict_to_skin(mesh, weight_data)


def _get_mesh_components(mesh):

    # -- Get the vertex count
    vertex_count = cmds.polyEvaluate(
        mesh,
        v=True,
    )

    # -- Build a list of all the vertices
    vertex_indices = [i for i in range(vertex_count)]
    indices_fn = om.MFnSingleIndexedComponent()
    vertex_component = indices_fn.create(om.MFn.kMeshVertComponent)
    indices_fn.addElements(vertex_indices)

    return vertex_component

def _get_nurbs_cv_components(nurbs_surface):
    """
    Returns an MObject representing all CVs of a NURBS surface.

    Args:
        nurbs_surface (str): Name of the NURBS surface.

    Returns:
        MObject: MFnSingleIndexedComponent for all CVs.
    """
    # Get DAG path
    sel = om.MSelectionList()
    sel.add(nurbs_surface)
    dag_path = sel.getDagPath(0)

    # NURBS surface function set
    nurbs_fn = om.MFnNurbsSurface(dag_path)
    num_u = nurbs_fn.numCVsInU
    num_v = nurbs_fn.numCVsInV

    # Create double-indexed component
    comp_fn = om.MFnDoubleIndexedComponent()
    cv_component = comp_fn.create(om.MFn.kSurfaceCVComponent)

    # Add all U,V indices
    for u in range(num_u):
        for v in range(num_v):
            comp_fn.addElement(u, v)

    return cv_component