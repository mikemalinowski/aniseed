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
            nodes = mc.ls(sl=True)

        for node in nodes:
            for child in mc.listRelatives(node, children=True) or list():
                if "constraint" in mc.nodeType(child).lower():
                    mc.delete(child)
