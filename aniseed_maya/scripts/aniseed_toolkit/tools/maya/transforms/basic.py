import mref
import qtility
import aniseed_toolkit
import maya.cmds as mc


class SnapshotNodeTranslation(aniseed_toolkit.Tool):

    identifier = "Scale Translation Snapshot"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    snapshot = dict()
    axis = ["X", "Y", "Z"]

    def run(
        self,
        node: str = "",
        scale_by: float = 1.0,
    ):
        if node:
            nodes = [node]
        else:
            nodes = mc.ls(selection=True)
        SnapshotNodeTranslation.snapshot = dict()

        for store_node in nodes:
            translation = []
            store_node = mref.get(store_node)
            for axis in self.axis:
                translation.append(store_node.attr(f"translate{axis}").get())
            SnapshotNodeTranslation.snapshot[store_node.name()] = translation

        qtility.request.message(
            title = "Scale Translation Snapshot",
            message = f"Stored {len(SnapshotNodeTranslation.snapshot)} nodes"
        )

class ScaleTranslationFromSnapshot(aniseed_toolkit.Tool):

    identifier = "Scale Translation (From Snapshot)"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(
        self,
        scale_by: float = 1.0,
    ):
        snapshot = SnapshotNodeTranslation.snapshot
        for node_to_scale, base_translation in snapshot.items():

            if not mref.objExists(node_to_scale):
                continue

            node_to_scale = mref.get(node_to_scale)

            for idx, axis in enumerate(SnapshotNodeTranslation.axis):
                node_to_scale.attr(f"translate{axis}").set(base_translation[idx])

            aniseed_toolkit.transformation.scale_translation(node_to_scale, scale_by)


class ScaleNodeTranslation(aniseed_toolkit.Tool):

    identifier = "Scale Translation (Node)"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(
        self,
        node: str = "",
        scale_by: float = 1.0,
    ):
        if node:
            nodes = [node]
        else:
            nodes = mc.ls(selection=True)

        for node in nodes:
            aniseed_toolkit.transformation.scale_translation(node, scale_by)


class ScaleHierarchyTranslation(aniseed_toolkit.Tool):

    identifier = "Scale Translation (Hierarchy)"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(
            self,
            node: str = "",
            scale_by: float = 1.0,
    ):
        if node:
            nodes = [node]
        else:
            nodes = mc.ls(selection=True)

        for node in nodes:
            aniseed_toolkit.transformation.scale_translation_of_hierarchy(node, scale_by)
