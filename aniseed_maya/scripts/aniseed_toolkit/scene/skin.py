"""
Skinning utilities: copying, interpolating, saving and loading skin weights,
and managing skin influences.

Nodes are handled through mref where it is an exact equivalent. The
following deliberately stay outside it:

- Skin clusters are found with Maya's own ``findRelatedSkinCluster`` mel
  procedure, which has a different resolution rule to mref's ``skin()``.
- Vertex and CV work (skinPercent, component strings and the selection of
  components) uses cmds, as mref items wrap nodes and attributes but not
  components.
- Reading and writing whole weight sets uses the OpenMaya
  ``MFnSkinCluster`` api, which does it in a single call per mesh.
"""
import json
import os

from maya import cmds
from maya import mel
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as om_anim
import mref

from ..registry import tool
from ..core import api as _api


def _related_skin(mesh: str) -> str:
    """
    Returns the name of the skinCluster deforming the given mesh, or an
    empty string if there is none.
    """
    return mel.eval(f'findRelatedSkinCluster "{mesh}";')


def copy_skin_to_unbound_meshes(skinned_mesh: str = "", unbound_meshes: list[str] = None) -> None:
    """
    Binds each of the unbound meshes to the influences of the skinned mesh
    (with the same maximum influences) and copies the skin weights onto them,
    matching by closest point and by influence name, closest joint and label.

    The skinned mesh is left selected afterwards.

    Args:
        skinned_mesh: the name of the skinned mesh
        unbound_meshes: A list of meshes you want to copy the skinweights
            to.

    Returns:
         None
    """
    skin = _related_skin(skinned_mesh)

    # -- Get all the joints for the skin
    influences = mref.skinCluster(
        skin,
        query=True,
        influence=True,
    )

    for target in unbound_meshes:
        # -- Create a skin cluster for the given target
        new_skin = mref.skinCluster(
            influences,
            target,
            toSelectedBones=True,
            maximumInfluences=mref.skinCluster(
                skin,
                query=True,
                maximumInfluences=True,
            ),
        )[0]

        # -- Copy the skin weights between them
        mref.copySkinWeights(
            sourceSkin=skin,
            destinationSkin=new_skin,
            noMirror=True,
            surfaceAssociation="closestPoint",
            influenceAssociation=["name", "closestJoint", "label"],
        )

    # -- Keep the source mesh selected
    mref.select(skinned_mesh)


def disconnect_all_skins() -> None:
    """
    Puts every skinCluster in the scene into move joints mode, so the
    influences can be moved without deforming the meshes. The skin clusters
    are not removed. Use reconnect_all_skins to undo this.

    Returns:
        None
    """
    for skin in mref.ls(type="skinCluster"):
        mref.skinCluster(
            skin,
            edit=True,
            moveJointsMode=True,
        )


def reconnect_all_skins() -> None:
    """
    Takes every skinCluster in the scene out of move joints mode (see
    disconnect_all_skins), so the influences deform the meshes again.

    Returns:
        None
    """
    for skin in mref.ls(type="skinCluster"):
        mref.skinCluster(
            skin,
            edit=True,
            moveJointsMode=False,
        )


class LocalisedSkinCopy(object):
    """
    Copies skin weights onto a stored set of vertices, from another skinned
    mesh. This works on the selection:

    1. Select the vertices to copy onto and call snapshot_vertices.
    2. Select the skinned mesh to copy from and call copy_skinweights.
    """

    _STORED_MESH = []
    _STORED_VERTICES = []

    @classmethod
    def snapshot_vertices(cls):
        """
        Stores the object of the first selected component, and the indices
        of all the selected vertices, as the destination for
        copy_skinweights.

        Returns:
            None
        """
        LocalisedSkinCopy._STORED_MESH = cmds.ls(selection=True, o=True)[0]
        LocalisedSkinCopy._STORED_VERTICES = list()

        for vtx in cmds.ls(selection=True, flatten=True):
            LocalisedSkinCopy._STORED_VERTICES.append(vtx.split("[")[-1].split("]")[0])

    @classmethod
    def copy_skinweights(cls):
        """
        Copies the skin weights of the first selected mesh onto the vertices
        stored by snapshot_vertices. The weights are first transferred onto
        a temporary duplicate of the stored mesh, and then copied vertex by
        vertex (using Maya's copy/paste vertex weights) onto the stored mesh.

        A message is printed if there is nothing selected or nothing stored,
        but the copy is still attempted.

        Returns:
            None
        """
        if not cmds.ls(selection=True):
            print('No mesh to copy weights from')

        if not LocalisedSkinCopy._STORED_MESH:
            print('No mesh to copy to')

        if not LocalisedSkinCopy._STORED_VERTICES:
            print('No vertices to copy to')

        source_mesh = cmds.ls(selection=True)[0]
        cmds.select(clear=True)

        # -- Duplicate the mesh
        new_mesh = cmds.duplicate(LocalisedSkinCopy._STORED_MESH)[0]

        # -- Copy the skin weights
        copy_skin_to_unbound_meshes(
            skinned_mesh=str(source_mesh),
            unbound_meshes=[str(new_mesh)],
        )

        # -- Now we need to copy the weights of the stored vertices
        # -- onto the stored mesh
        for vtx_id in LocalisedSkinCopy._STORED_VERTICES:

            cmds.select('%s.vtx[%s]' % (new_mesh, vtx_id))
            mel.eval("CopyVertexWeights;")
            mel.eval("artAttrSkinWeightCopy;")

            cmds.select('%s.vtx[%s]' % (cls._STORED_MESH, vtx_id))
            mel.eval("PasteVertexWeights;")
            mel.eval("artAttrSkinWeightPaste;")

        cmds.delete(new_mesh)


_WEIGHT_VALUE_COPY_DESTINATION = None


def declare_weight_value_copy_destination() -> None:
    """
    Stores the currently selected mesh as the destination for a subsequent
    call to :func:`copy_weight_values_to_destination`. A message is printed
    (and nothing stored) if nothing is selected.

    Returns:
        None
    """
    global _WEIGHT_VALUE_COPY_DESTINATION

    selection = cmds.ls(selection=True, o=True)

    if not selection:
        print("No mesh selected to declare as destination")
        return

    _WEIGHT_VALUE_COPY_DESTINATION = selection[0]


def copy_weight_values_to_destination(vertices: list[str] = None) -> None:
    """
    Reads the skin weights of the given (or selected) vertices and copies
    them onto the vertices of the destination mesh at matching vertex
    indices. Any influences present on the source that are missing on the
    destination skin cluster will be added.

    The destination mesh must be declared first via
    :func:`declare_weight_value_copy_destination`. A message is printed (and
    nothing changed) if there is no destination, no vertices, or either mesh
    has no skin cluster.

    Args:
        vertices: The source vertices to copy weights from. If not given
            the current selection is used.

    Returns:
        None
    """
    if not _WEIGHT_VALUE_COPY_DESTINATION:
        print(
            "No destination mesh declared. "
            "Call declare_weight_value_copy_destination first."
        )
        return

    if not vertices:
        vertices = cmds.ls(selection=True, flatten=True) or []

    if not vertices:
        print("No source vertices given or selected")
        return

    source_mesh = vertices[0].split(".")[0]
    source_skin = _related_skin(source_mesh)

    if not source_skin:
        print(f"Source mesh {source_mesh} has no skin cluster")
        return

    destination_mesh = _WEIGHT_VALUE_COPY_DESTINATION
    destination_skin = _related_skin(destination_mesh)

    if not destination_skin:
        print(f"Destination mesh {destination_mesh} has no skin cluster")
        return

    # -- Influence names stay cmds strings, as they are compared by name and
    # -- paired with the weight values for skinPercent.
    source_influences = cmds.skinCluster(
        source_skin,
        query=True,
        influence=True,
    ) or []

    destination_influences = set(
        cmds.skinCluster(destination_skin, query=True, influence=True) or []
    )

    for vertex in vertices:
        vertex_index = vertex.split("[")[-1].split("]")[0]

        source_values = cmds.skinPercent(
            source_skin,
            vertex,
            query=True,
            value=True,
        ) or []

        # -- Add any influences the destination skin is missing
        for influence in source_influences:
            if influence in destination_influences:
                continue
            cmds.skinCluster(
                destination_skin,
                edit=True,
                addInfluence=influence,
                weight=0.0,
            )
            destination_influences.add(influence)

        paired_data = list(zip(source_influences, source_values))
        destination_vertex = f"{destination_mesh}.vtx[{vertex_index}]"

        cmds.skinPercent(
            destination_skin,
            destination_vertex,
            transformValue=paired_data,
        )


class SkinLerper:
    """
    Sets the skin weights of a set of vertices to an interpolation between
    the weights of two other vertices (target a and target b) of the same
    skin. Set the targets and destination vertices first, then call
    set_by_interpolation_factor.
    """

    target_a_weights = []
    target_b_weights = []
    destination_vertices = []
    destination_mesh = None

    @classmethod
    def get_interpolated_value(cls, interp, a, b):
        """
        Returns the linear interpolation between a and b.

        Args:
            interp: The interpolation factor, where 0 gives a and 1 gives b
            a: The value at an interpolation factor of 0
            b: The value at an interpolation factor of 1

        Returns:
            float
        """
        return a + ((b - a) * interp)

    @classmethod
    def set_by_interpolation_factor(cls, interpolation_factor):
        """
        Sets the weights of every destination vertex to the interpolation
        between the target a and target b weights. The weights are paired
        with the destination skin's influences by index.

        Args:
            interpolation_factor: Where 0 gives the target a weights and 1
                gives the target b weights

        Returns:
            None
        """
        skin = _related_skin(cls.destination_mesh)
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
        """
        Stores the skin weights of the given vertex as the target a weights.

        Args:
            vertex: The vertex (e.g. "mesh.vtx[0]") to read the weights from

        Returns:
            None
        """
        mesh = vertex.split(".")[0]
        skin = _related_skin(mesh)
        SkinLerper.target_a_weights = cmds.skinPercent(skin, vertex, query=True, value=True)

    @classmethod
    def set_target_b_weights(cls, vertex):
        """
        Stores the skin weights of the given vertex as the target b weights.

        Args:
            vertex: The vertex (e.g. "mesh.vtx[0]") to read the weights from

        Returns:
            None
        """
        mesh = vertex.split(".")[0]
        skin = _related_skin(mesh)
        SkinLerper.target_b_weights = cmds.skinPercent(skin, vertex, query=True, value=True)

    @classmethod
    def set_destination_vertices(cls, vertices):
        """
        Stores the vertices whose weights set_by_interpolation_factor will
        set. They must all belong to the same mesh.

        Args:
            vertices: List of vertices (e.g. "mesh.vtx[0]")

        Returns:
            None
        """
        SkinLerper.destination_mesh = vertices[0].split(".")[0]
        SkinLerper.destination_vertices = list(vertices)


def _vertex_count_and_components(mesh):
    """
    Returns the number of skinnable components of the given mesh or nurbs
    surface, and an MObject for all of them.
    """
    vertex_count = cmds.polyEvaluate(
        mesh,
        vertex=True,
    )

    # -- polyEvaluate returns a message string rather than a count for
    # -- anything which is not a polygon mesh
    if isinstance(vertex_count, int):
        return vertex_count, _get_mesh_components(mesh)

    # -- Fall back to surface
    vertex_count = len(cmds.ls(f"{mesh}.cv[*]", flatten=True))
    return vertex_count, _get_nurbs_cv_components(mesh)


def skin_to_dict(mesh: str = "") -> dict:
    """
    Reads the skin weights of the given mesh (or nurbs surface) into a json
    serialisable dictionary.

    Args:
        mesh: The node to read the skin weights from

    Returns:
        dictionary of the form {"influences": [...], "weights": [...],
        "max_influences": int}, where weights holds one list of per-vertex
        weights for each influence
    """
    skin_node = mel.eval(
        f"findRelatedSkinCluster {mesh}",
    )

    # -- The MFnSkinCluster api reads every weight in one call
    skin_fn = om_anim.MFnSkinCluster(
        _api.get_mobject(skin_node)
    )

    vertex_count, vertex_component = _vertex_count_and_components(mesh)

    # -- Now get the weight data
    all_weights, influence_count = skin_fn.getWeights(
        _api.get_dagpath(mesh),
        vertex_component,
    )

    influences = [
        _api.get_name(dag_path.node())
        for dag_path in skin_fn.influenceObjects()
    ]

    # -- MFnSkinCluster.getWeights returns a flat component-major
    # -- array: [v0_inf0, v0_inf1, ..., v1_inf0, v1_inf1, ...].
    # -- Slice it back into per-influence lists.
    influence_weights = [
        [
            all_weights[c * influence_count + i]
            for c in range(vertex_count)
        ]
        for i in range(influence_count)
    ]

    packaged_data = dict(
        influences=influences,
        weights=influence_weights,
        max_influences=mref.get(skin_node).attr("maxInfluences").get(),
    )

    return packaged_data


def save(mesh: str = "", filepath: str = ""):
    """
    This will save the skin weights of the given mesh (see skin_to_dict) to
    the given filepath as json.

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


@tool(
    "Apply Skin Data",
    classification="Rigging",
    categories=["Skinning"],
)
def dict_to_skin(mesh, weight_data) -> str:
    """
    Skins the given mesh (or nurbs surface) with the given skin data, as
    returned by skin_to_dict. Any existing skin on the mesh is removed first,
    then a new skinCluster is bound to the influences in the data and the
    weights are applied (normalised).

    Args:
        mesh: The node to apply the skin to
        weight_data: Dictionary of skin data (influences, weights and
            max_influences)

    Returns:
        The name of the new skinCluster node
    """
    vertex_count, vertex_component = _vertex_count_and_components(mesh)

    # -- Start by removing any existing skin
    existing_skin = mel.eval(
        f"findRelatedSkinCluster {mesh}",
    )

    if existing_skin:
        mref.skinCluster(
            existing_skin,
            geometry=mesh,
            edit=True,
            remove=True
        )

    # -- Create a new skin cluster
    skin_node = mref.skinCluster(
        weight_data["influences"],
        mesh,
        toSelectedBones=True,
        maximumInfluences=weight_data["max_influences"],
        recacheBindMatrices=True,
    )[0]

    # -- The new skin's influences are in the same order as the data's
    num_influences = len(weight_data["influences"])
    influence_indices = om.MIntArray(list(range(num_influences)))

    # -- Build the weight list in component-major layout, matching
    # -- what MFnSkinCluster.setWeights expects:
    # -- [v0_inf0, v0_inf1, ..., v1_inf0, v1_inf1, ...].
    all_weights = om.MDoubleArray()
    for c in range(vertex_count):
        for i in range(num_influences):
            all_weights.append(weight_data["weights"][i][c])

    # -- Now apply the weights, in one call through the api
    skin_fn = om_anim.MFnSkinCluster(skin_node.pointer())

    skin_fn.setWeights(
        _api.get_dagpath(mesh),
        vertex_component,
        influence_indices,
        all_weights,
        True,
    )

    return skin_node.name()


def load(mesh="", filepath="") -> str:
    """
    This will load the given skin weights file onto the given mesh. If a skin
    is already applied, it will be removed.

    Args:
        mesh: The node to apply the skin weights to
        filepath: The location to load the skinweights from

    Returns:
        The name of the skinCluster node

    Raises:
        FileNotFoundError: If the filepath does not exist
    """
    # -- Ensure we can access the file
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)

    # -- Read the data
    with open(filepath, "r") as f:
        weight_data = json.load(f)

    return dict_to_skin(mesh, weight_data)


def _get_mesh_components(mesh):
    """
    Returns an MObject representing all the vertices of a polygon mesh.
    """
    vertex_count = cmds.polyEvaluate(
        mesh,
        v=True,
    )

    indices_fn = om.MFnSingleIndexedComponent()
    vertex_component = indices_fn.create(om.MFn.kMeshVertComponent)
    indices_fn.addElements(list(range(vertex_count)))

    return vertex_component


def _get_nurbs_cv_components(nurbs_surface):
    """
    Returns an MObject representing all CVs of a NURBS surface.

    Args:
        nurbs_surface (str): Name of the NURBS surface.

    Returns:
        MObject: MFnDoubleIndexedComponent for all CVs.
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


def add_all_skin_joints_to_all_skins():
    """
    Adds every influence of every skinCluster in the scene to every
    skinCluster in the scene. The influences are added with zero weight
    (locked while being added) and their lock weights state is restored
    afterwards. Influences which cannot be added are skipped.

    Returns:
        None
    """
    # -- Get a list of all the skin clusters in the scene
    all_skins = mref.ls(type="skinCluster")

    # -- We need to find all the joints driving any of the skins
    all_skin_joints = []
    for skin in all_skins:
        all_skin_joints.extend(skin.influences())
    all_skin_joints = list(set(all_skin_joints))

    # -- Store the lock weights setting of each joint, so we can restore it
    lock_weight_values = dict()
    for joint in all_skin_joints:
        lock_weight_values[joint] = joint.attr("liw").get()

    # -- Now ensure all of those joints are part of all
    # -- of the skins
    for skin in all_skins:
        for joint in all_skin_joints:
            try:
                skin.add_influence(joint, lockWeights=True)
            except Exception:
                pass

    # -- Now restore the lock weights
    for joint, lock_value in lock_weight_values.items():
        joint.attr("liw").set(lock_value)


def add_all_skin_joints_to_target_meshes(meshes):
    """
    Takes the skinClusters deforming the given meshes and adds every
    influence of any of them to all of them. Only skinClusters whose
    (first) deformed shape is the first shape of one of the meshes are
    considered. The influences have their weights locked while being added
    (so they come in with zero weight) and their lock weights state is
    restored afterwards. Influences which cannot be added are skipped.

    Args:
        meshes: List of mesh transforms (names or mref items)

    Returns:
        None
    """
    meshes = mref.get(
        [
            mref.get(mesh).shape()
            for mesh in meshes
        ]
    )

    # -- Get a list of all the skin clusters in the scene
    all_skins = mref.ls(type="skinCluster")
    skins_to_process = []

    # -- We need to find all the joints driving any of the skins
    all_skin_joints = []
    for skin in all_skins:
        if skin.shape() in meshes:
            skins_to_process.append(skin)
            all_skin_joints.extend(skin.influences())
    all_skin_joints = list(set(all_skin_joints))

    # -- Store the lock weights setting of each joint, so we can restore it
    lock_weight_values = dict()
    for joint in all_skin_joints:
        lock_weight_values[joint] = joint.attr("liw").get()
        joint.attr("liw").set(1)

    # -- Now ensure all of those joints are part of all
    # -- of the skins
    for skin in skins_to_process:
        for joint in all_skin_joints:
            try:
                skin.add_influence(joint, lockWeights=True)
            except Exception:
                pass

    # -- Now restore the lock weights
    for joint, lock_value in lock_weight_values.items():
        joint.attr("liw").set(lock_value)
