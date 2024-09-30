import maya.mel
import maya.cmds as mc

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
