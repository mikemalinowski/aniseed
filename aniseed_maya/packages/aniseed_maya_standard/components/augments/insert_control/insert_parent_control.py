"""
Provides the "Augment : Add Parent Control" component, which creates a
control under a node's current parent and then parents the node beneath it.
"""
import logging
import mref
import aniseed
import aniseed_toolkit

log = logging.getLogger(__name__)


class InsertParentControlComponent(aniseed.RigComponent):
    """
    Creates a control as a child of the nodes parent and then makes
    the given node a child of the new control.
    """

    identifier = "Augment : Add Parent Control"

    def __init__(self, *args, **kwargs):
        """
        Declares the "Node" input, the match, naming and shape options, and the
        "Control" output.
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

        self.declare_option(
            name="Match Transform To",
            description=(
                "Optional node whose world transform the new control "
                "will be matched to. Leave empty to match the input "
                "node's parent."
            ),
            value="",
            group="Behaviour",
        )

        self.declare_option(
            name="Name",
            description="Descriptive name token used when generating the control's name.",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            description=(
                "Location token (e.g. c/l/r/f/b) used when generating "
                "the control's name. Inherited from the parent "
                "component when added to the stack."
            ),
            value=self.config.middle,
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            description="Aniseed-toolkit control shape used for the inserted control.",
            value="core_cube",
            group="Visuals",
        )

        self.declare_output(
            "Control",
            description="The newly-created control node.",
        )

    def option_widget(self, option_name: str):
        """
        Returns a location selector for "Location", a shape selector for
        "Shape" and an object selector for "Match Transform To", or None
        otherwise.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                default_item=self.option("Shape").get(),
            )

        if option_name == "Match Transform To":
            return aniseed.widgets.ObjectSelector(component=self)

    def suggested_label(self):
        """
        Builds a label from the "Name" and upper-cased "Location" options.
        """
        name = self.option("Name").get()
        location = self.option("Location").get().upper()

        return f"Insert {name} Control {location}"

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the "Node" input, or None otherwise.

        Args:
            requirement_name: The name of the input to return a widget for.
        """
        if requirement_name == "Node":
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def is_valid(self) -> bool:
        """
        Checks that the "Node" input and the "Name" option are given.
        """
        if not self.input("Node").get():
            log.warning(f"{self.label()} : Node is not set")
            return False

        if not self.option("Name").get():
            log.warning(f"{self.label()} : Name is empty, so the control cannot be named")
            return False

        return True

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

        control = aniseed_toolkit.rig.control.create(
            description=self.option("Name").get(),
            location=self.option("Location").get(),
            parent=parent_name,
            config=self.config,
            shape=self.option("Shape").get(),
            match_to=self.option("Match Transform To").get() or parent_name,
        )
        self.output("Control").set(control.ctl)

        node.set_parent(control.ctl)

        return True
