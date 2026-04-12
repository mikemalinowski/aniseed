import mref
import aniseed
from maya import cmds


class AddChildrenOfTypeToLayer(aniseed.RigComponent):

    identifier = "Utility : Add Children Of Type To Layer"

    def __init__(self, *args, **kwargs):
        super(AddChildrenOfTypeToLayer, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Layer Name",
            value="",
            validate=True,
        )

        self.declare_input(
            name="Root Node",
            value="",
        )

        self.declare_input(
            name="Node Types",
            value=[],
            validate=True,
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "Root Node":
            return aniseed.widgets.ObjectSelector()

        if requirement_name == "Node Types":
            return aniseed.widgets.TextList()

    def run(self):
        layer_name = self.input("Layer Name").get()
        self.ensure_exists(layer_name)
        self.add_nodes(layer_name)

    def add_nodes(self, layer_name):

        allowable_types = self.input("Node Types").get()
        root_node = mref.get(self.input("Root Node").get())

        nodes = mref.ReferenceList(
            [
                node
                for node in root_node.children(recursive=True)
                if node.node_type() in allowable_types
            ]
        )
        mref.editDisplayLayerMembers(layer_name, nodes.names(), noRecurse=True)

    def ensure_exists(self, layer_name: str):

        if cmds.objExists(layer_name):
            if cmds.nodeType(layer_name) == "displayLayer":
                return layer_name
            else:
                raise ValueError(f"'{layer_name}' exists but is not a displayLayer.")
        return cmds.createDisplayLayer(name=layer_name, empty=True)


class AddControlsToLayer(aniseed.RigComponent):
    identifier = "Utility : Add Controls To Layer"

    def __init__(self, *args, **kwargs):
        super(AddControlsToLayer, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Layer Name",
            value="Controls",
            validate=True,
        )

        self.declare_input(
            name="Root Node",
            value = "",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "Root Node":
            return aniseed.widgets.ObjectSelector()

    def run(self):
        layer_name = self.input("Layer Name").get()
        self.ensure_exists(layer_name)
        self.add_nodes(layer_name)

    def add_nodes(self, layer_name):

        root_node = self.input("Root Node").get()

        all_controllers = [
            control.name()
            for control in mref.controller(query=True, allControllers=True)
            if root_node in control.full_name()
        ]

        mref.editDisplayLayerMembers(layer_name, all_controllers, noRecurse=True)

    def ensure_exists(self, layer_name: str):

        if cmds.objExists(layer_name):
            if cmds.nodeType(layer_name) == "displayLayer":
                return layer_name
            else:
                raise ValueError(f"'{layer_name}' exists but is not a displayLayer.")
        return cmds.createDisplayLayer(name=layer_name, empty=True)
