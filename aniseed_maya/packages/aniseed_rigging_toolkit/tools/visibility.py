"""
Rigging Toolkit tools for showing and hiding nodes, using the draw style for
joints so their children stay visible.
"""
import logging

from maya import cmds

import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)


def _requires_selection(message: str) -> bool:
    if not cmds.ls(selection=True):
        log.warning(message)
        return False

    return True


# --------------------------------------------------------------------------------------
class HideNodesTool(toolkits.Tool):
    """
    Hides the selected nodes. Joints are hidden by setting their draw style
    to None (so their children stay visible); other nodes have their
    visibility turned off.
    """

    identifier = "Hide Nodes"
    toolkit = "Rigging"
    categories = ["Visibility"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the nodes to hide")

    def run(self) -> None:
        au.scene.visibility.hide(cmds.ls(selection=True))


# --------------------------------------------------------------------------------------
class ShowNodesTool(toolkits.Tool):
    """
    Shows the selected nodes. Joints are shown by setting their draw style
    to Bone; other nodes have their visibility turned on.
    """

    identifier = "Show Nodes"
    toolkit = "Rigging"
    categories = ["Visibility"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the nodes to show")

    def run(self) -> None:
        au.scene.visibility.show(cmds.ls(selection=True))
