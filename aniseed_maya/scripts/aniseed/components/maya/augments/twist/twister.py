import os
import aniseed
import aniseed_toolkit
import maya.cmds as mc


class TwisterComponent(aniseed.RigComponent):

    identifier = "Augment : Twister"
    icon = os.path.join(
        os.path.dirname(__file__),
        "twister.png",
    )

    def __init__(self, *args, **kwargs):
        super(TwisterComponent, self).__init__(*args, **kwargs)

        self.builder = None

        self.declare_input(
            name="Parent",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Joints",
            description="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Root",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Tip",
            validate=True,
            group="Required Joints",
        )

        self.declare_option(
            name="Descriptive Prefix",
            value="",
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
            name="Constrain Root",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Constrain Tip",
            value=True,
            group="Behaviour",
        )

        self.declare_output("Twisters")

    def option_widget(self, option_name):

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                default_item=self.option("Shape").get()
            )

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(
                config=self.config,
            )

        if option_name == "Lock and Hide":
            return aniseed.widgets.TextList()

    def input_widget(self, requirement_name):
        if requirement_name == "Joints":
            return aniseed.widgets.ObjectList()

        if requirement_name == "Root Driver":
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Tip Driver":
            return aniseed.widgets.ObjectSelector(component=self)

    def is_valid(self) -> bool:

        joints = self.input("Joints To Drive").get()

        if not joints:
            print("No joints given to drive")
            return False

        facing_direction = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            start=joints[0],
            end=joints[-1],
        )
        if facing_direction == facing_direction.Unknown:
            print("Not a valid facing direction")
            return False

        return True

    def run(self):

        joints_to_drive = self.input("Joints").get()
        root_driver = self.input("Root").get()
        tip_driver = self.input("Tip").get()
        parent = self.input("Parent").get()

        twist_builder = aniseed_toolkit.run(
            "Create Twist Setup",
            twist_count=len(joints_to_drive),
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            config=self.config,
        )

        mc.parent(
            twist_builder.org(),
            parent,
        )

        mc.xform(
            twist_builder.org(),
            matrix=mc.xform(
                root_driver,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        mc.xform(
            twist_builder.tip(),
            translation=mc.xform(
                tip_driver,
                query=True,
                translation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        mc.xform(
            twist_builder.tip(),
            rotation=mc.xform(
                twist_builder.org(),
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        if self.option("Constrain Root").get():
            mc.parentConstraint(
                root_driver,
                twist_builder.root(),
                maintainOffset=True,
            )

        if self.option("Constrain Tip").get():
            mc.parentConstraint(
                tip_driver,
                twist_builder.tip(),
                maintainOffset=True,
            )

        twist_builder.reset_aim()

        total_distance = aniseed_toolkit.run(
            "Distance Between",
            root_driver,
            tip_driver,
            print_result=False,
        )

        for idx, joint in enumerate(joints_to_drive):

            root_distance = aniseed_toolkit.run(
                "Distance Between",
                root_driver,
                joint,
                print_result=False,
            )

            factor = root_distance / total_distance

            twist_builder.set_blend_factor(
                idx,
                factor,
            )

            mc.parentConstraint(
                twist_builder.twists()[idx],
                joint,
                maintainOffset=True,
            )

        self.builder = twist_builder

        self.output("Twisters").set(
            twist_builder.twists(),
        )

        return True
