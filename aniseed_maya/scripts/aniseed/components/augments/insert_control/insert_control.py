import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
class InsertControlComponent(aniseed.RigComponent):

    identifier = "Augment : Insert Control"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(InsertControlComponent, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Parent",
            value="",
            validate=True,
            group="Required Joint",
        )

        self.declare_option(
            name="Move All Children Under Control",
            value=True,
            group="Behaviour",
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

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                default_item=self.option("Shape").get(),
            )

        if option_name == "Match Transform To":
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name: str) :
        if requirement_name == "Parent":
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        return None

    # ----------------------------------------------------------------------------------
    def suggested_label(self):
        name = self.option("Name").get()
        location = self.option("Location").get().upper()

        return f"Insert {name} Control {location}"

    # ----------------------------------------------------------------------------------
    def run(self) -> bool:

        parent = self.requirement("Parent").get()
        children = mc.listRelatives(parent, children=True) or list()
        shapes = mc.listRelatives(parent, shapes=True) or list()

        control = aniseed.control.create(
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

                if child in shapes:
                    continue

                mc.parent(
                    child,
                    control,
                )

        return True
