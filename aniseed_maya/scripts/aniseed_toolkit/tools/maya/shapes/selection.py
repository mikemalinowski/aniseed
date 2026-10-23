import os
import json
import typing
import qtility
import aniseed_toolkit

from maya import cmds
import maya.api.OpenMaya as om


class SelectShapes(aniseed_toolkit.Tool):

    identifier = 'Select Shapes'
    classification = "Rigging"
    categories = [
        "Shapes"
    ]

    def run(self, nodes=None) -> list[str]:
        """
        This will select the shapes of the given (or selected) nodes.

        Args:
            nodes: The nodes to select the shapes of

        Returns:
            None
        """
        nodes = nodes or cmds.ls(sl=True)
        return aniseed_toolkit.scene.shapes.select_shapes(nodes)
