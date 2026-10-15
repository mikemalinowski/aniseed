import aniseed_toolkit
import maya.cmds as mc


class IsPinnedTool(aniseed_toolkit.Tool):

    identifier = "Is Pinned"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Pinning",
    ]

    def run(self, joint: str = None) -> bool:
        """
        This will test whether the given item is already pinned or not.

        Args:
            joint: The item to test

        Returns:
            True if the joint is pinned
        """
        return aniseed_toolkit.pinning.is_pinned(joint or mc.ls(selection=True)[0])
