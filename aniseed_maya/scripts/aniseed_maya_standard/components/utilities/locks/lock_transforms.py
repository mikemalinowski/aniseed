"""
Provides the "Utility : Lock Transform Attributes" component, which locks
the translate, rotate and scale channels of the given nodes, optionally
hiding them from the channel box.
"""
import mref
import aniseed


class LockTransformComponent(aniseed.RigComponent):
    """
    Locks the translate, rotate and scale channels of each given node,
    optionally hiding them from the channel box.
    """

    identifier = "Utility : Lock Transform Attributes"

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes To Lock input and the Hide Attributes option.
        """
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
        """
        Returns an object list widget for the Nodes To Lock input.
        """
        if requirement_name == "Nodes To Lock":
            return aniseed.widgets.ObjectList()

    def run(self) -> bool:
        """
        Locks the transform attributes of every node in Nodes To Lock, hiding
        them from the channel box when Hide Attributes is on.
        """
        hide = self.option("Hide Attributes").get()

        for node in mref.get(self.input("Nodes To Lock").get()):
            node.lock_transform_attributes(hide=hide)
