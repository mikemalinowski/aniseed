"""
Provides the "Augment : Insert Control" component, which creates a control
beneath a parent node and optionally moves the parent's existing transform
children under that control.
"""
import mref
import aniseed
import aniseed_toolkit


class InsertControlComponent(aniseed.mixins.InsertControlMixin, aniseed.RigComponent):
    """
    Inserts a new control between a parent node and its existing
    children. The control is created as a child of ``Parent`` and,
    if "Move All Children Under Control" is enabled, every transform
    child of ``Parent`` is re-parented under the new control so the
    control sits in the middle of the hierarchy.
    """

    identifier = "Augment : Insert Control"

    def __init__(self, *args, **kwargs):
        """
        Declares the "Parent" input, the "Move All Children Under Control" option
        and the shared control attributes (match to, location etc) from the
        insert control mixin.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description=(
                "The node above the point where the new control will "
                "be inserted. The control becomes a child of this node."
            ),
            value="",
            validate=True,
            group="Required Joint",
        )

        self.declare_option(
            name="Move All Children Under Control",
            description=(
                "If enabled, every transform child of ``Parent`` is "
                "re-parented under the new control after creation."
            ),
            value=True,
            group="Behaviour",
        )

        self._declare_control_attributes(
            match_description=(
                "Optional node whose world transform the new control "
                "will be matched to. Leave empty to match the parent."
            ),
            location_description=(
                "Location token (c/l/r/f/b) used when generating the "
                "control's name. Inherited from the parent component "
                "when added to the stack."
            ),
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the "Parent" input, or None otherwise.

        Args:
            requirement_name: The name of the input to return a widget for.
        """
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def run(self) -> bool:
        """
        Creates a control beneath the parent (matched to the parent unless a
        match node is given) and, if enabled, moves the parent's transform
        children under it. The children are gathered before the control is
        created so the control itself is not re-parented.
        """

        parent = mref.get(self.input("Parent").get())

        # -- Gather the children before the control is added beneath the parent
        children = parent.children(node_type="transform")

        control = mref.get(
            self._create_control(
                parent=parent.full_name(),
                default_match_to=parent.full_name(),
            ).ctl
        )

        if self.option("Move All Children Under Control").get():
            control.add_children(children)

        return True
