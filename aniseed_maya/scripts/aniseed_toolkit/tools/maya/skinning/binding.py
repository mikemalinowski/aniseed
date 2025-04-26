import aniseed_toolkit
import maya
import maya.cmds as mc


class CopySkinToUnskinnedMeshes(aniseed_toolkit.Tool):

    identifier = "Copy Skin To Unskinned Meshes"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, skinned_mesh: str = "", unskinned_meshes: list[str] = None) -> None:
        """
        This will copy the skin weights from the skinned_mesh object
        to all the unskinned_meshes.

        Args:
            skinned_mesh: the name of the skinned mesh
            unskinned_meshes: A list of meshes you want to copy the skinweights
                to.

        Returns:
             None
        """
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
