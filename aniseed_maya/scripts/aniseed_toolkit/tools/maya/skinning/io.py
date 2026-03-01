import os
import qtility
import aniseed_toolkit
from maya import cmds


class ReadSkinData(aniseed_toolkit.Tool):

    identifier = "Read Skin Data"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, mesh: str = ""):
        """
        This will save the skin weights of the given mesh to the given
        filepath.

        Args:
            mesh: The node to save the skin weights for
            filepath: The location to save the skinweights

        Returns:
            None
        """
        mesh = mesh or cmds.ls(selection=True)[0]
        return aniseed_toolkit.skin.skin_to_dict(mesh)


class SaveSkinFile(aniseed_toolkit.Tool):

    identifier = "Save Skin File"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, meshes: str = "", folderpath: str = ""):
        """
        This will save the skin weights of the given mesh to the given
        filepath.

        Args:
            mesh: The node to save the skin weights for
            filepath: The location to save the skinweights

        Returns:
            None
        """
        if not meshes:
            meshes = cmds.ls(selection=True)

        if not folderpath:
            folderpath = qtility.request.folderpath(
                title="Save Skin Files",
            )

        if not folderpath:
            return

        for mesh in meshes:
            filepath = os.path.join(folderpath, f"{mesh}.skin")
            aniseed_toolkit.skin.save(mesh, filepath)


class ApplySkinData(aniseed_toolkit.Tool):

    identifier = "Apply Skin Data"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]
    def run(self, mesh, weight_data) -> str:
        return aniseed_toolkit.skin.dict_to_skin(mesh, weight_data)


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
            mesh = cmds.ls(selection=True)[0]

        if not filepath:
            filepath = qtility.request.filepath(
                title="Load Skin File",
                save=False,
            )

        # -- Ensure we can access the file
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)

        return aniseed_toolkit.skin.load(mesh, filepath)


class LoadSkinDirectory(aniseed_toolkit.Tool):

    identifier = "Load Skin Directory"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, mesh="", folderpath="") -> str:
        """
        This will load the given skin weights file onto the given mesh. If a skin
        is already applied, it will be removed.

        Args:
            mesh: The node to apply the skin weights to
            filepath: The location to load the skinweights from

        Returns:
            The skinCluster node
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
            mesh_name = filename.split(".")[0]
            filepath = os.path.join(folderpath, filename)
            print("mesh : %s" % mesh_name)
            if cmds.objExists(mesh_name):
                try:
                    aniseed_toolkit.skin.load(mesh_name, filepath)
                except:
                    print(f"did not apply to {mesh_name}")
