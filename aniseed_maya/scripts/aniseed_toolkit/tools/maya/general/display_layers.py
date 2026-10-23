import logging

import aniseed_toolkit
from maya import cmds

log = logging.getLogger(__name__)


class RemoveEmptyDisplayLayers(aniseed_toolkit.Tool):
    """
    Deletes every display layer in the scene which has no members.
    """

    identifier = "Remove Empty Display Layers"
    classification = "Rigging"
    categories = [
        "General",
    ]

    def run(self) -> list[str]:
        """
        Deletes every display layer in the scene which has no members. The
        default layer, and layers which come from a reference (which cannot
        be deleted), are left alone.

        Returns:
            The names of the deleted display layers.
        """
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
        return removed
