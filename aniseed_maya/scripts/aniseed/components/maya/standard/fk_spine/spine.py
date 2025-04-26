import os
import typing
import aniseed
import qtility
import aniseed_toolkit
import maya.cmds as mc


class FKSpineComponent(aniseed.RigComponent):
    """
    This component will create a rig where all controls are sequential except the
    hip sway which can be manipulated without adjusting the children.
    """

    identifier = "Standard : FK Spine"
    icon = os.path.join(
        os.path.dirname(__file__),
        "spine.png",
    )

    def __init__(self, *args, **kwargs):
        super(FKSpineComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Hip",
            description="The root of the spine",
            validate=True,
            value="",
            group="Required Joints",
        )

        self.declare_input(
            name="Chest",
            description="The tip of the spine",
            validate=True,
            value="",
            group="Required Joints",
        )

        self.declare_option(
            name="Label",
            value="",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="lf",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Align Controls To World",
            value=True,
            group="Behaviour",
        )

        self.declare_output(name="Hip")
        self.declare_output(name="Chest")

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    def input_widget(self, requirement_name):
        if requirement_name in ["Hip", "Chest", "Parent"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Joints": self.user_func_build_skeleton,
        }

    def is_valid(self):

        hip = self.input("Hip").get()
        chest = self.input("Chest").get()

        if not mc.objExists(hip):
            print(f"{hip} does not exist")
            return False

        if not mc.objExists(chest):
            print(f"{chest} does not exist")
            return False

        facing_dir = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            start=hip,
            end=chest,
            epsilon=20,
        )

        if facing_dir != facing_dir.PositiveX:
            print("The spine joints are expected to point along positive x")
            return False

        return True

    def run(self):

        hip_bone = self.input("Hip").get()
        chest_bone = self.input("Chest").get()

        align_to_world = self.option("Align Controls To World").get()

        joints = []
        next_joint = chest_bone

        # -- Get all the joints that make up part of the continuous hierarchy
        long_name = mc.ls(chest_bone, long=True)[0]
        chain = long_name.split("|")
        joints = chain[chain.index(hip_bone):]

        control_parent = self.input("Parent").get()

        kwargs = dict(
            config=self.config,
            shape="core_rounded_square",
            rotate_shape=[90, 90, 0],
        )

        hip_control = aniseed_toolkit.run(
            "Create Control",
            description="Hip" + self.option("Label").get(),
            location=self.option("Location").get(),
            shape_scale=24,
            parent=control_parent,
            match_to=hip_bone,
            **kwargs
        )
        self._align_control(hip_control, align_to_world)

        # -- Store the output
        self.output("Hip").set(hip_control)

        sway_control = aniseed_toolkit.run(
            "Create Control",
            description="HipSway" + self.option("Label").get(),
            location=self.option("Location").get(),
            shape_scale=20,
            parent=hip_control.ctl,
            match_to=hip_bone,
            **kwargs
        )
        self._align_control(sway_control, align_to_world)

        mc.parentConstraint(
            sway_control.ctl,
            hip_bone,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            sway_control.ctl,
            hip_bone,
            maintainOffset=True,
        )

        control_parent = hip_control.ctl

        for idx, joint in enumerate(joints[1:-1]):

            spine_control = aniseed_toolkit.run(
                "Create Control",
                description="Spine" + self.option("Label").get(),
                location=self.option("Location").get(),
                shape_scale=16,
                parent=control_parent,
                match_to=joint,
                **kwargs
            )
            self._align_control(spine_control, align_to_world)

            mc.parentConstraint(
                spine_control.ctl,
                joint,
                maintainOffset=True,
            )

            mc.scaleConstraint(
                spine_control.ctl,
                joint,
                maintainOffset=True,
            )

            control_parent = spine_control.ctl

        chest_control = aniseed_toolkit.run(
            "Create Control",
            description="Chest" + self.option("Label").get(),
            location=self.option("Location").get(),
            shape_scale=24,
            parent=control_parent,
            match_to=chest_bone,
            **kwargs
        )
        self._align_control(chest_control, align_to_world)

        # -- Store the chest output
        self.output("Chest").set(chest_control.ctl)

        mc.parentConstraint(
            chest_control.ctl,
            chest_bone,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            chest_control.ctl,
            chest_bone,
            maintainOffset=True,
        )

        return True

    def _align_control(self, control, perform_align_controlment):

        if not perform_align_controlment:
            return

        mc.xform(
            control.org,
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        aniseed_toolkit.run(
            "Rotate Shapes",
            control.ctl,
            x=0,
            y=0,
            z=90,
        )

    def user_func_build_skeleton(self, joint_count=None):

        if not joint_count:
            joint_count = qtility.request.text(
                title="Joint Count",
                message="How many joints (including hip and chest) do you want?"
            )

            if not joint_count:
                return

            joint_count = int(joint_count)

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        increment = 25 / (joint_count - 1)

        hip_joint = aniseed_toolkit.run(
            "Create Joint",
            description="Hip" + self.option("Label").get(),
            location=self.option("Location").get(),
            parent=parent,
            match_to=parent,
            config=self.config
        )
        self.input("Hip").set(hip_joint)

        mc.xform(
            hip_joint,
            rotation=[-90, 0, 90],
            translation=[0, 105, 0],
            worldSpace=True,
        )

        parent = hip_joint

        for idx in range(joint_count-2):
            spine_joint = aniseed_toolkit.run(
                "Create Joint",
                description="Spine" + self.option("Label").get(),
                location=self.option("Location").get(),
                parent=parent,
                match_to=parent,
                config=self.config
            )

            mc.setAttr(
                f"{spine_joint}.translateX",
                increment
            )

            parent = spine_joint

        chest_joint = aniseed_toolkit.run(
            "Create Joint",
            description="Chest" + self.option("Label").get(),
            location=self.option("Location").get(),
            parent=parent,
            match_to=parent,
            config=self.config
        )
        self.input("Chest").set(chest_joint)

        mc.setAttr(
            f"{chest_joint}.translateX",
            increment
        )

        mc.select(hip_joint)
