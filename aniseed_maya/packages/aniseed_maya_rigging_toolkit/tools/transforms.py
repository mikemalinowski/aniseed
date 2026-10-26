"""
Rigging Toolkit tools for working with transforms: scaling translations,
clearing constraints, aiming, positioning between nodes, mirroring and showing
the local axis.
"""
import logging

import mref
from maya import cmds

import aniseed
import aniseed_toolkit
from aniseed import toolkits

log = logging.getLogger(__name__)

# -- The translation channels the snapshot stores, in order
_AXES = ["X", "Y", "Z"]

# -- The clipboard Scale Translation Snapshot stores the translations in
_SNAPSHOT_CLIPBOARD = "Scale Translation Snapshot"

# -- The axis strings Aim At accepts (see Direction.from_string)
_AIM_AXES = ["x", "y", "z", "-x", "-y", "-z"]


def _node_or_selection(node: str) -> list:
    """
    Returns the given node in a list, or the selection if no node is given.
    """
    if node:
        return [node]

    return cmds.ls(selection=True)


def _requires_node_or_selection(node: str, message: str) -> bool:
    if not _node_or_selection(node):
        log.warning(message)
        return False

    return True


def _snapshot() -> dict:
    """
    Returns the stored translations, by node name.
    """
    return toolkits.clipboard(_SNAPSHOT_CLIPBOARD).get("translations") or dict()


def _name_replacement(expression: str) -> list or None:
    """
    Returns the [replace_this, with_this] pair of a "replace_this:with_this"
    expression, or None if the expression is empty.
    """
    if not expression:
        return None

    replace_this, with_this = expression.split(":")[:2]
    return [replace_this, with_this]


# --------------------------------------------------------------------------------------
class SnapshotNodeTranslation(toolkits.Tool):
    """
    Remembers the translation of the given Node, or of the selected nodes if
    no Node is given, so Scale Translation (From Snapshot) can scale them from
    these values. Each run replaces the previous snapshot.
    """

    identifier = "Scale Translation Snapshot"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node to snapshot, used instead of the selection when given",
        )

    def option_widget(self, option_name: str):
        if option_name == "Node":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        return None

    def is_valid(self) -> bool:
        return _requires_node_or_selection(
            self.option("Node").get(),
            "Select the nodes to snapshot the translation of, or give a Node",
        )

    def run(self) -> None:
        snapshot = dict()

        for node in _node_or_selection(self.option("Node").get()):
            node = mref.get(node)
            snapshot[node.name()] = [
                node.attr(f"translate{axis}").get()
                for axis in _AXES
            ]

        toolkits.clipboard(_SNAPSHOT_CLIPBOARD)["translations"] = snapshot
        log.info(f"Stored {len(snapshot)} nodes")


# --------------------------------------------------------------------------------------
class ScaleTranslationFromSnapshot(toolkits.Tool):
    """
    Restores the translation of every node stored by Scale Translation
    Snapshot, then multiplies it by Scale By. Running it again scales from
    the snapshot rather than compounding. Nodes which no longer exist are
    skipped.
    """

    identifier = "Scale Translation (From Snapshot)"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Scale By",
            value=1.0,
            description="The amount to multiply the stored translations by",
        )

    def is_valid(self) -> bool:
        if not _snapshot():
            log.warning("Store a snapshot with Scale Translation Snapshot first")
            return False

        return True

    def run(self) -> None:
        scale_by = self.option("Scale By").get()

        for node_name, base_translation in _snapshot().items():

            if not mref.objExists(node_name):
                continue

            node = mref.get(node_name)

            for index, axis in enumerate(_AXES):
                node.attr(f"translate{axis}").set(base_translation[index])

            aniseed_toolkit.scene.transforms.scale_translation(node, scale_by)


# --------------------------------------------------------------------------------------
class ScaleNodeTranslation(toolkits.Tool):
    """
    Multiplies the translation of the given Node, or of the selected nodes if
    no Node is given, by Scale By.
    """

    identifier = "Scale Translation (Node)"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node to scale the translation of, used instead of the selection when given",
        )

        self.declare_option(
            name="Scale By",
            value=1.0,
            description="The amount to multiply the translation by",
        )

    def option_widget(self, option_name: str):
        if option_name == "Node":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        return None

    def is_valid(self) -> bool:
        return _requires_node_or_selection(
            self.option("Node").get(),
            "Select the nodes to scale the translation of, or give a Node",
        )

    def run(self) -> None:
        scale_by = self.option("Scale By").get()

        for node in _node_or_selection(self.option("Node").get()):
            aniseed_toolkit.scene.transforms.scale_translation(node, scale_by)


# --------------------------------------------------------------------------------------
class ScaleHierarchyTranslation(toolkits.Tool):
    """
    Multiplies the translation of the given Node, or of the selected nodes if
    no Node is given, and of every transform and joint below them, by Scale
    By.
    """

    identifier = "Scale Translation (Hierarchy)"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The top node of the hierarchy to scale, used instead of the selection when given",
        )

        self.declare_option(
            name="Scale By",
            value=1.0,
            description="The amount to multiply the translations by",
        )

    def option_widget(self, option_name: str):
        if option_name == "Node":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        return None

    def is_valid(self) -> bool:
        return _requires_node_or_selection(
            self.option("Node").get(),
            "Select the top nodes of the hierarchies to scale, or give a Node",
        )

    def run(self) -> None:
        scale_by = self.option("Scale By").get()

        for node in _node_or_selection(self.option("Node").get()):
            aniseed_toolkit.scene.transforms.scale_translation_of_hierarchy(node, scale_by)


# --------------------------------------------------------------------------------------
class ClearConstraintsTool(toolkits.Tool):
    """
    Deletes every constraint directly beneath the given Node, or beneath the
    selected nodes if no Node is given.
    """

    identifier = "Clear Constraints"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node to clear the constraints of, used instead of the selection when given",
        )

    def option_widget(self, option_name: str):
        if option_name == "Node":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        return None

    def is_valid(self) -> bool:
        return _requires_node_or_selection(
            self.option("Node").get(),
            "Select the nodes to clear the constraints of, or give a Node",
        )

    def run(self) -> None:
        aniseed_toolkit.scene.constraints.remove_all(
            _node_or_selection(self.option("Node").get()),
        )


# --------------------------------------------------------------------------------------
class AimAtTool(toolkits.Tool):
    """
    Rotates one node to aim at another. Select the node to aim then the node
    to aim at (and optionally a third node to use as the up target), or give
    them as Aim This, At This and Up Target; a selection of two or three
    nodes is used over those options. Aim Axis is the axis pointed at the
    target, and Up Axis the axis pointed towards the Up Target (or the scene
    up when there is no up target).
    """

    identifier = "Aim At"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Aim This",
            value="",
            description="The node to rotate (used when two or three nodes are not selected)",
        )

        self.declare_option(
            name="At This",
            value="",
            description="The node to aim at (used when two or three nodes are not selected)",
        )

        self.declare_option(
            name="Aim Axis",
            value="x",
            description="The axis to point at the target, such as x or -x",
        )

        self.declare_option(
            name="Up Axis",
            value="y",
            description="The axis to point towards the up target (or the scene up), such as y or -y",
        )

        self.declare_option(
            name="Up Target",
            value="",
            description="The node to use as the up target. The scene up is used if not given",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Aim This", "At This", "Up Target"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        if option_name in ["Aim Axis", "Up Axis"]:
            return aniseed.widgets.ItemSelector(
                items=_AIM_AXES,
                default_item=self.option(option_name).get(),
            )

        return None

    def _nodes(self) -> tuple:
        """
        Returns the node to aim, the node to aim at and the up target, from
        the selection if two or three nodes are selected, otherwise from the
        options.
        """
        aim_this = self.option("Aim This").get()
        at_this = self.option("At This").get()
        up_target = self.option("Up Target").get()

        selection_list = cmds.ls(selection=True)

        if len(selection_list) == 2:
            aim_this, at_this = selection_list

        elif len(selection_list) == 3:
            aim_this, at_this, up_target = selection_list

        return aim_this, at_this, up_target

    def is_valid(self) -> bool:
        aim_this, at_this, _ = self._nodes()

        if not aim_this or not at_this:
            log.warning("Select the node to aim then the node to aim at, or give Aim This and At This")
            return False

        return True

    def run(self) -> None:
        aim_this, at_this, up_target = self._nodes()

        aniseed_toolkit.scene.transforms.aim_at(
            aim_this,
            at_this,
            self.option("Aim Axis").get(),
            self.option("Up Axis").get(),
            up_target,
        )


# --------------------------------------------------------------------------------------
class PositionBetween(toolkits.Tool):
    """
    Moves Node to a position between From This and To This. A Factor of 0
    puts it on top of To This, a Factor of 1 on top of From This, and 0.5
    halfway between them.
    """

    identifier = "Position Between"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node to move",
        )

        self.declare_option(
            name="From This",
            value="",
            description="The node a Factor of 1 puts it on top of",
        )

        self.declare_option(
            name="To This",
            value="",
            description="The node a Factor of 0 puts it on top of",
        )

        self.declare_option(
            name="Factor",
            value=0.5,
            description="How far between To This (0) and From This (1) to put the node",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Node", "From This", "To This"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        return None

    def is_valid(self) -> bool:
        for name in ["Node", "From This", "To This"]:
            if not self.option(name).get():
                log.warning("Give the Node to move, and the From This and To This nodes to put it between")
                return False

        return True

    def run(self) -> None:
        aniseed_toolkit.scene.transforms.position_between(
            node=self.option("Node").get(),
            from_this=self.option("From This").get(),
            to_this=self.option("To This").get(),
            factor=self.option("Factor").get(),
        )


# --------------------------------------------------------------------------------------
class GlobalMirrorTool(toolkits.Tool):
    """
    Mirrors the world space transform of the selected transforms and joints
    across a plane through the world origin (Across). With Behaviour on, the
    rotational behaviour is mirrored too, and Flip XY Rotations flips the
    result 180 degrees in X and Y. Give a Name Replacement of the form
    replace_this:with_this (such as _LF:_RT) to apply each mirrored transform
    to the node with that replaced name instead of the node itself; leave it
    empty to mirror the selected nodes in place.
    """

    identifier = "Global Mirror"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Across",
            value="YZ",
            description="The plane to mirror across",
        )

        self.declare_option(
            name="Behaviour",
            value=True,
            description="Whether to mirror the rotational behaviour too",
        )

        self.declare_option(
            name="Flip XY Rotations",
            value=False,
            description="Whether to flip the result 180 degrees in X and Y",
        )

        self.declare_option(
            name="Name Replacement",
            value="",
            description="replace_this:with_this, to mirror onto the nodes with the replaced names. Empty mirrors in place",
        )

    def option_widget(self, option_name: str):
        if option_name == "Across":
            return aniseed.widgets.ItemSelector(
                items=sorted(aniseed_toolkit.scene.mirror.MIRROR_PLANES.values()),
                default_item=self.option(option_name).get(),
            )

        return None

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the transforms to mirror")
            return False

        name_replacement = self.option("Name Replacement").get()
        if name_replacement and ":" not in name_replacement:
            log.warning("Name Replacement must be of the form replace_this:with_this (or empty)")
            return False

        return True

    def run(self) -> None:
        aniseed_toolkit.scene.mirror.mirror_transforms(
            transforms=cmds.ls(selection=True),
            across=self.option("Across").get(),
            behaviour=self.option("Behaviour").get(),
            rotate_flip=self.option("Flip XY Rotations").get(),
            name_replacement=_name_replacement(self.option("Name Replacement").get()),
        )


# --------------------------------------------------------------------------------------
class InvertTranslation(toolkits.Tool):
    """
    Negates the local translation (X, Y and Z) of the selected nodes.
    """

    identifier = "Invert Translation"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the nodes to invert the translation of")
            return False

        return True

    def run(self) -> None:
        aniseed_toolkit.scene.mirror.invert_translation(
            transforms=cmds.ls(selection=True),
        )


# --------------------------------------------------------------------------------------
class ShowAxisTool(toolkits.Tool):
    """
    Shows (or with Visibility off, hides) the local rotation axis of the
    selected nodes. Selected nodes without a local axis are skipped.
    """

    identifier = "Show Axis"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Visibility",
            value=True,
            description="Whether to show the local axis (on) or hide it (off)",
        )

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the nodes to show the local axis of")
            return False

        return True

    def run(self) -> None:
        visibility = self.option("Visibility").get()

        for node in mref.selected():
            if node.has_attribute("displayLocalAxis"):
                node.displayLocalAxis.set(visibility)
