import aniseed
import aniseed_toolkit
from maya import cmds


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
            The aniseed.Rig the node belongs to, or None
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
    This will return every rig control which shares the location (side) of
    the first of the given controls

    Args:
        controls: List of controls, of which the first defines the location.
            If none are given then the selection will be used.
    """
    return aniseed_toolkit.rig.controls.controls_by_location(
        controls or cmds.ls(selection=True)
    )
