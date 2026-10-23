import aniseed_toolkit


class DisconnectAllSkinsTool(aniseed_toolkit.Tool):

    identifier = "Disconnect All Skins"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self) -> None:
        """
        This will disconnect all the skinCluster nodes in the scene (putting
        them into move joints mode), so the influences can be moved without
        deforming the meshes. It does not delete them.
        """
        aniseed_toolkit.scene.skin.disconnect_all_skins()


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
        aniseed_toolkit.scene.skin.reconnect_all_skins()
