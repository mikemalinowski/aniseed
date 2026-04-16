import mref
import aniseed
from maya import cmds


class SetAttributeMany(aniseed.RigComponent):

    identifier = "Utility : Set Attribute (Multi)"

    def __init__(self, *args, **kwargs):
        super(SetAttributeMany, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
        )

        self.declare_input(
            name="Attribute",
            value="",
        )

        self.declare_input(
            name="Value",
            value="",
            validate=False,
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()

    def run(self):

        node_names = self.input("Nodes").get()

        for node_name in node_names:

            node = mref.get(node_name)
            attribute = node.attr(self.input("Attribute").get())
            python_type = attribute.python_type()

            if python_type is None:
                continue

            value = python_type(self.input("Value").get())
            attribute.set(value)
