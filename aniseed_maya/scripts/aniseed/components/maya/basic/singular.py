import aniseed
import aniseed_toolkit
import mref
from maya import cmds


class Singular(aniseed.RigComponent):
    """
    A basic component which creates a single joint and a single control
    """

    identifier = "Basic : Singular"

    def __init__(self, *args, **kwargs):
        aniseed.RigComponent.__init__(self, *args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="Control Parent",
            group="Control Rig",
        )

        self.declare_input(
            name="Joint",
            value="",
            description="Name of the joint to drive",
            group="Joints",
        )

        self.declare_option(
            name="Description",
            value="Singular",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            value=self.config.middle,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            value="core_cube",
            group="Visuals",
            pre_expose=True,
        )

        self.declare_option(
            name="Create Joint",
            value=True,
            group="Creation",
            pre_expose=True,
        )

        self.declare_option(
            name="Align Control To World",
            value=False,
            group="Behaviour",
        )

        self.declare_output(name="Control")

    def suggested_label(self):
        return self.option("Description").get()

    def option_widget(self, option_name):

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(default_item=self.option("Shape").get() or "")

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    def input_widget(self, requirement_name):
        if requirement_name in ["Parent", "Joint"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def on_enter_stack(self):
        if not self.option("Create Joint").get():
            return

        selection = mref.selected()
        parent = selection[0] if selection else None

        joint = mref.create("joint", parent=parent)
        joint.rename(
            self.config.generate_name(
                classification=self.config.joint,
                description=self.option("Description").get(),
                location=self.option("Location").get(),
            ),
        )
        if parent:
            joint.match_to(parent)

        self.input("Joint").set(joint.name())

    def is_valid(self) -> bool:
        if not self.input("Parent").get(resolved=False):
            print("You must specify a Parent")
            return False

        joint = self.input("Joint").get()
        if not joint or not cmds.objExists(joint):
            print("You must specify a valid joint")
            return False

        return True

    def run(self):

        control = aniseed_toolkit.control.create(
            description=self.option("Description").get(),
            location=self.option("Location").get(),
            config=self.config,
            shape=self.option("Shape").get(),
            parent=self.input("Parent").get(),
            match_to=self.input("Joint").get(),
        )

        cmds.parentConstraint(
            control.ctl,
            self.input("Joint").get(),
            maintainOffset=True,
        )

        cmds.scaleConstraint(
            control.ctl,
            self.input("Joint").get(),
            maintainOffset=True,
        )

        self.output("Control").set(control.ctl)