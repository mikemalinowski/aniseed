import os
import bony
import typing
import shapeshift

import qute
import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
class FKSpineComponent(aniseed.RigComponent):

    identifier = "Standard : FK Spine"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(FKSpineComponent, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="hip",
            description="The root of the spine",
            validate=True,
            value="",
            group="Required Joints",
        )

        self.declare_requirement(
            name="chest",
            description="The tip of the spine",
            validate=True,
            value="",
            group="Required Joints",
        )

        self.declare_requirement(
            name="parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
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

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name):

        if requirement_name == "chest":
            return aniseed.widgets.everywhere.GraphicalItemSelector(
                component=self,
                filepath=os.path.join(
                    os.path.dirname(__file__),
                    "spine.json",
                )
            )

        if requirement_name == "hip":
            return self.IGNORE_OPTION_FOR_UI

        if requirement_name == "parent":
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Joints": self.build_skeleton,
        }

    # ----------------------------------------------------------------------------------
    def is_valid(self):

        hip = self.requirement("hip").get()
        chest = self.requirement("chest").get()

        if not mc.objExists(hip):
            print(f"{hip} does not exist")
            return False

        if not mc.objExists(chest):
            print(f"{chest} does not exist")
            return False

        facind_dir = bony.direction.get_chain_facing_direction(
            start=hip,
            end=chest,
            epsilon=20,
        )

        if facind_dir != bony.direction.Facing.PositiveX:
            print("The spine joints are expected to point along positive x")
            return False

        return True

    # ----------------------------------------------------------------------------------
    def run(self):

        hip_bone = self.requirement("hip").get()
        chest_bone = self.requirement("chest").get()

        align_to_world = self.option("Align Controls To World").get()

        joints = []
        next_joint = chest_bone

        # -- Get all the joints that make up part of the continuous hierarchy
        long_name = mc.ls(chest_bone, long=True)[0]
        chain = long_name.split("|")
        joints = chain[chain.index(hip_bone):]

        control_parent = self.requirement("parent").get()

        kwargs = dict(
            config=self.config,
            shape="core_rounded_square",
            rotate_shape=[90, 90, 0],
        )

        hip_control = aniseed.control.create(
            description="Hip" + self.option("Label").get(),
            location=self.option("Location").get(),
            shape_scale=24,
            parent=control_parent,
            match_to=hip_bone,
            **kwargs
        )
        self._align(hip_control, align_to_world)

        # -- Store the output
        self.output("Hip").set(hip_control)

        sway_control = aniseed.control.create(
            description="HipSway" + self.option("Label").get(),
            location=self.option("Location").get(),
            shape_scale=20,
            parent=hip_control,
            match_to=hip_bone,
            **kwargs
        )
        self._align(sway_control, align_to_world)

        mc.parentConstraint(
            sway_control,
            hip_bone,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            sway_control,
            hip_bone,
            maintainOffset=True,
        )

        control_parent = hip_control

        for idx, joint in enumerate(joints[1:-1]):

            spine_control = aniseed.control.create(
            description="Spine" + self.option("Label").get(),
                location=self.option("Location").get(),
                shape_scale=16,
                parent=control_parent,
                match_to=joint,
                **kwargs
            )
            self._align(spine_control, align_to_world)

            mc.parentConstraint(
                spine_control,
                joint,
                maintainOffset=True,
            )

            mc.scaleConstraint(
                spine_control,
                joint,
                maintainOffset=True,
            )

            control_parent = spine_control

        chest_control = aniseed.control.create(
            description="Chest" + self.option("Label").get(),
            location=self.option("Location").get(),
            shape_scale=24,
            parent=control_parent,
            match_to=chest_bone,
            **kwargs
        )
        self._align(chest_control, align_to_world)

        # -- Store the chest output
        self.output("Chest").set(chest_control)

        mc.parentConstraint(
            chest_control,
            chest_bone,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            chest_control,
            chest_bone,
            maintainOffset=True,
        )

        return True

    # ----------------------------------------------------------------------------------
    def _align(self, node, perform_alignment):

        if not perform_alignment:
            return

        org = aniseed.control.get_classification(
            node,
            component_type="org",
        )

        mc.xform(
            org,
            rotation=[0, 0, 0],
            worldSpace=True,
        )

        shapeshift.rotate_shape(
            node,
            x=0,
            y=0,
            z=90,
        )

    # ----------------------------------------------------------------------------------
    def build_skeleton(self, joint_count=None):

        if not joint_count:
            joint_count = qute.utilities.request.text(
                title="Joint Count",
                label="How many joints (including hip and chest) do you want?"
            )

            if not joint_count:
                return

            joint_count = int(joint_count)

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        increment = 25 / (joint_count - 1)

        hip_joint = aniseed.joint.create(
            description="Hip" + self.option("Label").get(),
            location=self.option("Location").get(),
            parent=parent,
            match_to=parent,
            config=self.config
        )
        self.requirement("hip").set(hip_joint)

        mc.xform(
            hip_joint,
            rotation=[-90, 0, 90],
            translation=[0, 105, 0],
            worldSpace=True,
        )

        parent = hip_joint

        for idx in range(joint_count-2):
            spine_joint = aniseed.joint.create(
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

        chest_joint = aniseed.joint.create(
            description="Chest" + self.option("Label").get(),
            location=self.option("Location").get(),
            parent=parent,
            match_to=parent,
            config=self.config
        )
        self.requirement("chest").set(chest_joint)

        mc.setAttr(
            f"{chest_joint}.translateX",
            increment
        )

        mc.select(hip_joint)
