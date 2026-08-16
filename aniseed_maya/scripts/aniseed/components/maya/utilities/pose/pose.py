import os
import typing
import aniseed

from maya import cmds


class PosingComponent(aniseed.RigComponent):
    """
    Stores a snapshot of world-space transforms for a set of nodes and
    re-applies them on rebuild. Used to pin a rig back to a captured pose
    after rebuilding from guides.
    """

    identifier = "Utility : Apply Pose"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
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
            description="Press to capture the current world-space transforms of the input nodes (and their children when enabled) into the component.",
        )

        self.declare_option(
            "_PoseData",
            value=None,
            hidden=True,
            description="Internal storage for the captured node-to-matrix dictionary.",
        )

    def option_widget(self, option_name: str):
        if option_name == "_StorePose":
            return aniseed.widgets.ButtonWidget(
                button_name="Store Pose",
                func=self._store
            )

    def input_widget(self, requirement_name: str) :
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()

        return None

    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Apply Pose To Selected": self.apply_to_selected,
            "Store Selected": self.store_selected,
        }

    def is_valid(self) -> bool:
        if not self.input("Nodes").get():
            print("No node given")
            return False

        return True

    def run(self) -> bool:

        data = self.option("_PoseData").get()

        if not data:
            return True

        for node, matrix in data.items():
            if not cmds.objExists(node):
                print(f"Could not apply Pose to {node} as it does not exist. Skipping.")
                continue

            cmds.xform(
                    node,
                    matrix=matrix,
                )

        return True

    def _store(self):

        data = dict()

        for node in self._get_nodes():

            data[node] = cmds.xform(
                node,
                query=True,
                matrix=True,
            )

        self.option("_PoseData").set(data)

    def _get_nodes(self):
        nodes = list(self.input("Nodes").get() or [])

        if not self.option("Apply To Children").get():
            return nodes

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

        selected = cmds.ls(selection=True) or list()

        if not selected:
            return

        data = self.option("_PoseData").get()

        if not data:
            return

        for node, matrix in data.items():
            if node not in selected:
                continue

            if not cmds.objExists(node):
                print(f"Could not apply Pose to {node} as it does not exist. Skipping.")
                continue

            cmds.xform(
                node,
                matrix=matrix,
            )

    def store_selected(self):

        data = self.option("_PoseData").get() or {}

        for node in cmds.ls(selection=True):
            data[node] = cmds.xform(
                node,
                query=True,
                matrix=True,
            )

        self.option("_PoseData").set(data)