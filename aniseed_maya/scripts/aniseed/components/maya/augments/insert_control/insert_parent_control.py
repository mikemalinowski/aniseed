import mref
import aniseed
import aniseed_toolkit

from maya import cmds


class InsertParentControlComponent(aniseed.RigComponent):
    """
    Creates a control as a child of the nodes parent and then makes
    the given node a child of the new control.
    """

    identifier = "Augment : Add Parent Control"

    def __init__(self, *args, **kwargs):
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
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                default_item=self.option("Shape").get(),
            )

        if option_name == "Match Transform To":
            return aniseed.widgets.ObjectSelector(component=self)

    def input_widget(self, requirement_name: str):
        if requirement_name == "Node":
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def suggested_label(self):
        name = self.option("Name").get()
        location = self.option("Location").get().upper()

        return f"Insert {name} Control {location}"

    def run(self) -> bool:

        node = self.input("Node").get()
        node_parent = mref.get(node).parent()
        # -- A node at the world root has no parent; pass None through
        # -- so the toolkit creates the control under the world.
        parent_name = node_parent.name() if node_parent else None

        control = aniseed_toolkit.run("Create Control",
            description=self.option("Name").get(),
            location=self.option("Location").get(),
            parent=parent_name,
            config=self.config,
            shape=self.option("Shape").get(),
            match_to=self.option("Match Transform To").get(),
        )

        cmds.parent(
            node,
            control.ctl,
        )

        self.output("Control").set(control.ctl)

        return True
