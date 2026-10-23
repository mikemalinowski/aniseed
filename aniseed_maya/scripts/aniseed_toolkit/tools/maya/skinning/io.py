import os
import logging
import qtility
import aniseed_toolkit
from maya import cmds

log = logging.getLogger(__name__)


def _skin_filename(mesh: str) -> str:
    """
    Returns the skin file name for the given mesh: its name without any DAG
    path or namespace. A ":" in a file name writes an NTFS alternate data
    stream, and a "|" is not valid in a file name at all.
    """
    return mesh.split("|")[-1].split(":")[-1] + ".skin"


class ReadSkinData(aniseed_toolkit.Tool):

    identifier = "Read Skin Data"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, mesh: str = ""):
        """
        This will return the skin weights of the given mesh as a dictionary.

        Args:
            mesh: The node to read the skin weights from. If not given, the
                first selected node is used.

        Returns:
            Dictionary of the skin data
        """
        mesh = mesh or next(iter(cmds.ls(selection=True)), "")

        if not mesh:
            log.warning("Give or select the mesh to read the skin weights from")
            return None

        return aniseed_toolkit.scene.skin.skin_to_dict(mesh)


class SaveSkinFile(aniseed_toolkit.Tool):

    identifier = "Save Skin File"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, meshes: list[str] or str = "", folderpath: str = ""):
        """
        This will save the skin weights of each of the given meshes to a
        <mesh name>.skin file in the given folder. The file is named after
        the mesh without its namespace or DAG path.

        Args:
            meshes: The mesh (or list of meshes) to save the skin weights for.
                If not given, the selection is used.
            folderpath: The folder to save the skin files in

        Returns:
            None
        """
        if not meshes:
            meshes = cmds.ls(selection=True)

        if isinstance(meshes, str):
            meshes = [meshes]

        if not meshes:
            log.warning("Give or select the meshes to save the skin weights of")
            return

        if not folderpath:
            folderpath = qtility.request.folderpath(
                title="Save Skin Files",
            )

        if not folderpath:
            return

        written = dict()

        for mesh in meshes:
            filename = _skin_filename(mesh)

            if filename in written:
                log.warning(
                    f"{mesh} and {written[filename]} share the skin file name {filename}, "
                    f"so the skin of {mesh} replaces it"
                )
            written[filename] = mesh

            aniseed_toolkit.scene.skin.save(mesh, os.path.join(folderpath, filename))


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
            mesh = next(iter(cmds.ls(selection=True)), "")

        if not mesh:
            log.warning("Give or select the mesh to load the skin weights onto")
            return None

        if not filepath:
            filepath = qtility.request.filepath(
                title="Load Skin File",
                save=False,
            )

        if not filepath:
            return None

        # -- Ensure we can access the file
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)

        return aniseed_toolkit.scene.skin.load(mesh, filepath)


class LoadSkinDirectory(aniseed_toolkit.Tool):

    identifier = "Load Skin Directory"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, mesh="", folderpath="") -> str:
        """
        This will load every .skin file in the given folder onto the mesh it
        is named after. A mesh with that name in a namespace is used if there
        is no mesh with the exact name. If a skin is already applied, it will
        be removed.

        Args:
            mesh: Unused
            folderpath: The folder to load the skin files from

        Returns:
            None
        """
        if not folderpath:
            folderpath = qtility.request.folderpath(
                title="Load Skin Directory",
            )

        if not folderpath:
            return

        # -- Ensure we can access the file
        if not os.path.exists(folderpath):
            raise FileNotFoundError(folderpath)

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
                aniseed_toolkit.scene.skin.load(targets[0], filepath)

            except Exception:
                log.exception(f"Could not apply {filepath} to {targets[0]}")
