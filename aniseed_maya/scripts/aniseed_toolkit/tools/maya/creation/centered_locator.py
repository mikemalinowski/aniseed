import aniseed_toolkit
import maya.cmds as mc


class CreateLocatorAtCenterTool(aniseed_toolkit.Tool):

    identifier = "Create Locator At Center"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(self) -> str:
        """
        Creates a locator at the center of the current selected components

        Returns:
            The name of the created locator
        """
        # -- If nothing selected, do nothing
        if not mc.ls(sl=True):
            return

        # -- Create a temporary cluster, snap position, remove temporary cluster/constraint
        temp_cluster = mc.cluster()
        locator = mc.spaceLocator()
        temp_constraint = mc.pointConstraint(
            temp_cluster[1],
            locator,
            mo=False
        )
        mc.delete(temp_cluster, temp_constraint)

        return locator