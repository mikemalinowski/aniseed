"""
Rigging Toolkit tools for skinning: binding and copying skins, copying and
interpolating skin weights, saving and loading skin files, and disconnecting
skins so their joints can be moved.
"""
import os
import logging

from maya import cmds

import aniseed
import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)


def _requires_selection(message: str) -> bool:
    if not cmds.ls(selection=True):
        log.warning(message)
        return False

    return True


def _skin_filename(mesh: str) -> str:
    """
    Returns the skin file name for the given mesh: its name without any DAG
    path or namespace. A ":" in a file name writes an NTFS alternate data
    stream, and a "|" is not valid in a file name at all.
    """
    return mesh.split("|")[-1].split(":")[-1] + ".skin"


def _requires_folder(folderpath: str, purpose: str) -> bool:
    if not folderpath:
        log.warning(f"Set the Folderpath to {purpose}")
        return False

    if not os.path.isdir(folderpath):
        log.warning(f"The Folderpath does not exist: {folderpath}")
        return False

    return True


# --------------------------------------------------------------------------------------
class CopySkinToUnskinnedMeshes(toolkits.Tool):
    """
    Skins the unskinned meshes to the joints of a skinned mesh and copies its
    skin weights onto them (by closest point, matching joints by name,
    closest joint and label). Select the skinned mesh first and then the
    meshes to copy onto. Give a Skinned Mesh to copy from that mesh instead
    of the first selected one (every selected mesh after the first is still
    copied onto).
    """

    identifier = "Copy Skin To Unskinned Meshes"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Skinned Mesh",
            value="",
            description="The skinned mesh to copy from, used instead of the first selected mesh when given",
        )

    def option_widget(self, option_name: str):
        if option_name == "Skinned Mesh":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        # -- The meshes to copy onto are always the selection after the first
        if not cmds.ls(selection=True)[1:]:
            log.warning("Select the skinned mesh, then the meshes to copy its skin onto")
            return False

        return True

    def run(self) -> None:
        selection = cmds.ls(selection=True)

        au.scene.skin.copy_skin_to_unbound_meshes(
            skinned_mesh=self.option("Skinned Mesh").get() or selection[0],
            unbound_meshes=selection[1:],
        )


# --------------------------------------------------------------------------------------
class AddAllSkinJointsToAllSkins(toolkits.Tool):
    """
    Adds every joint used by any skin in the scene to every skin in the
    scene. The joints are added with zero weight, so the meshes do not
    change.
    """

    identifier = "Add All Skins Joints to All Skins"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def run(self) -> None:
        au.scene.skin.add_all_skin_joints_to_all_skins()


# --------------------------------------------------------------------------------------
class AddAllSkinJointsToSelectedSkins(toolkits.Tool):
    """
    Adds every joint used by the skins of the selected meshes to all of
    those skins. The joints are added with zero weight, so the meshes do not
    change.
    """

    identifier = "Add All Skins Joints to Selected Meshes"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the skinned meshes to share their joints between")

    def run(self) -> None:
        au.scene.skin.add_all_skin_joints_to_target_meshes(
            cmds.ls(selection=True),
        )


# --------------------------------------------------------------------------------------
class DisconnectAllSkinsTool(toolkits.Tool):
    """
    Puts every skin in the scene into move joints mode, so the joints can be
    moved without deforming the meshes. The skins are not removed: use
    Reconnect All Skins to make them deform the meshes again.
    """

    identifier = "Disconnect All Skins"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def run(self) -> None:
        au.scene.skin.disconnect_all_skins()


# --------------------------------------------------------------------------------------
class ReconnectAllSkinsTool(toolkits.Tool):
    """
    Takes every skin in the scene out of move joints mode (see Disconnect
    All Skins), so the joints deform the meshes again.
    """

    identifier = "Reconnect All Skins"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def run(self) -> None:
        au.scene.skin.reconnect_all_skins()


# --------------------------------------------------------------------------------------
class SnapshotCopyDestination(toolkits.Tool):
    """
    Remembers the selected vertices as the ones to copy skin weights onto
    with Localised Copy : Copy. Only these vertices are changed by it.
    """

    identifier = "Localised Copy : Snapshot Destination"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the vertices to copy skin weights onto")

    def run(self) -> None:
        localised_copy = au.scene.skin.LocalisedSkinCopy
        localised_copy.snapshot_vertices()

        log.info(
            f"Stored {len(localised_copy._STORED_VERTICES)} destination vertices "
            f"of {localised_copy._STORED_MESH}"
        )


# --------------------------------------------------------------------------------------
class CopyLocalised(toolkits.Tool):
    """
    Copies the skin weights of the selected skinned mesh onto the vertices
    remembered by Localised Copy : Snapshot Destination. No other vertices
    are changed. The two meshes must be skinned to the same joints.
    """

    identifier = "Localised Copy : Copy"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def is_valid(self) -> bool:
        # -- The library keeps the snapshot (see LocalisedSkinCopy)
        localised_copy = au.scene.skin.LocalisedSkinCopy

        if not localised_copy._STORED_MESH or not localised_copy._STORED_VERTICES:
            log.warning("Store the vertices to copy onto with Localised Copy : Snapshot Destination first")
            return False

        return _requires_selection("Select the skinned mesh to copy the skin weights from")

    def run(self) -> None:
        localised_copy = au.scene.skin.LocalisedSkinCopy
        localised_copy.copy_skinweights()

        log.info(f"Skin weights copied to the stored vertices of {localised_copy._STORED_MESH}")


# --------------------------------------------------------------------------------------
class CopySkinWeightsToMemory(toolkits.Tool):
    """
    Remembers the skin weights of the selected mesh (or of Mesh, if given),
    ready to be applied with Paste Skin Weights To Matching Vertices.
    """

    identifier = "Copy Skin Weights To Memory"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Mesh",
            value="",
            description="The skinned mesh to copy from, used instead of the selection when given",
        )

    def option_widget(self, option_name: str):
        if option_name == "Mesh":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        if not self.option("Mesh").get() and not cmds.ls(selection=True, objectsOnly=True):
            log.warning("Select a skinned mesh to copy the skin weights from")
            return False

        return True

    def run(self) -> None or bool:
        mesh = self.option("Mesh").get() or cmds.ls(selection=True, objectsOnly=True)[0]

        # -- The library keeps the copied weights, for
        # -- paste_skin_to_matching_vertices
        try:
            data = au.scene.skin.copy_skin_to_memory(mesh)

        except ValueError as error:
            log.warning(str(error))
            return False

        vertex_count = len(data["weights"][0]) if data["weights"] else 0
        log.info(
            f"Copied skin weights to memory: {vertex_count} vertices, "
            f"{len(data['influences'])} influences"
        )


# --------------------------------------------------------------------------------------
class PasteSkinWeightsToMatchingVertices(toolkits.Tool):
    """
    Pastes the skin weights remembered by Copy Skin Weights To Memory onto
    the selected vertices (or every vertex of a selected mesh). Each vertex
    takes the weights of the copied vertex with the same id. A mesh which is
    not skinned is skinned to the copied joints first.
    """

    identifier = "Paste Skin Weights To Matching Vertices"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the vertices (or mesh) to paste the skin weights onto")

    def run(self) -> None or bool:
        # -- This raises a ValueError (reported as a warning) if nothing has
        # -- been copied with Copy Skin Weights To Memory
        try:
            result = au.scene.skin.paste_skin_to_matching_vertices(
                cmds.ls(selection=True, flatten=True),
            )

        except ValueError as error:
            log.warning(str(error))
            return False

        if result["skipped"]:
            log.warning(
                f"{len(result['skipped'])} vertices have no matching id in the "
                f"copied data and were skipped"
            )

        log.info(f"Pasted skin weights onto {result['pasted']} vertices of {result['mesh']}")


# --------------------------------------------------------------------------------------
class SkinInterpSetTargetAWeights(toolkits.Tool):
    """
    Remembers the skin weights of the selected vertex as the A weights for
    Interp : Apply Interpolation.
    """

    identifier = "Interp : Set Target A Weights"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the vertex to read the A weights from")

    def run(self) -> None:
        au.scene.skin.SkinLerper.set_target_a_weights(cmds.ls(selection=True)[0])


# --------------------------------------------------------------------------------------
class SkinInterpSetTargetBWeights(toolkits.Tool):
    """
    Remembers the skin weights of the selected vertex as the B weights for
    Interp : Apply Interpolation.
    """

    identifier = "Interp : Set Target B Weights"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the vertex to read the B weights from")

    def run(self) -> None:
        au.scene.skin.SkinLerper.set_target_b_weights(cmds.ls(selection=True)[0])


# --------------------------------------------------------------------------------------
class SkinInterpApply(toolkits.Tool):
    """
    Sets the skin weights of the selected vertices to a blend of the weights
    remembered by Interp : Set Target A Weights and Interp : Set Target B
    Weights. An Interpolation Factor of 0 gives the A weights, 1 gives the B
    weights. The vertices must be on the same skin as the targets.
    """

    identifier = "Interp : Apply Interpolation"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Interpolation Factor",
            value=0.5,
            description="The blend between the A weights (0) and the B weights (1)",
        )

    def is_valid(self) -> bool:
        lerper = au.scene.skin.SkinLerper

        if not lerper.target_a_weights or not lerper.target_b_weights:
            log.warning("Set the A and B weights with Interp : Set Target A / B Weights first")
            return False

        return _requires_selection("Select the vertices to set the weights of")

    def run(self) -> None:
        lerper = au.scene.skin.SkinLerper
        lerper.set_destination_vertices(cmds.ls(selection=True, flatten=True))
        lerper.set_by_interpolation_factor(self.option("Interpolation Factor").get())


# --------------------------------------------------------------------------------------
class SaveSkinFile(toolkits.Tool):
    """
    Saves the skin weights of each selected mesh (or of Meshes, if given) to
    a <mesh name>.skin file in the Folderpath folder. The file is named
    after the mesh without its namespace or DAG path.
    """

    identifier = "Save Skin File"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Meshes",
            value="",
            description="The mesh to save the skin weights of, used instead of the selection when given",
        )

        self.declare_option(
            name="Folderpath",
            value="",
            description="The folder to save the skin files in",
        )

    def option_widget(self, option_name: str):
        if option_name == "Meshes":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def _meshes(self) -> list:
        meshes = self.option("Meshes").get() or cmds.ls(selection=True)

        if isinstance(meshes, str):
            meshes = [meshes]

        return meshes

    def is_valid(self) -> bool:
        if not self._meshes():
            log.warning("Give or select the meshes to save the skin weights of")
            return False

        return _requires_folder(self.option("Folderpath").get(), "save the skin files in")

    def run(self) -> None:
        folderpath = self.option("Folderpath").get()
        written = dict()

        for mesh in self._meshes():
            filename = _skin_filename(mesh)

            if filename in written:
                log.warning(
                    f"{mesh} and {written[filename]} share the skin file name {filename}, "
                    f"so the skin of {mesh} replaces it"
                )
            written[filename] = mesh

            au.scene.skin.save(mesh, os.path.join(folderpath, filename))

        log.info(f"Saved {len(written)} skin files to {folderpath}")


# --------------------------------------------------------------------------------------
class LoadSkinFile(toolkits.Tool):
    """
    Loads the skin file at Filepath onto the selected mesh (or onto Mesh, if
    given). Any skin the mesh already has is removed first.
    """

    identifier = "Load Skin File"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Mesh",
            value="",
            description="The mesh to load the skin onto, used instead of the selection when given",
        )

        self.declare_option(
            name="Filepath",
            value="",
            description="The skin file to load",
        )

    def option_widget(self, option_name: str):
        if option_name == "Mesh":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        if option_name == "Filepath":
            return aniseed.widgets.FilepathSelector(
                self.option(option_name).get(),
                filter_="*.skin (*.skin)",
                save=False,
                title="Load Skin File",
            )

        return None

    def is_valid(self) -> bool:
        if not self.option("Mesh").get() and not cmds.ls(selection=True):
            log.warning("Give or select the mesh to load the skin weights onto")
            return False

        filepath = self.option("Filepath").get()

        if not filepath:
            log.warning("Set the Filepath of the skin file to load")
            return False

        if not os.path.exists(filepath):
            log.warning(f"The skin file does not exist: {filepath}")
            return False

        return True

    def run(self) -> None:
        mesh = self.option("Mesh").get() or cmds.ls(selection=True)[0]

        skin = au.scene.skin.load(mesh, self.option("Filepath").get())
        log.info(f"Loaded the skin onto {mesh}: {skin}")


# --------------------------------------------------------------------------------------
class LoadSkinDirectory(toolkits.Tool):
    """
    Loads every .skin file in the Folderpath folder onto the mesh it is
    named after. A mesh of that name in a namespace is used if there is no
    mesh with the exact name, and files matching more than one mesh are
    skipped. Any skin a mesh already has is removed first.
    """

    identifier = "Load Skin Directory"
    toolkit = "Rigging"
    categories = ["Skinning"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Folderpath",
            value="",
            description="The folder to load the skin files from",
        )

    def is_valid(self) -> bool:
        return _requires_folder(self.option("Folderpath").get(), "load the skin files from")

    def run(self) -> None:
        folderpath = self.option("Folderpath").get()

        for filename in os.listdir(folderpath):

            if not filename.endswith(".skin"):
                continue

            mesh_name = filename.split(".")[0]
            filepath = os.path.join(folderpath, filename)

            targets = cmds.ls(mesh_name) or cmds.ls(f"*:{mesh_name}")

            if not targets:
                continue

            if len(targets) > 1:
                log.warning(
                    f"Skipped {filename}, as more than one node is called {mesh_name}: {targets}"
                )
                continue

            try:
                au.scene.skin.load(targets[0], filepath)

            except Exception:
                log.exception(f"Could not apply {filepath} to {targets[0]}")
