import aniseed_toolkit
from maya import cmds


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
        aniseed_toolkit.skin.LocalisedSkinCopy.snapshot_vertices()


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
        aniseed_toolkit.skin.LocalisedSkinCopy.copy_skinweights()
