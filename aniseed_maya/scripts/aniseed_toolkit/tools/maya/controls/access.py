import aniseed
import aniseed_toolkit
import maya.cmds as mc


class GetRigTool(aniseed_toolkit.Tool):

    identifier = "Get Rig"
    classification = "Animation"
    user_facing = False

    def run(self, node: str = "") -> "aniseed.Rig" or None:
        """
        This will attempt to find the rig for the given node

        Args:
            node: The node to attempt to find the rig for

        Returns:
            node name
        """
        return aniseed_toolkit.rig.get(node)
