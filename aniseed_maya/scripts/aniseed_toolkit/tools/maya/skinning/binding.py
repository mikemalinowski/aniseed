import aniseed_toolkit
import maya
import maya.cmds as mc


class CopySkinToUnskinnedMeshes(aniseed_toolkit.Tool):

    identifier = "Copy Skin To Unskinned Meshes"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, skinned_mesh: str = "", unbound_meshes: list[str] = None) -> None:
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
        # -- If we are not given our inputs, then resolve them from the
        # -- current selection
        skinned_mesh = skinned_mesh or mc.ls(sl=True)[0]
        unbound_meshes = unbound_meshes or mc.ls(sl=True)[1:]

        if not isinstance(unbound_meshes, list):
            unbound_meshes = [unbound_meshes]

        aniseed_toolkit.skin.copy_skin_to_unbound_meshes(
            skinned_mesh=skinned_mesh,
            unbound_meshes=unbound_meshes,
        )
