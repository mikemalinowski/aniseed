import mref
import aniseed
import aniseed_toolkit
from maya import cmds


class JointlessSingular(aniseed.RigComponent):
    """
    A basic component which creates a single joint and a single control
    """

    identifier = "Basic : Singular (Jointless)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the generated control's org will be parented under",
            group="Control Rig",
        )

        self.declare_input(
            name="Guide",
            value="",
            description="Name of the guide for placement",
            group="Control Rig",
        )

        self.declare_option(
            name="Description",
            description=(
                "Descriptive token used when naming the control (and the "
                "auto-created joint, if ``Create Joint`` is enabled)."
            ),
            value="Singular",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            description="Location token (e.g. md/lf/rt) applied to generated node names",
            value=self.config.middle,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            description="Shape used for the generated control (and the offset control, if enabled)",
            value="core_cube",
            group="Visuals",
            pre_expose=True,
        )

        self.declare_option(
            name="Add Offset Control",
            description=(
                "If enabled, a second control is created and parented under "
                "the main control. The offset control becomes the driving "
                "control for the joint, letting animators add layered offsets "
                "on top of the main control."
            ),
            value=False,
            group="Behaviour",
            pre_expose=True,
        )

        self.declare_option(
            name="Align Control To World",
            description=(
                "If enabled, the generated control is aligned to world "
                "orientation instead of inheriting the joint's orientation."
            ),
            value=False,
            group="Behaviour",
        )

        self.declare_output(
            name="Control",
            description="The main control created by this component",
            is_default=True,
        )
        self.declare_output(
            name="Offset Control",
            description=(
                "The optional offset control created when ``Add Offset "
                "Control`` is enabled. Unset otherwise."
            ),
            is_default=False,
        )

    def suggested_label(self):
        return self.option("Description").get()

    def option_widget(self, option_name):

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(default_item=self.option("Shape").get() or "")

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

        return None

    def input_widget(self, requirement_name):
        if requirement_name in ["Parent", "Guide"]:
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def on_enter_stack(self):
        super().on_enter_stack()
        self.input("Parent").hook_to_parent()

    def is_valid(self) -> bool:
        if not self.input("Parent").get(resolved=False):
            print("You must specify a Parent")
            return False

        guide = self.input("Guide").get()
        if not guide or not cmds.objExists(guide):
            print("You must specify a valid Guide")
            return False

        return True

    def run(self):

        # -- Lets read our inputs
        description = self.option("Description").get()
        location = self.option("Location").get()
        shape = self.option("Shape").get()
        parent = self.input("Parent").get()
        guide = self.input("Guide").get()

        control = aniseed_toolkit.control.create(
            description=description,
            location=location,
            config=self.config,
            shape=shape,
            parent=parent,
            match_to=guide,
        )
        driving_control = control

        if self.option("Align Control To World").get():
            cmds.xform(
                driving_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        if self.option("Add Offset Control").get():
            driving_control = aniseed_toolkit.control.create(
                description=description + "_offset",
                location=location,
                config=self.config,
                shape=shape,
                parent=control.ctl,
                match_to=guide,
            )
            self.output("Offset Control").set(driving_control.ctl)

        self.output("Control").set(control.ctl)
        return True
