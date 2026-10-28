"""
Rigging Toolkit tools for general scene housekeeping.
"""
import logging

from maya import cmds

from aniseed import toolkits

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
class RemoveEmptyDisplayLayers(toolkits.Tool):
    """
    Deletes every display layer in the scene which has no members. The
    default layer, and layers which come from a reference (which cannot be
    deleted), are left alone.
    """

    identifier = "Remove Empty Display Layers"
    toolkit = "Rigging"
    categories = ["General"]

    def run(self) -> None:
        removed = []

        for layer in cmds.ls(type="displayLayer"):

            if layer == "defaultLayer":
                continue

            if cmds.referenceQuery(layer, isNodeReferenced=True):
                continue

            if cmds.editDisplayLayerMembers(layer, query=True, fullNames=True):
                continue

            cmds.delete(layer)
            removed.append(layer)

        log.info(f"Removed {len(removed)} empty display layers: {removed}")
