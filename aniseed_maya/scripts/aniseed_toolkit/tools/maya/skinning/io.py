import os
import json
import maya
import qtility
import aniseed_toolkit
import maya.cmds as mc
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as om_anim


class SaveSkinFile(aniseed_toolkit.Tool):

    identifier = "Save Skin File"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, mesh: str = "", filepath: str = ""):
        """
        This will save the skin weights of the given mesh to the given
        filepath.

        Args:
            mesh: The node to save the skin weights for
            filepath: The location to save the skinweights

        Returns:
            None
        """
        if not mesh:
            mesh = mc.ls(sl=True)[0]

        if not filepath:
            filepath = qtility.request.filepath(
                title="Save Skin File",
            )

        skin_node = maya.mel.eval(
            f"findRelatedSkinCluster {mesh}",
        )

        # -- Get the skin function set from the mesh
        skin_fn = om_anim.MFnSkinCluster(
            aniseed_toolkit.run(
                "Get MObject",
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
            aniseed_toolkit.run("Get DagPath", mesh),
            vertex_component,
        )

        influences = [
            aniseed_toolkit.run("MObject Name", dag_path.node())
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


class LoadSkinFile(aniseed_toolkit.Tool):

    identifier = "Load Skin File"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, mesh="", filepath="") -> str:
        """
        This will load the given skin weights file onto the given mesh. If a skin
        is already applied, it will be removed.

        Args:
            mesh: The node to apply the skin weights to
            filepath: The location to load the skinweights from

        Returns:
            The skinCluster node
        """
        if not mesh:
            mesh = mc.ls(sl=True)[0]

        if not filepath:
            filepath = qtility.request.filepath(
                title="Load Skin File",
                save=False,
            )

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
            aniseed_toolkit.run("Get MObject", skin_node),
        )

        skin_fn.setWeights(
            aniseed_toolkit.run("Get DagPath", mesh),
            vertex_component,
            influence_indices,
            all_weights,
            True,
        )

        return skin_node


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
