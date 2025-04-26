import aniseed_toolkit
import maya.cmds as mc


class DisconnectAllSkinsTool(aniseed_toolkit.Tool):

    identifier = "Disconnect All Skins"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self) -> None:
        """
        This will disconnect all the skinCluster nodes in the scene. It does not
        remove them, and does not disconnect them.
        """
        for skin in mc.ls(type="skinCluster"):
            mc.skinCluster(
                skin,
                edit=True,
                moveJointsMode=True,
            )


class ReconnectAllSkinsTool(aniseed_toolkit.Tool):

    identifier = "Reconnect All Skins"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self) -> None:
        """
        This will reconnect all skin clusters in the scene which have previously
        been disconnected.
        """
        for skin in mc.ls(type="skinCluster"):
            mc.skinCluster(
                skin,
                edit=True,
                moveJointsMode=False,
            )
