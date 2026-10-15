"""
Provides the "Augment : Add Parent Control" component, which creates a
control under a node's current parent and then parents the node beneath it.
"""
import mref
import aniseed
import aniseed_toolkit


class InsertParentControlComponent(aniseed.mixins.InsertControlMixin, aniseed.RigComponent):
    """
    Creates a control as a child of the nodes parent and then makes
    the given node a child of the new control.
    """

    identifier = "Augment : Add Parent Control"

    def __init__(self, *args, **kwargs):
        """
        Declares the "Node" input and the shared control attributes (match to,
        location etc) from the insert control mixin.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Node",
            description=(
                "The node to insert a new parent control above. The "
                "new control will take the node's existing parent as "
                "its own parent."
            ),
            value="",
            validate=True,
            group="Required Joint",
        )

        self._declare_control_attributes(
            match_description=(
                "Optional node whose world transform the new control "
                "will be matched to. Leave empty to match the input "
                "node's parent."
            ),
            location_description=(
                "Location token (e.g. c/l/r/f/b) used when generating "
                "the control's name. Inherited from the parent "
                "component when added to the stack."
            ),
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the "Node" input, or None otherwise.

        Args:
            requirement_name: The name of the input to return a widget for.
        """
        if requirement_name == "Node":
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def run(self) -> bool:
        """
        Creates a control under the node's current parent (or the world if it
        has none), matched to that parent unless a match node is given, and then
        parents the node beneath the new control.
        """

        node = mref.get(self.input("Node").get())

        # -- A node at the world root has no parent; pass None through
        # -- so the toolkit creates the control under the world.
        node_parent = node.parent()
        parent_name = node_parent.full_name() if node_parent else None

        control = self._create_control(
            parent=parent_name,
            default_match_to=parent_name,
        )
        node.set_parent(control.ctl)

        return True
