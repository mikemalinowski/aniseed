import mref
import aniseed
import aniseed_toolkit
from maya import cmds


class Singular(aniseed.RigComponent):
    """
    A basic component which creates a single joint and a single control
    """

    identifier = "Basic : Singular"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the generated control's org will be parented under",
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
            name="Create Joint",
            description=(
                "If enabled when the component first enters the stack, a "
                "driving joint is created automatically (parented to the "
                "current Maya selection) and wired into the ``Joint`` input."
            ),
            value=True,
            group="Creation",
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

        self.declare_option(
            name="Has Initialised",
            description=(
                "Internal flag: True once the component's first-add "
                "joint-creation has run. Should not be edited by hand."
            ),
            value=False,
            hidden=True,
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
        if requirement_name in ["Parent", "Joint"]:
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def on_enter_stack(self):
        super().on_enter_stack()

        initialised_option = self.option("Has Initialised")
        joint_option = self.option("Create Joint")
        if initialised_option.get():
            return

        initialised_option.set(True)
        joint_option.set_hidden(True)

        if not joint_option.get():
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

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

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

        # -- Lets read our inputs
        description = self.option("Description").get()
        location = self.option("Location").get()
        shape = self.option("Shape").get()
        parent = self.input("Parent").get()
        joint = self.input("Joint").get()

        control = aniseed_toolkit.control.create(
            description=description,
            location=location,
            config=self.config,
            shape=shape,
            parent=parent,
            match_to=joint,
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
                match_to=joint,
            )
            self.output("Offset Control").set(driving_control.ctl)

        cmds.parentConstraint(
            driving_control.ctl,
            joint,
            maintainOffset=True,
        )

        cmds.scaleConstraint(
            driving_control.ctl,
            joint,
            maintainOffset=True,
        )

        self.output("Control").set(control.ctl)