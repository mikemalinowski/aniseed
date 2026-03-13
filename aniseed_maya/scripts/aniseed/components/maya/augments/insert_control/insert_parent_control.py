import mref
import aniseed
import aniseed_toolkit
import maya.cmds as mc


class InsetParentControlComponent(aniseed.RigComponent):
    """
    Creates a control as a child of the nodes parent and then makes
    the given node a child of the new control.
    """

    identifier = "Augment : Add Parent Control"

    def __init__(self, *args, **kwargs):
        super(InsetParentControlComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Node",
            value="",
            validate=True,
            group="Required Joint",
        )

        self.declare_option(
            name="Match Transform To",
            value="",
            group="Behaviour",
        )

        self.declare_option(
            name="Name",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            value="core_cube",
            group="Visuals",
        )

        self.declare_output(
            "Control",
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

    def input_widget(self, requirement_name: str) :
        if requirement_name == "Node":
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def suggested_label(self):
        name = self.option("Name").get()
        location = self.option("Location").get().upper()

        return f"Insert {name} Control {location}"

    def run(self) -> bool:

        node = self.input("Node").get()
        parent = mref.get(node).parent()

        control = aniseed_toolkit.run("Create Control",
            description=self.option("Name").get(),
            location=self.option("Location").get(),
            parent=parent.name(),
            config=self.config,
            shape=self.option("Shape").get(),
            match_to=self.option("Match Transform To").get(),
        )

        mc.parent(
            node,
            control.ctl,
        )

        self.output("Control").set(control.ctl)

        return True
