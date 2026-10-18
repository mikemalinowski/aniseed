"""
Provides components for populating Maya display layers, creating the layer
if needed. "Utility : Add Children Of Type To Layer" adds every descendant
of a root node whose type is in a given list, and "Utility : Add Controls
To Layer" adds every controller whose name contains a given string.
"""
import mref
import aniseed


def _ensure_display_layer(layer_name: str) -> None:
    """
    Creates an empty display layer with the given name if it does not
    already exist. Raises a ValueError if a node of another type
    already has that name.
    """
    if not mref.objExists(layer_name):
        mref.createDisplayLayer(name=layer_name, empty=True)

    elif mref.get(layer_name).node_type() != "displayLayer":
        raise ValueError(f"'{layer_name}' exists but is not a displayLayer.")


class AddChildrenOfTypeToLayer(aniseed.RigComponent):
    """
    Ensures a Maya display layer exists, then walks the descendants of a
    root node and adds every node whose type matches one of the allowed
    node types to that layer.
    """

    identifier = "Utility : Add Children Of Type To Layer"

    def __init__(self, *args, **kwargs):
        """
        Declares the Layer Name, Root Node and Node Types inputs.
        """
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
        """
        Returns an object selector for the Root Node input and a text list for
        the Node Types input.
        """
        if requirement_name == "Root Node":
            return aniseed.widgets.ObjectSelector()

        if requirement_name == "Node Types":
            return aniseed.widgets.TextList()

    def run(self):
        """
        Ensures the display layer exists, then adds every descendant of the
        root node whose node type is in Node Types to it.
        """
        layer_name = self.input("Layer Name").get()
        root_node = mref.get(self.input("Root Node").get())
        allowable_types = self.input("Node Types").get()

        _ensure_display_layer(layer_name)

        nodes = mref.ReferenceList(
            [
                node
                for node in root_node.children(recursive=True)
                if isinstance(node, mref.ReferencedItem) and node.node_type() in allowable_types
            ]
        )
        mref.editDisplayLayerMembers(layer_name, nodes.names(), noRecurse=True)


class AddControlsToLayer(aniseed.RigComponent):
    """
    Ensures a Maya display layer exists, then adds every Maya controller
    whose name (or full DAG path, configurable via 'Test By Full Name')
    contains the chosen root-node string to that layer.
    """

    identifier = "Utility : Add Controls To Layer"

    def __init__(self, *args, **kwargs):
        """
        Declares the Layer Name and Root Node inputs and the Test By Full Name
        option.
        """
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
        """
        Returns an object selector for the Root Node input.
        """
        if requirement_name == "Root Node":
            return aniseed.widgets.ObjectSelector()

    def run(self):
        """
        Ensures the display layer exists, then adds every controller in the
        scene whose name (or full name, depending on Test By Full Name) contains
        the Root Node string to it.
        """
        layer_name = self.input("Layer Name").get()
        root_node = self.input("Root Node").get()
        test_by_full_name = self.option("Test By Full Name").get()

        _ensure_display_layer(layer_name)

        controls = [
            control.name()
            for control in mref.controller(query=True, allControllers=True)
            if root_node in (control.full_name() if test_by_full_name else control.name())
        ]
        mref.editDisplayLayerMembers(layer_name, controls, noRecurse=True)
