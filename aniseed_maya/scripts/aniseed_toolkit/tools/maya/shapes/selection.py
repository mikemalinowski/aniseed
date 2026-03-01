import os
import json
import typing
import qtility
import aniseed_toolkit

import maya.cmds as mc
import maya.api.OpenMaya as om


class SelectShapes(aniseed_toolkit.Tool):

    identifier = 'Select Shapes'
    classification = "Rigging"
    categories = [
        "Shapes"
    ]

    def run(self, nodes=None) -> list[str]:
        """
        This will return a list of shape files which are present in the
        aniseed toolkit shapes directory

        Returns:
            List of absolute paths to the json shape files
        """
        nodes = nodes or mc.ls(sl=True)
        return aniseed_toolkit.shapes.select_shapes(nodes)
