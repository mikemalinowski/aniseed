"""
Provides the attribute connection components. "Utility : Connect Attribute"
connects one source attribute into one destination attribute, optionally
routing it through a reverse node. "Utility : Connect Attribute (Multi)"
connects one source attribute into the same named attribute on a list of
nodes. Both expose a Force option to replace existing connections.
"""
import mref
import aniseed


class ConnectAttr(aniseed.RigComponent):
    """
    Connects a single source attribute on one node to a single destination
    attribute on another node, mirroring Maya's ``connectAttr`` command.
    """

    identifier = "Utility : Connect Attribute"

    def __init__(self, *args, **kwargs):
        """
        Declares the source and destination node/attribute inputs, plus the
        Force and Reverse options.
        """
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

        self.declare_option(
            name="Reverse",
            value=False,
            description="If true, the connection is routed through a reverse node, so the destination receives one minus the source value.",
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the Source Node and Destination Node
        inputs.
        """
        if requirement_name in ["Source Node", "Destination Node"]:
            return aniseed.widgets.ObjectSelector()

    def run(self):
        """
        Connects the source attribute into the destination attribute. When
        Reverse is enabled, a reverse node is created and the connection is
        routed through its X channel.
        """
        source_node = mref.get(self.input("Source Node").get())
        destination_node = mref.get(self.input("Destination Node").get())

        source_attribute = source_node.attr(self.input("Source Attribute").get())
        destination_attribute = destination_node.attr(self.input("Destination Attribute").get())

        # -- When reversing, the reverse node sits between the source
        # -- and the destination
        if self.option("Reverse").get():
            reverse_node = mref.create("reverse")
            source_attribute.connect(reverse_node.inputX)
            source_attribute = reverse_node.outputX

        source_attribute.connect(
            destination_attribute,
            force=self.option("Force").get(),
        )


class ConnectManyAttr(aniseed.RigComponent):
    """
    Connects a single source attribute on one node to the same named
    attribute on every node in a list of destination nodes.
    """

    identifier = "Utility : Connect Attribute (Multi)"

    def __init__(self, *args, **kwargs):
        """
        Declares the source node/attribute inputs, the Destination Nodes list
        and Destination Attribute inputs, and the Force option.
        """
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
        """
        Returns an object selector for Source Node and an object list for
        Destination Nodes.
        """
        if requirement_name in ["Source Node"]:
            return aniseed.widgets.ObjectSelector()

        if requirement_name == "Destination Nodes":
            return aniseed.widgets.ObjectList()

    def run(self):
        """
        Connects the source attribute into the Destination Attribute of
        every node in Destination Nodes.
        """
        source_node = mref.get(self.input("Source Node").get())
        source_attribute = source_node.attr(self.input("Source Attribute").get())
        destination_attribute = self.input("Destination Attribute").get()
        force = self.option("Force").get()

        for destination_node_name in self.input("Destination Nodes").get():
            source_attribute.connect(
                mref.get(destination_node_name).attr(destination_attribute),
                force=force,
            )
