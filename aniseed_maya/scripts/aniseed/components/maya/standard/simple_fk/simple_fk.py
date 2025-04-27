import os
import aniseed
import aniseed_toolkit
import maya.cmds as mc


class SimpleFkComponent(aniseed.RigComponent):

    identifier = "Standard : Simple Fk"
    icon = os.path.join(
        os.path.dirname(__file__),
        "simple_fk.png",
    )

    def __init__(self, *args, **kwargs):
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

        self.declare_output("Root Control")
        self.declare_output("Tip Control")

    def option_widget(self, option_name):

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
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Joints To Drive":
            return aniseed.widgets.ObjectList()

    def is_valid(self) -> bool:

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

        # -- Here we're accessing the values of the requirements for this
        # -- component. In this case, getting the parent and the joints
        parent = self.input("Parent").get()
        joints_to_drive = self.input("Joints To Drive").get()

        for joint_to_drive in joints_to_drive:

            # -- Aniseed gives us a function to create a control but it does not
            # -- force you to use it. Aniseed does not expect a formal control
            # -- to be used, but it is easier.
            # -- Note that we're accessing the options here too, in order to allow
            # -- the user to tailor the result
            control = aniseed_toolkit.run("Create Control",
            description=self.option("Label").get(),
                location=self.option("Location").get(),
                shape=self.option("Shape").get(),
                config=self.config,
                parent=parent,
                match_to=joint_to_drive,
            )

            # -- Set our outputs
            if not self.output("Root Control").get():
                self.output("Root Control").set(control.ctl)

            self.output("Tip Control").set(control.ctl)

            # -- There is no smoke and mirrors with how an aniseed rig controls
            # -- a skeleton. Its what-you-see-is-what-you-get. So we're just
            # -- using maya to constrain the joint to the control
            mc.parentConstraint(
                control.ctl,
                joint_to_drive,
                maintainOffset=False,
            )

            mc.scaleConstraint(
                control.ctl,
                joint_to_drive,
                maintainOffset=False,
            )

            if not self.option("Flat Hierarchy").get():
                parent = control.ctl

        return True
