import mref
import aniseed
from maya import cmds


class AddChildrenOfTypeToLayer(aniseed.RigComponent):
    """
    Ensures a Maya display layer exists, then walks the descendants of a
    root node and adds every node whose type matches one of the allowed
    node types to that layer.
    """

    identifier = "Utility : Add Children Of Type To Layer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Layer Name",
            value="",
            validate=True,
            description="The name of the display layer to populate. The layer is created if it does not already exist.",
        )

        self.declare_input(
            name="Root Node",
            value="",
            description="The root of the hierarchy to scan. Every descendant is considered for inclusion in the layer.",
        )

        self.declare_input(
            name="Node Types",
            value=[],
            validate=True,
            description="The Maya node types to include (e.g. mesh, nurbsCurve). Descendants whose node type is not in this list are skipped.",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "Root Node":
            return aniseed.widgets.ObjectSelector()

        if requirement_name == "Node Types":
            return aniseed.widgets.TextList()

    def run(self):
        layer_name = self.input("Layer Name").get()
        root_node_name = self.input("Root Node").get()
        allowable_types = self.input("Node Types").get()

        self.ensure_exists(layer_name)
        self.add_nodes(layer_name, root_node_name, allowable_types)

    def add_nodes(self, layer_name, root_node_name, allowable_types):
        root_node = mref.get(root_node_name)

        nodes = mref.ReferenceList(
            [
                node
                for node in root_node.children(recursive=True)
                if isinstance(node, mref.ReferencedItem) and node.node_type() in allowable_types
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
    """
    Ensures a Maya display layer exists, then adds every Maya controller
    whose name (or full DAG path, configurable via 'Test By Full Name')
    contains the chosen root-node string to that layer.
    """

    identifier = "Utility : Add Controls To Layer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Layer Name",
            value="Controls",
            validate=True,
            description="The name of the display layer to populate. The layer is created if it does not already exist.",
        )

        self.declare_input(
            name="Root Node",
            value="",
            description="The substring to match against each controller's name when deciding whether it belongs to this layer.",
        )

        self.declare_option(
            name="Test By Full Name",
            value=True,
            description="If true, the Root Node substring is matched against each controller's full DAG path (safer when controls live deep in a hierarchy). If false, only the short name is tested.",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "Root Node":
            return aniseed.widgets.ObjectSelector()

    def run(self):
        layer_name = self.input("Layer Name").get()
        root_node = self.input("Root Node").get()
        test_by_full_name = self.option("Test By Full Name").get()

        self.ensure_exists(layer_name)
        self.add_nodes(layer_name, root_node, test_by_full_name)

    def add_nodes(self, layer_name, root_node, test_by_full_name):
        all_controllers = [
            control.name()
            for control in mref.controller(query=True, allControllers=True)
            if root_node in (control.full_name() if test_by_full_name else control.name())
        ]

        mref.editDisplayLayerMembers(layer_name, all_controllers, noRecurse=True)

    def ensure_exists(self, layer_name: str):

        if cmds.objExists(layer_name):
            if cmds.nodeType(layer_name) == "displayLayer":
                return layer_name
            else:
                raise ValueError(f"'{layer_name}' exists but is not a displayLayer.")
        return cmds.createDisplayLayer(name=layer_name, empty=True)