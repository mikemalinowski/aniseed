import mref
import aniseed


class LockTransformComponent(aniseed.RigComponent):

    identifier = "Utility : Lock Transform Attributes"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes To Lock",
            value=[],
            validate=True,
        )

        self.declare_option(
            name="Hide Attributes",
            value=True,
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "Nodes To Lock":
            return aniseed.widgets.ObjectList()

    def run(self) -> bool:
        nodes = mref.get(self.input("Nodes To Lock").get())

        for node in nodes:
            node.lock_transform_attributes(hide=self.option("Hide Attributes").get())