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


@aniseed_toolkit.tool(
    "Get By Location",
    classification="Animation",
    categories=["Selection", "Controls"],
    user_facing=False,
)
def get_by_location(controls: list[str] or None = None) -> list[str]:
    """
    This will return the opposite controls for the given controls

    Args:
        controls: List of controls to get the opposites for. If none are
            given then the selection will be used.
    """
    return aniseed_toolkit.rig.controls.controls_by_location(
        controls or mc.ls(selection=True)
    )
