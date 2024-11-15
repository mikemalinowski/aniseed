import os
import typing
import aniseed

import maya.cmds as mc


# --------------------------------------------------------------------------------------
class PosingComponent(aniseed.RigComponent):

    identifier = "Utility : Apply Pose"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(PosingComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Node",
            value="",
            validate=True,
            group="Required Joint",
        )

        self.declare_option(
            name="Apply To Children",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="_StorePose",
            value=True,
            group="Functionality"
        )

        self.declare_option(
            "_PoseData",
            value=None,
            hidden=True,
        )

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):
        if option_name == "_StorePose":
            return aniseed.widgets.everywhere.ButtonWidget(
                button_name="Store Pose",
                func=self._store
            )

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name: str) :
        if requirement_name == "Node":
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        return None

    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Apply Pose To Selected": self.apply_to_selected,
            "Store Selected": self.store_selected,
        }

    # ----------------------------------------------------------------------------------
    def is_valid(self) -> bool:
        if not self.input("Node").get():
            print("No node given")
            return False

        return True

    # ----------------------------------------------------------------------------------
    def run(self) -> bool:

        data = self.option("_PoseData").get()

        if not data:
            return True

        for node, matrix in data.items():
            if not mc.objExists(node):
                print(f"Could not apply Pose to {node} as it does not exist. Skipping.")
                continue

            mc.xform(
                    node,
                    matrix=matrix,
                )

        return True

    # ----------------------------------------------------------------------------------
    def _store(self):
        # label = "PoseStore" + self.input('Label').get()

        data = dict()

        for node in self._get_nodes():

            data[node] = mc.xform(
                node,
                query=True,
                matrix=True,
            )

        self.option("_PoseData").set(data)

    # ----------------------------------------------------------------------------------
    def _get_nodes(self):
        nodes = [self.input("Node").get()]

        if self.option("Apply To Children").get():

            all_children = mc.listRelatives(
                nodes[0],
                children=True,
                allDescendents=True,
                type="transform"
            ) or list()

            nodes.extend(
                [
                    node
                    for node in all_children
                    if "constraint" not in node.lower()
                ]
            )

        return nodes

    # ----------------------------------------------------------------------------------
    def apply_to_selected(self):

        selected = mc.ls(sl=True) or list()

        if not selected:
            return

        data = self.option("_PoseData").get()

        if not data:
            return True

        for node, matrix in data.items():
            if not node in selected:
                continue

            if not mc.objExists(node):
                print(f"Could not apply Pose to {node} as it does not exist. Skipping.")
                continue

            mc.xform(
                node,
                matrix=matrix,
            )

    # ----------------------------------------------------------------------------------
    def store_selected(self):

        data = self.option("_PoseData").get()

        for node in mc.ls(sl=True):
            data[node] = mc.xform(
                node,
                query=True,
                matrix=True,
            )

        self.option("_PoseData").set(data)