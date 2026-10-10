import mref
import aniseed
import aniseed_toolkit
from maya import cmds


class MakeHierarchical(aniseed.RigComponent):
    """
    Creates a control that blends the rotation of a joint between two
    target nodes. A "Blend" attribute on the control (0.0 to 1.0) drives
    a pair of parent constraints between Target A and Target B, while the
    control itself drives the joint's transform.
    """

    identifier = "Utility : Parent Hierarchy"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes To Make Hierarchical",
            value="",
            validate=True,
        )

    def input_widget(self, requirement_name):

        if requirement_name == "Nodes To Make Hierarchical":
            return aniseed.widgets.ObjectList()

        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        nodes = self.input("Nodes To Make Hierarchical").get()

        for idx, node in enumerate(nodes):
            if not idx:
                continue

            try:
                node = mref.get(node)
                world_matrix = node.get_matrix(space="world")
                node.set_parent(nodes[idx-1])
                node.set_matrix(world_matrix)
            except: pass


class SetParentMulti(aniseed.RigComponent):
    """
    Creates a control that blends the rotation of a joint between two
    target nodes. A "Blend" attribute on the control (0.0 to 1.0) drives
    a pair of parent constraints between Target A and Target B, while the
    control itself drives the joint's transform.
    """

    identifier = "Utility : Reparent (Multi)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes To Reparent",
            value=[],
            validate=True,
        )

        self.declare_input(
            name="New Parent",
            value="",
        )

    def input_widget(self, requirement_name):

        if requirement_name == "Nodes To Reparent":
            return aniseed.widgets.ObjectList()

        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        nodes = self.input("Nodes To Reparent").get()
        parent = mref.get(self.input("New Parent").get())

        for node in nodes:
            try:
                node = mref.get(node)
                world_matrix = node.get_matrix(space="world")
                node.set_parent(parent)
                node.set_matrix(world_matrix)
            except: pass

