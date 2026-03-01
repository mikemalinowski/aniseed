import aniseed
import aniseed_toolkit
import maya.cmds as mc


class GetControls(aniseed_toolkit.Tool):

    identifier = 'Get Controls'
    classification = "Animation"
    user_facing = False

    def run(self):
        """
        This will return the control nodes for all the selected rigs. If no
        rig is selected then all controls in all rigs will be returned.
        """
        return aniseed_toolkit.rig.all_controls()


class ResolveRigNode(aniseed_toolkit.Tool):

    identifier = "Resolve Rig Node"
    classification = "Animation"
    user_facing = False

    def run(self, node: str = "") -> "str":
        """
        This will attempt to find the rig for the given node

        Args:
            node: The node to attempt to find the rig for

        Returns:
            node name
        """
        return aniseed_toolkit.rig.get_rig_node(node)


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


class GetOpposite(aniseed_toolkit.Tool):

    identifier = "Get Opposites"
    classification = "Animation"
    user_facing = False
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, controls: list[str] or None = None) -> list[str]:
        """
        This will return the opposite controls for the given controls

        Args:
            controls: List of controls to get the opposites for. If none are
                given then the selection will be used.
        """
        return aniseed_toolkit.rig.opposing_controls(controls)



class GetByLocation(aniseed_toolkit.Tool):

    identifier = "Get By Location"
    classification = "Animation"
    user_facing = False
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, controls: list[str] or None = None) -> list[str]:
        """
        This will return the opposite controls for the given controls

        Args:
            controls: List of controls to get the opposites for. If none are
                given then the selection will be used.
        """
        return aniseed_toolkit.rig.controls_by_location(
            controls or mc.ls(selection=True)
        )
