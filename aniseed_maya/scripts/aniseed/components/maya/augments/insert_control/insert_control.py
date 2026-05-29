import aniseed
import aniseed_toolkit

from maya import cmds


class InsertControlComponent(aniseed.RigComponent):
    """
    Inserts a new control between a parent node and its existing
    children. The control is created as a child of ``Parent`` and,
    if "Move All Children Under Control" is enabled, every transform
    child of ``Parent`` is re-parented under the new control so the
    control sits in the middle of the hierarchy.
    """

    identifier = "Augment : Insert Control"

    def __init__(self, *args, **kwargs):
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

        self.declare_option(
            name="Match Transform To",
            description=(
                "Optional node whose world transform the new control "
                "will be matched to. Leave empty to match the parent."
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
                "Location token (c/l/r/f/b) used when generating the "
                "control's name. Inherited from the parent component "
                "when added to the stack."
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
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def suggested_label(self):
        name = self.option("Name").get()
        location = self.option("Location").get().upper()

        return f"Insert {name} Control {location}"

    def run(self) -> bool:

        parent = self.input("Parent").get()
        children = cmds.listRelatives(parent, children=True, type="transform") or list()

        control = aniseed_toolkit.run("Create Control",
            description=self.option("Name").get(),
            location=self.option("Location").get(),
            parent=parent,
            config=self.config,
            shape=self.option("Shape").get(),
            match_to=self.option("Match Transform To").get(),
        )

        self.output("Control").set(control)

        if self.option("Move All Children Under Control").get():
            for child in children:
                cmds.parent(
                    child,
                    control,
                )

        return True
