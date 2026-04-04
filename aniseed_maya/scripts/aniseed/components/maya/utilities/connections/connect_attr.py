import mref
import aniseed
from maya import cmds


class ConnectAttr(aniseed.RigComponent):

    identifier = "Utility : Connect Attribute"

    def __init__(self, *args, **kwargs):
        super(ConnectAttr, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Source Node",
            value="",
        )

        self.declare_input(
            name="Source Attribute",
            value="",
        )

        self.declare_input(
            name="Destination Node",
            value="",
        )

        self.declare_input(
            name="Destination Attribute",
            value="",
        )

        self.declare_option(
            name="Force",
            value=True,
        )

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Source Node", "Destination Node"]:
            return aniseed.widgets.ObjectSelector()

    def is_valid(self) -> bool:
        source_node = self.input_widget("Source Node").get()
        destination_node = self.input_widget("Destination Node").get()

        if not source_node or not cmds.objExists(source_node):
            print("Source node is invalid.")
            return False

        if not destination_node or not cmds.objExists(destination_node):
            print("Destination node is invalid.")
            return False

    def run(self):

        source_node = mref.get(self.option("Source Node").get())
        destination_node = mref.get(self.option("Destination Node").get())

        source_node.attr(self.input_widget("Source Attribute").get()).connect(
            destination_node.attr(self.input_widget("Destination Attribute").get()),
            force=self.option("Force").get(),
        )
