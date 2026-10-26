"""
Provides the "Utility : Apply Pose" component, which stores the object
space matrices of a set of nodes (and optionally their transform
descendants) and re-applies them on every build. Poses are captured with
the Store Pose button, and menu entries allow storing or applying the pose
for just the selected nodes.
"""
import logging
import os
import mref
import typing
import aniseed

from maya import cmds

log = logging.getLogger(__name__)


class PosingComponent(aniseed.RigComponent):
    """
    Stores a snapshot of the transforms of a set of nodes and re-applies
    them on rebuild. Used to pin a rig back to a captured pose after
    rebuilding from guides.

    Note that the matrices are captured and applied in object (local)
    space.
    """

    identifier = "Utility : Apply Pose"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes input, the Apply To Children option, the Store Pose
        button option and the hidden pose data storage.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
            validate=True,
            group="Objects",
            description="The nodes to capture and re-apply transforms for. When Apply To Children is enabled, transform descendants of these nodes are also captured.",
        )

        self.declare_option(
            name="Apply To Children",
            value=True,
            group="Behaviour",
            description="If true, all transform descendants of each input node are also captured and re-applied (skipping any node with 'constraint' in its name).",
        )

        self.declare_option(
            name="_StorePose",
            value=True,
            group="Functionality",
            description="Press to capture the current object-space (local) transforms of the input nodes (and their children when enabled) into the component.",
        )

        self.declare_option(
            "_PoseData",
            value=None,
            hidden=True,
            description="Internal storage for the captured node-to-matrix dictionary.",
        )

    def option_widget(self, option_name: str):
        """
        Returns a Store Pose button widget for the _StorePose option.
        """
        if option_name == "_StorePose":
            return aniseed.widgets.ButtonWidget(
                button_name="Store Pose",
                func=self._store
            )

    def input_widget(self, requirement_name: str) :
        """
        Returns an object list widget for the Nodes input, and None for anything
        else.
        """
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()

        return None

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Exposes the Apply Pose To Selected and Store Selected menu entries.
        """
        return {
            "Apply Pose To Selected": self.apply_to_selected,
            "Store Selected": self.store_selected,
        }

    def is_valid(self) -> bool:
        """
        Checks that at least one node has been given.
        """
        if not self.input("Nodes").get():
            log.warning(f"{self.label()} : No node given")
            return False

        return True

    def run(self) -> bool:
        """
        Applies the stored pose to all of the nodes it was captured from.
        """
        self._apply()
        return True

    def _store(self):
        """
        Captures the matrices of the input nodes (and their children when
        enabled) into the pose data, replacing anything stored previously.
        """
        self.option("_PoseData").set(self._read_matrices(self._get_nodes()))

    def _get_nodes(self):
        """
        Returns the input nodes, plus all of their transform descendants
        (excluding any with 'constraint' in the name) when Apply To Children is
        enabled.

        Returns:
            List of node names
        """
        nodes = list(self.input("Nodes").get() or [])

        if not self.option("Apply To Children").get():
            return nodes

        # -- The node names are the keys of the stored pose data, so these
        # -- are kept as the plain names maya.cmds gives
        all_children = []
        for node in nodes:
            descendants = cmds.listRelatives(
                node,
                children=True,
                allDescendents=True,
                type="transform",
            ) or []
            all_children.extend(descendants)

        nodes.extend(
            child
            for child in all_children
            if "constraint" not in child.lower()
        )

        return nodes

    def apply_to_selected(self):
        """
        Applies the stored pose only to the currently selected nodes.
        """
        # -- Plain maya.cmds names, so they can be compared against the
        # -- node names stored in the pose data
        selected = cmds.ls(selection=True) or list()

        if not selected:
            return

        self._apply(only=selected)

    def store_selected(self):
        """
        Captures the matrices of the currently selected nodes and merges them
        into the existing pose data.
        """
        data = self.option("_PoseData").get() or {}
        data.update(self._read_matrices(cmds.ls(selection=True)))
        self.option("_PoseData").set(data)

    def _apply(self, only: list[str] = None):
        """
        Applies the stored (object space) matrices to the nodes they were
        captured from.

        Args:
            only: If given, only nodes in this list are posed
        """
        data = self.option("_PoseData").get()

        if not data:
            return

        for node, matrix in data.items():
            if only is not None and node not in only:
                continue

            if not mref.objExists(node):
                log.warning(f"Could not apply Pose to {node} as it does not exist. Skipping.")
                continue

            mref.get(node).set_matrix(matrix)

    @staticmethod
    def _read_matrices(nodes) -> dict:
        """
        Returns a dictionary of the object space matrix of each given node,
        keyed by the node name.
        """
        return {
            node: mref.get(node).get_matrix()
            for node in nodes
        }
