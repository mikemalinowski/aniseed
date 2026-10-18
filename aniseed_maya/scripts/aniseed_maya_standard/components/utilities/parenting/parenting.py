"""
Provides parenting components. "Utility : Parent Hierarchy" parents each
node in a list under the one before it to form a chain, and "Utility :
Reparent (Multi)" parents a list of nodes under a single new parent.
Parenting failures are silently ignored.
"""
import mref
import aniseed


def _reparent(node, parent) -> None:
    """
    Parents the node under the given parent, attempting to retain its
    transform. Any failure is silently ignored.
    """
    try:
        node = mref.get(node)
        world_matrix = node.get_matrix(space="world")
        node.set_parent(parent)

        # -- Known issue (kept for parity): the world matrix is re-applied
        # -- in object space, so the node is moved whenever its new parent
        # -- is not at the origin. set_parent already retains the world
        # -- transform on its own.
        node.set_matrix(world_matrix)
    except:
        pass


class MakeHierarchical(aniseed.RigComponent):
    """
    Parents each of the given nodes under the node before it in the
    list, forming a single chain hierarchy.
    """

    identifier = "Utility : Parent Hierarchy"

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes To Make Hierarchical input.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes To Make Hierarchical",
            value="",
            validate=True,
        )

    def input_widget(self, requirement_name):
        """
        Returns an object list widget for the Nodes To Make Hierarchical input
        and an object selector for any other input.
        """

        if requirement_name == "Nodes To Make Hierarchical":
            return aniseed.widgets.ObjectList()

        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        """
        Parents each node in the list under the node before it, forming a chain.
        """
        nodes = self.input("Nodes To Make Hierarchical").get()

        for parent, node in zip(nodes, nodes[1:]):
            _reparent(node, parent)


class SetParentMulti(aniseed.RigComponent):
    """
    Parents each of the given nodes under a single new parent.
    """

    identifier = "Utility : Reparent (Multi)"

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes To Reparent and New Parent inputs.
        """
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
        """
        Returns an object list widget for the Nodes To Reparent input and an
        object selector for any other input (i.e. New Parent).
        """

        if requirement_name == "Nodes To Reparent":
            return aniseed.widgets.ObjectList()

        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        """
        Parents every node in Nodes To Reparent under the New Parent.
        """
        parent = mref.get(self.input("New Parent").get())

        for node in self.input("Nodes To Reparent").get():
            _reparent(node, parent)
