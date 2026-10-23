import logging

import qtility
import aniseed_toolkit
from maya import cmds

log = logging.getLogger(__name__)


class SnapshotCopyDestination(aniseed_toolkit.Tool):
    """
    This will store the vertices that you want to copy weights to. Using the Localised Copy
    will ONLY affect these vertices.
    """

    identifier = 'Localised Copy : Snapshot Destination'
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self):
        aniseed_toolkit.scene.skin.LocalisedSkinCopy.snapshot_vertices()

        qtility.request.message(
            title="Localised Copy",
            message="Destination vertices stored!",
        )


class CopyLocalised(aniseed_toolkit.Tool):
    """
    This will copy the weighting from the currently selected object to the stored vertices (using
    the Snapshot Destination tool).

    Note: The influences MUST be the same.
    """

    identifier = 'Localised Copy : Copy'
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self):
        aniseed_toolkit.scene.skin.LocalisedSkinCopy.copy_skinweights()

        qtility.request.message(
            title="Localised Copy",
            message="Skin weights copied to the stored vertices!",
        )


class CopySkinWeightsToMemory(aniseed_toolkit.Tool):
    """
    Copies the skin weights of the selected mesh into memory, ready to be
    applied with the Paste Skin Weights To Matching Vertices tool.
    """

    identifier = "Copy Skin Weights To Memory"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, mesh: str = "") -> bool:
        """
        Copies the skin weights of the given (or selected) mesh into memory.

        Args:
            mesh: The skinned mesh to copy from. If not given, the first
                selected object is used.

        Returns:
            True if the weights were copied.
        """
        try:
            data = aniseed_toolkit.scene.skin.copy_skin_to_memory(mesh)

        except ValueError as error:
            cmds.warning(str(error))
            return False

        vertex_count = len(data["weights"][0]) if data["weights"] else 0
        log.info(
            f"Copied skin weights to memory: {vertex_count} vertices, "
            f"{len(data['influences'])} influences"
        )
        return True


class PasteSkinWeightsToMatchingVertices(aniseed_toolkit.Tool):
    """
    Pastes the skin weights held in memory (from the Copy Skin Weights To
    Memory tool) onto the selected vertices. Each vertex takes the weights of
    the copied vertex with the same id. If the mesh has no skin cluster, one
    is added.
    """

    identifier = "Paste Skin Weights To Matching Vertices"
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, vertices: list[str] = None) -> bool:
        """
        Pastes the copied skin weights onto the given (or selected) vertices,
        matching by vertex id. Selecting a whole mesh pastes onto all of its
        vertices.

        Args:
            vertices: The target vertices. If not given, the selected
                vertices are used.

        Returns:
            True if the weights were pasted.
        """
        try:
            result = aniseed_toolkit.scene.skin.paste_skin_to_matching_vertices(vertices)

        except ValueError as error:
            cmds.warning(str(error))
            return False

        if result["skipped"]:
            cmds.warning(
                f"{len(result['skipped'])} vertices have no matching id in the "
                f"copied data and were skipped"
            )

        log.info(
            f"Pasted skin weights onto {result['pasted']} vertices "
            f"of {result['mesh']}"
        )
        return True