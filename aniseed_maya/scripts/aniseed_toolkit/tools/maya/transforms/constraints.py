import aniseed_toolkit
from maya import cmds


class ClearConstraintsTool(aniseed_toolkit.Tool):

    identifier = "Clear Constraints"
    classification = "Rigging"
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
            nodes = cmds.ls(selection=True)

        aniseed_toolkit.scene.constraints.remove_all(nodes)
