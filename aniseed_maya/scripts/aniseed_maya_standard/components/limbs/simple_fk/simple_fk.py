"""
Provides the "Limb : Simple Fk" component, which creates an fk control for
each joint given in Joints To Drive and constrains the joint to it. Controls
are chained (or flat, if Flat Hierarchy is set) and can optionally have an
offset control. It is also heavily commented as an example component.
"""
import os
import mref
import aniseed
import aniseed_toolkit
from aniseed_maya_standard.mixins import MirrorMixin


class SimpleFkComponent(aniseed.RigComponent, MirrorMixin):

    identifier = "Limb : Simple Fk"
    icon = os.path.join(
        os.path.dirname(__file__),
        "simple_fk.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent and Joints To Drive inputs, the naming, shape and
        hierarchy/offset control options and the root and tip control outputs.
        """
        super(SimpleFkComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            group="Control Rig",
        )

        # -- Requirements are things we must have given to us in order to
        # -- build. So for the simple fk we need to know the joints we want
        # -- to drive as well as the parent
        self.declare_input(
            name="Joints To Drive",
            validate=True,
            group="Required Joints",
        )

        # -- Options are there to allow a user to tailor the result. They should'nt
        # -- be mandatory
        self.declare_option(
            name="Label",
            value="Control",
            group="Naming",
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

        # -- Note: this option is not currently used during the build, but
        # -- is kept as it is serialised into existing rigs
        self.declare_option(
            name="Lock and Hide",
            value=list(),
            group="Behaviour",
        )

        self.declare_option(
            name="Flat Hierarchy",
            value=False,
            group="Behaviour",
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

        self.declare_output("Root Control")
        self.declare_output("Tip Control")

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output.
        """
        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def option_widget(self, option_name):
        """
        Returns a shape selector for Shape, a location selector for Location
        and a text list for Lock and Hide.
        """

        # -- We can use this function to tailor how we visualise certain options.
        # -- In this case, we want to show a list of shapes to the user for them
        # -- to select from (a drop down menu).
        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                default_item=self.option("Shape").get() or ""
            )

        # -- Here we're providing a list of locations from the configuration
        # -- component to pick from
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

        if option_name == "Lock and Hide":
            return aniseed.widgets.TextList()

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the Parent and an object list for the
        Joints To Drive.
        """
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Joints To Drive":
            return aniseed.widgets.ObjectList()

    def is_valid(self) -> bool:
        """
        Checks that at least one joint has been given to drive.
        """

        # -- We can use this function to test that we think the component
        # -- is valid before its built. In this case we're validating that
        # -- the joints have been set, but actually we could have just
        # -- set validate=True in the self.declare_input() call and it
        # -- would do that for us.
        joints = self.input("Joints To Drive").get()

        if not joints:
            print("No joints given to drive")
            return False

        return True

    def run(self):
        """
        Creates an fk control (plus an optional offset control) for each joint
        to drive, parent and scale constraining the joint to it. Controls are
        chained unless Flat Hierarchy is set. Sets the root/tip outputs and
        declares an "Fk Control N" output for every control.
        """

        # -- Here we're accessing the values of the requirements for this
        # -- component. In this case, getting the parent and the joints
        parent = self.input("Parent").get()
        joints_to_drive = self.input("Joints To Drive").get()

        # -- Note that we're accessing the options here too, in order to allow
        # -- the user to tailor the result
        label = self.option("Label").get()
        location = self.option("Location").get()

        for idx, joint_to_drive in enumerate(joints_to_drive):

            # -- Aniseed gives us a function to create a control but it does not
            # -- force you to use it. Aniseed does not expect a formal control
            # -- to be used, but it is easier.
            control = aniseed_toolkit.rig.control.create(
                description=label,
                location=location,
                shape=self.option("Shape").get(),
                config=self.config,
                parent=parent,
                match_to=joint_to_drive,
                rotate_shape=[0, 0, 90],
            )
            driver = control.ctl

            if self.option("Add Offset Control").get():
                driver = aniseed_toolkit.rig.control.add_offset_control(
                    control,
                    description=label,
                    location=location,
                    config=self.config,
                    shape="core_cube",
                    match_to=joint_to_drive,
                    rotate_shape=[0, 0, 90],
                ).ctl

            # -- Set our outputs
            if not self.output("Root Control").get():
                self.output("Root Control").set(control.ctl)

            self.output("Tip Control").set(control.ctl)

            # -- There is no smoke and mirrors with how an aniseed rig controls
            # -- a skeleton. Its what-you-see-is-what-you-get. So we're just
            # -- using maya to constrain the joint to the control
            aniseed_toolkit.scene.constraints.parent_and_scale(
                driver,
                joint_to_drive,
                maintain_offset=False,
            )

            if not self.option("Flat Hierarchy").get():
                parent = control.ctl

            # -- Declare an output for each control
            self.declare_output(f"Fk Control {idx}")
            self.output(f"Fk Control {idx}").set(control.ctl)

        return True

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the joints to drive, in order. Empty if none are set.
        """
        return list(self.input("Joints To Drive").get() or [])

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the first joint to drive. Empty if there is
        no joint or it has no parent.
        """
        joints = self.input("Joints To Drive").get() or []
        if not joints or not mref.objExists(joints[0]):
            return ""

        parent = mref.get(joints[0]).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's joints if they already exist (the search and
        replaced names), otherwise copies the original joints into the mirrored
        hierarchy for this component to drive.
        """
        original_joints = list(mirrored_from.input("Joints To Drive").get() or [])
        mirrored_joints = list(self.input("Joints To Drive").get() or [])

        if not original_joints:
            return

        if self.mirror_mixin_counterparts_exist(original_joints, mirrored_joints):
            return

        self.input("Joints To Drive").set(
            self.mirror_mixin_copy_nodes(original_joints),
        )
