import mref
import aniseed
from maya import cmds


class ConnectAttr(aniseed.RigComponent):
    """
    Connects a single source attribute on one node to a single destination
    attribute on another node, mirroring Maya's ``connectAttr`` command.
    """

    identifier = "Utility : Connect Attribute"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Source Node",
            value="",
            description="The node that owns the attribute being connected from.",
        )

        self.declare_input(
            name="Source Attribute",
            value="",
            description="The name of the attribute on the source node to connect from.",
        )

        self.declare_input(
            name="Destination Node",
            value="",
            description="The node that owns the attribute being connected into.",
        )

        self.declare_input(
            name="Destination Attribute",
            value="",
            description="The name of the attribute on the destination node to connect into.",
        )

        self.declare_option(
            name="Force",
            value=True,
            description="If true, an existing connection into the destination attribute is broken before the new one is made.",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Source Node", "Destination Node"]:
            return aniseed.widgets.ObjectSelector()

    def is_valid(self) -> bool:
        return True

    def run(self):
        source_node = mref.get(self.input("Source Node").get())
        destination_node = mref.get(self.input("Destination Node").get())
        source_attribute = self.input("Source Attribute").get()
        destination_attribute = self.input("Destination Attribute").get()
        force = self.option("Force").get()

        source_node.attr(source_attribute).connect(
            destination_node.attr(destination_attribute),
            force=force,
        )


class ConnectManyAttr(aniseed.RigComponent):
    """
    Connects a single source attribute on one node to the same named
    attribute on every node in a list of destination nodes.
    """

    identifier = "Utility : Connect Attribute (Multi)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Source Node",
            value="",
            description="The node that owns the attribute being connected from.",
        )

        self.declare_input(
            name="Source Attribute",
            value="",
            description="The name of the attribute on the source node to connect from.",
        )

        self.declare_input(
            name="Destination Nodes",
            value=[],
            description="The list of nodes whose Destination Attribute will each be driven by the source.",
        )

        self.declare_input(
            name="Destination Attribute",
            value="",
            description="The attribute name to connect into on every destination node.",
        )

        self.declare_option(
            name="Force",
            value=True,
            description="If true, an existing connection into each destination attribute is broken before the new one is made.",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Source Node"]:
            return aniseed.widgets.ObjectSelector()

        if requirement_name == "Destination Nodes":
            return aniseed.widgets.ObjectList()

    def run(self):
        source_node = mref.get(self.input("Source Node").get())
        destination_node_names = self.input("Destination Nodes").get()
        source_attribute = self.input("Source Attribute").get()
        destination_attribute = self.input("Destination Attribute").get()
        force = self.option("Force").get()

        source_attr = source_node.attr(source_attribute)

        for destination_node_name in destination_node_names:
            destination_node = mref.get(destination_node_name)
            source_attr.connect(
                destination_node.attr(destination_attribute),
                force=force,
            )
