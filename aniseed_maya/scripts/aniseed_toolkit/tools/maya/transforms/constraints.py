import aniseed_toolkit
import maya.cmds as mc


class ClearConstraintsTool(aniseed_toolkit.Tool):

    identifier = "Clear Constraints"
    categories = [
        "Transforms",
    ]

    def run(
        self,
        node: str = "",
    ):

        if node:
            nodes = [node]
        else:
            nodes = mc.ls(selection=True)

        aniseed_toolkit.containts.remove_all(nodes)
