import os
import json
import mref
import qtility
import aniseed
import aniseed_toolkit
from maya import cmds



class FaceComponent(aniseed.RigComponent):
    """
    This will automatically create eye and mouth components as well
    as a series of singulars to represent face bones. It will then
    create a transform mixer and a construct a facial control rig
    to drive it all.
    """

    identifier = "Limb : Face"

    with open(os.path.join(os.path.dirname(__file__), "face_data.json"), "r") as f:
        face_bones = json.load(f)

    pose_list = [

        "left_lip_corner_push_in",
        "left_lip_corner_push_in_jaw_open",
        "left_lip_corner_pull_out",
        "left_lip_corner_pull_up",
        "left_lip_corner_pull_down",
        "left_lip_sneer_lower",
        "left_lip_sneer_upper",
        "left_cheek_suck",
        "left_cheek_blow",
        "left_nose_flare",
        "left_squint_inner",
        "left_squint_outer",

        "right_lip_corner_push_in",
        "right_lip_corner_push_in_jaw_open",
        "right_lip_corner_pull_out",
        "right_lip_corner_pull_up",
        "right_lip_corner_pull_down",
        "right_lip_sneer_lower",
        "right_lip_sneer_upper",
        "right_cheek_suck",
        "right_cheek_blow",
        "right_nose_flare",
        "right_squint_inner",
        "right_squint_outer",

        "upper_sneer",
        "lower_sneer",

        "upper_lip_pull",
        "lower_lip_pull",
        "upper_lip_compress",
        "lower_lip_compress",
        "upper_lip_curl_out",
        "lower_lip_curl_out",
        "upper_lip_curl_in",
        "lower_lip_curl_in",

        "left_brow_inner_up",
        "left_brow_inner_down",
        "left_brow_inner_in",
        "left_brow_outer_up",
        "left_brow_outer_down",
        "left_brow_mid_up",
        "left_brow_mid_down",

        "right_brow_inner_up",
        "right_brow_inner_down",
        "right_brow_inner_in",
        "right_brow_outer_up",
        "right_brow_outer_down",
        "right_brow_mid_up",
        "right_brow_mid_down",

        "jaw_open",
    ]

    control_groups = [
        "left_lip_corner",
        "right_lip_corner",
        "upper_lip",
        "lower_lip",
        "nose",
        "left_brow_inner",
        "left_brow_outer",
        "right_brow_inner",
        "right_brow_outer",
    ]

    def __init__(self, *args, **kwargs):
        super(FaceComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig"
        )

        self.declare_input(
            name="Attribute Host",
            value="",
            group="Control Rig",
        )
        for bone_description in self.face_bones:
            self.declare_input(
                name=f"{bone_description['name']}_{bone_description['location']}",
                value="",
                group="Joints",
            )

        self.declare_option(
            name="Mixer Data",
            value=[],
            hidden=True,
        )

        self.declare_option(
            name="Snapshot Data",
            value=None,
        )

        self.declare_option(
            name="Show Pose",
            value=None,
        )
        self.declare_option(
            name="Hide Pose",
            value=None,
        )
        self.declare_option(
            name="Mirror Pose",
            value=None,
        )

        self.declare_option(
            name="Save Data",
            value=None,
        )

        self.declare_option(
            name="Snap Pose",
            value=None,
        )

        self.declare_option(
            name="Load Data",
            value=None,
        )

        self.declare_option(
            name="Clear Data",
            value=None,
        )

        self.declare_option(
            name="Mixer",
            value="",
            hidden=False,
        )

        self.declare_option(
            name="Use Control Rig",
            value=True,
        )

        for control_label in self.control_groups:
            group = "Control : %s" % control_label.replace("_", " ").title()

            self.declare_input(
                name=f"{control_label}_control",
                value="",
                group=group,
                validate=False,
            )
            self.declare_input(
                name=f"{control_label}_parent",
                value="",
                group=group,
                validate=False,
            )

            self.declare_input(
                name=f"{control_label}_guide",
                value="",
                group=group,
                validate=False,
            )

            self.declare_input(
                name=f"{control_label}_shape",
                value="core_cube",
                group=group,
                validate=False,
            )

        self.declare_option(
            name="Mouth Target Distance Multiplier",
            value=1.0,
        )
        self.declare_option(
            name="Eye Target Distance",
            value=30,
        )
        self.declare_output("FaceRig")
        # self.declare_output("Mixer")

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Parent", "Attribute Host"]:
            return aniseed.widgets.ObjectSelector()

        if requirement_name.endswith("_shape"):
            return aniseed.widgets.ShapeSelector(default_item="core_cube")

        attribute = self.input(requirement_name)
        if attribute.group() and attribute.group().startswith("Control :"):
            return aniseed.widgets.ObjectSelector()

    def option_widget(self, option_name: str):
        if option_name == "Snapshot Data":
            return aniseed.widgets.ButtonWidget(button_name="Snapshot Data", func=self.snapshot_data)

        if option_name == "Mirror Pose":
            return aniseed.widgets.ButtonWidget(button_name="Mirror Pose", func=self.mirror_pose)

        if option_name == "Show Pose":
            return aniseed.widgets.ButtonWidget(button_name="Show Pose", func=self.show_pose)

        if option_name == "Hide Pose":
            return aniseed.widgets.ButtonWidget(button_name="Hide Pose", func=self.hide_pose)

        if option_name == "Save Data":
            return aniseed.widgets.ButtonWidget(button_name="Save Data", func=self.save_data)

        if option_name == "Load Data":
            return aniseed.widgets.ButtonWidget(button_name="Load Data", func=self.load_data)

        if option_name == "Clear Data":
            return aniseed.widgets.ButtonWidget(button_name="Clear Data", func=self.clear_data)

        if option_name == "Snap Pose":
            return aniseed.widgets.ButtonWidget(button_name="Snap Pose", func=self.snap_pose)


    def snapshot_data(self, silent=False):
        mixer_name = self.option("Mixer").get()
        # mixer_name = "transformMixer"
        if not mixer_name or not cmds.objExists(mixer_name):
            if not silent:
                qtility.request.message(
                    title="Cannot Snapshot Data",
                    message="You must build the rig before using the snapshot"
                )
            return

        mixer = aniseed_toolkit.transformation.TransformMixer(node=mixer_name)
        self.option("Mixer Data").set(mixer.serialise())

        if not silent:
            qtility.request.message(
                title="Snapshot Complete",
                message="The snapshot has been made",
            )

        return

    def save_data(self, filepath=None):

        if not filepath:
            filepath = qtility.request.filepath(
                title="Save Data",
                save=True,
            )
            if not filepath:
                return

        with open(filepath, "w") as f:
            json.dump(self.mixer().serialise(), f, indent=4)

        qtility.request.message(
            title="Save Complete",
            message="The data has been saved",
        )


    def load_data(self, filepath=None):

        if not filepath:
            filepath = qtility.request.filepath(
                title="Load Data",
                save=False,
            )
            if not filepath:
                return

        with open(filepath, "r") as f:
            self.option("Mixer Data").set(json.load(f))

        qtility.request.message(
            title="Load Complete",
            message="The data has been loaded, please rebuild the rig",
        )

    def clear_data(self):
        confirmation = qtility.request.confirmation(
            title="Clear Data",
            message="Are you sure you want to clear the data?",
        )
        if not confirmation:
            return

        self.option("Mixer Data").set([])

    def run(self) -> bool:

        parent = self.input("Parent").get()

        # -- Create the org
        org = mref.get(
            aniseed_toolkit.transforms.create(
                classification=self.config.organisational,
                description="face",
                location=self.config.middle,
                config=self.config,
                parent=parent,
            )
        )
        attribute_host = mref.get(self.input("Attribute Host").get() or org)
        visibility_attribute = attribute_host.add_attribute(
            name="direct_control_visibility",
            value=0,
            attribute_type="bool",
            keyable=True,
        )

        # -- Create the mouth
        mouth_component = self.stack.component_library.request("Limb : Mouth")(label="", stack=self.stack)
        mouth_component.input("Parent").set(org.name())
        mouth_component.input("Jaw Joint").set(self.input("jaw_middle").get())
        mouth_component.input("Upper Lip Joint").set(self.input("upper_lip_middle").get())
        mouth_component.input("Lower Lip Joint").set(self.input("lower_lip_middle").get())
        mouth_component.option("Aim Control Distance Multiplier").set(self.option("Mouth Target Distance Multiplier").get())
        mouth_component.run()

        # -- Create the eyes
        eyes_component = self.stack.component_library.request("Limb : Eyes")(label="", stack=self.stack)
        eyes_component.input("Parent").set(org.name())
        eyes_component.input("Left Eye Joint").set(self.input("eye_left").get())
        eyes_component.input("Left Upper Eye Lid Joint").set(self.input("eye_upper_lid_left").get())
        eyes_component.input("Left Lower Eye Lid Joint").set(self.input("eye_lower_lid_left").get())
        eyes_component.input("Right Eye Joint").set(self.input("eye_right").get())
        eyes_component.input("Right Upper Eye Lid Joint").set(self.input("eye_upper_lid_right").get())
        eyes_component.input("Right Lower Eye Lid Joint").set(self.input("eye_lower_lid_right").get())
        eyes_component.option("Aim Distance").set(self.option("Mouth Target Distance Multiplier").get())
        eyes_component.run()

        created_controls = dict(
            jaw_middle=mouth_component.output("Jaw Control").get(),
            upper_lip_middle=mouth_component.output("Upper Lip Control").get(),
            lower_lip_middle=mouth_component.output("Lower Lip Control").get(),
            eye_left=eyes_component.output("Left Eye Control").get(),
            eye_right=eyes_component.output("Right Eye Control").get(),
        )
        direct_controls = dict()

        # -- Create the controls for the rest of the joints
        for input_plug in self.inputs():

            if input_plug.name() in created_controls:
                print("SKIPPING %s" % input_plug.name())
                continue

            data = self.get_data_by_label(input_plug.name())

            if not data:
                print("skippingx %s" % input_plug.name())
                continue
            # -- If the bone is managed by another component, skip it
            if data["component"]:
                continue

            control = aniseed_toolkit.control.create(
                description=data["name"],
                location=data["location"],
                parent=created_controls.get(data["parent"], org.name()),
                shape="core_cube",
                config=self.config,
                match_to=input_plug.get(),
            )
            cmds.parentConstraint(
                control.ctl,
                input_plug.get(),
                maintainOffset=True,
            )

            visibility_attribute.connect(f"{control.ctl}.visibility")

            # created_controls[input_plug.name()] = control.ctl
            direct_controls[input_plug.name()] = control.off

        # -- Create the bespoke inserted controls
        for label, created_control in created_controls.items():

            data = self.get_data_by_label(label)

            # -- Create a control which we will insert into the hierarchy
            created_control = aniseed_toolkit.control.get(created_control)

            control = aniseed_toolkit.control.create(
                description=data["name"],
                location=data["location"],
                parent=mref.get(created_control.org).parent().name(),
                shape="core_cube",
                config=self.config,
                match_to=created_control.ctl,
            )
            cmds.parent(
                created_control.org,
                # created_control.off,
                control.ctl,
            )
            direct_controls[label] = control.off

        # -- Setup the blend constraint setup for the mouth
        pass
        # blended_jaw = mref.create("transform", name="blended_jaw", parent=org)
        # cmds.parentConstraint(
        #     org,
        #     blended_jaw,
        #     maintainOffset=True,
        # )
        # cns = mref.get(cmds.parentConstraint(created_controls["jaw_middle"], blended_jaw, maintainOffset=True))
        # cns.interpType.set(0) # -- No Flip
        # cns.weight_attributes()[0].set(0.5)
        # cns.weight_attributes()[1].set(0.5)
        jaw_control = mouth_component.output("Jaw Control").get()
        #
        # mouth_constraint_data = [
        #     {
        #         "constrain_this": direct_controls["upper_lip_outer_left"],
        #         "to_this": jaw_control,
        #         "weights": [0.6, 0.4]
        #     },
        #     {
        #         "constrain_this": direct_controls["upper_lip_outer_right"],
        #         "to_this": jaw_control,
        #         "weights": [0.6, 0.4]
        #     },
        #     {
        #         "constrain_this": direct_controls["lower_lip_outer_left"],
        #         "to_this": jaw_control,
        #         "weights": [0.4, 0.6]
        #     },
        #     {
        #         "constrain_this": direct_controls["lower_lip_outer_right"],
        #         "to_this": jaw_control,
        #         "weights": [0.4, 0.6]
        #     },
        #     {
        #         "constrain_this": direct_controls["upper_lip_mid_left"],
        #         "to_this": jaw_control,
        #         "weights": [0.8, 0.2]
        #     },
        #     {
        #         "constrain_this": direct_controls["upper_lip_mid_right"],
        #         "to_this": jaw_control,
        #         "weights": [0.8, 0.2]
        #     },
        #     {
        #         "constrain_this": direct_controls["lower_lip_mid_left"],
        #         "to_this": jaw_control,
        #         "weights": [0.2, 0.8]
        #     },
        #     {
        #         "constrain_this": direct_controls["lower_lip_mid_right"],
        #         "to_this": jaw_control,
        #         "weights": [0.2, 0.8]
        #     },
        #     {
        #         "constrain_this": direct_controls["upper_lip_inner_left"],
        #         "to_this": jaw_control,
        #         "weights": [1, 0]
        #     },
        #     {
        #         "constrain_this": direct_controls["upper_lip_inner_right"],
        #         "to_this": jaw_control,
        #         "weights": [1, 0]
        #     },
        #     {
        #         "constrain_this": direct_controls["lower_lip_inner_left"],
        #         "to_this": jaw_control,
        #         "weights": [0, 1]
        #     },
        #     {
        #         "constrain_this": direct_controls["lower_lip_inner_right"],
        #         "to_this": jaw_control,
        #         "weights": [0, 1]
        #     },
        #     {
        #         "constrain_this": direct_controls["dimple_left"],
        #         "to_this": jaw_control,
        #         "weights": [0.5, 0.5]
        #     },
        #     {
        #         "constrain_this": direct_controls["dimple_right"],
        #         "to_this": jaw_control,
        #         "weights": [0.5, 0.5]
        #     },
        #
        # ]

        upper_lip_control = aniseed_toolkit.control.get(direct_controls["upper_lip_middle"]).ctl
        lower_lip_control = aniseed_toolkit.control.get(direct_controls["lower_lip_middle"]).ctl
        mouth_constraint_data = [
            {
                "constrain_this": direct_controls["upper_lip_outer_left"],
                "to_this": jaw_control,
                "parent_space": upper_lip_control,
                "weights": [0.6, 0.4]
            },
            {
                "constrain_this": direct_controls["upper_lip_outer_right"],
                "to_this": jaw_control,
                "parent_space": upper_lip_control,
                "weights": [0.6, 0.4]
            },
            {
                "constrain_this": direct_controls["lower_lip_outer_left"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0.4, 0.6]
            },
            {
                "constrain_this": direct_controls["lower_lip_outer_right"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0.4, 0.6]
            },
            {
                "constrain_this": direct_controls["upper_lip_mid_left"],
                "to_this": jaw_control,
                "parent_space": upper_lip_control,
                "weights": [0.8, 0.2]
            },
            {
                "constrain_this": direct_controls["upper_lip_mid_right"],
                "to_this": jaw_control,
                "parent_space": upper_lip_control,
                "weights": [0.8, 0.2]
            },
            {
                "constrain_this": direct_controls["lower_lip_mid_left"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0.2, 0.8]
            },
            {
                "constrain_this": direct_controls["lower_lip_mid_right"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0.2, 0.8]
            },
            {
                "constrain_this": direct_controls["upper_lip_inner_left"],
                "to_this": jaw_control,
                "parent_space": upper_lip_control,
                "weights": [1, 0]
            },
            {
                "constrain_this": direct_controls["upper_lip_inner_right"],
                "to_this": jaw_control,
                "parent_space": upper_lip_control,
                "weights": [1, 0]
            },
            {
                "constrain_this": direct_controls["lower_lip_inner_left"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0, 1]
            },
            {
                "constrain_this": direct_controls["lower_lip_inner_right"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0, 1]
            },
            {
                "constrain_this": direct_controls["dimple_left"],
                "to_this": jaw_control,
                "parent_space": org.name(),
                "weights": [0.5, 0.5]
            },
            {
                "constrain_this": direct_controls["dimple_right"],
                "to_this": jaw_control,
                "parent_space": org.name(),
                "weights": [0.5, 0.5]
            },

        ]
        for constraint_data in mouth_constraint_data:
            constrained = mref.get(constraint_data["constrain_this"]).parent().name()
            cmds.parentConstraint(
                constraint_data["parent_space"],
                constrained,
                maintainOffset=True,
            )
            cns = mref.get(
                cmds.parentConstraint(
                    constraint_data["to_this"],
                    constrained,
                    maintainOffset=True,
                )[0]
            )
            cns.interpType.set(2) # -- Shortest

            for idx, weight in enumerate(constraint_data["weights"]):
                cns.weight_attributes()[idx].set(weight)

        # -- Create the mixer
        mixer_data = self.option("Mixer Data").get()

        mixer = aniseed_toolkit.transformation.TransformMixer(parent=org.name())
        self.option("Mixer").set(mixer.node.name())

        for plug_name, control_offset in direct_controls.items():

            control_offset = mref.get(control_offset)
            mixer_deformer = mixer.add_deformer(plug_name)
            mixer_deformer.parent().set_matrix(control_offset.get_matrix(space="world"), space="world")

            mixer_deformer.translate.connect(control_offset.translate)
            mixer_deformer.rotate.connect(control_offset.rotate)
            mixer_deformer.scale.connect(control_offset.scale)

        for pose_name in self.pose_list:
            pose = mixer.add_pose(name=pose_name)

        # -- Now set the matrices
        if mixer_data:
            for pose in mixer_data["poses"]:
                for target_data in pose["targets"]:
                    deformer_name = target_data["name"]
                    pose_name = pose["name"]
                    target = mixer.get_target(pose_name, deformer_name)
                    target.set_matrix(target_data["transform"])

        if self.option("Use Control Rig").get():

            # -- Create the control rig.
            self.create_control_setup(jaw=mref.get(jaw_control))
        else:
            # -- Expose the attributes
            for pose_name in self.pose_list:
                driving_attribute = attribute_host.add_attribute(
                    pose_name,
                    value=0,
                    attribute_type="float",
                    keyable=True,
                )
                driving_attribute.connect(mixer.node.attr(pose_name))


        # -- Set the outputs
        self.output("FaceRig").set(org.name())

    def create_control_setup(self, jaw):

        attribute_dictionary = self.construct_attribute_dictionary()
        addition_nodes = self.initialise_driving_adds(attribute_dictionary)

        self.setup_lip_puller(
            location="left",
            guide=self.input("left_lip_corner_guide").get(),
            jaw=jaw,
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_lip_puller(
            location="right",
            guide=self.input("right_lip_corner_guide").get(),
            jaw=jaw,
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_central_lip(
            section="upper",
            guide=self.input("upper_lip_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )
        self.setup_central_lip(
            section="lower",
            guide=self.input("lower_lip_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_nose(
            guide=self.input("nose_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_inner_brow(
            location="left",
            guide=self.input("left_brow_inner_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_inner_brow(
            location="right",
            guide=self.input("right_brow_inner_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_outer_brow(
            location="left",
            guide=self.input("left_brow_outer_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_outer_brow(
            location="right",
            guide=self.input("right_brow_outer_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

    def get_data_by_label(self, label: str):
        print("looking for %s" % label)
        for data in self.face_bones:
            if data["name"] + "_" + data["location"] == label:
                return data
        return None

    def on_enter_stack(self):

        joint_parent = mref.selected()[0]

        sides = {
            "left": self.config.left,
            "right": self.config.right,
            "middle": self.config.middle,
        }
        created_joints = dict()


        for bone_description in self.face_bones:
            bone_label = f"{bone_description['name']}_{bone_description['location']}"

            bone = mref.get(
                aniseed_toolkit.joints.create(
                    description=bone_description["name"],
                    location=sides[bone_description["location"]],
                    parent=created_joints.get(bone_description["parent"], joint_parent).name(),
                    config=self.config,
                )
            )
            bone.set_matrix(bone_description["matrix"])
            self.input(bone_label).set(bone.name())
            created_joints[bone_label] = bone

        self.input("Parent").hook_to_parent()

    def mixer(self, silent=False):
        mixer_name = self.option("Mixer").get()
        if not mixer_name or not cmds.objExists(mixer_name):
            if not silent:
                qtility.request.message(
                    title="Cannot Snapshot Data",
                    message="You must build the rig before using the snapshot"
                )
            return

        mixer = aniseed_toolkit.transformation.TransformMixer(node=mixer_name)
        return mixer

    def mirror_pose(self):
        mixer = self.mixer()
        if not mixer:
            return

        for pose in mref.selected():
            source_pose_name = pose.pose_name.get()

            side = "left"
            alternate_side = "right"

            if side not in source_pose_name:
                side = "right"
                alternate_side = "left"

            other_pose_name = source_pose_name.replace(side, alternate_side)

            source_targets = []
            destination_targets = []
            source_targets = []
            print(mixer)
            print(mixer.deformers())
            for deformer in mixer.deformers():
                deformer_name = deformer.deformer_name.get()

                if side in deformer_name:
                    source_target = mixer.get_target(source_pose_name, deformer_name)
                    source_targets.append(source_target)

            mref.select(source_targets)

            aniseed_toolkit.mirror.global_mirror(
                transforms=[target.name() for target in source_targets],
                name_replacement=[side, alternate_side],
            )

    def show_pose(self):

        for pose in mref.selected():
            pose_name = pose.pose_name.get()
            mixer = self.mixer()
            if not mixer:
                print("no mixer")
                return

            attribute_name = f"show_{pose_name}_targets"
            mixer.node.attr(attribute_name).set(True)


    def hide_pose(self):
        for pose in mref.selected():
            pose_name = pose.pose_name.get()
            mixer = self.mixer()
            if not mixer:
                print("no mixer")
                return

            attribute_name = f"show_{pose_name}_targets"
            mixer.node.attr(attribute_name).set(False)

    def construct_attribute_dictionary(self):

        mixer = self.mixer(silent=True)
        attribute_dictionary = dict()
        for pose in self.pose_list:

            attribute_dictionary[pose] = mixer.node.attr(pose)

        return attribute_dictionary

    def setup_outer_brow(self, location, guide, parent, connection_map):
        control = self.resolve_control(
            description="brow_outer",
            identity_label=f"{location}_brow_outer",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tx", "tz"],
        )

        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_outer_up"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_outer_down"],
        )

        self.expose_direct(
            control=control,
            label="squint_inner",
            destination_attribute=connection_map[f"{location}_squint_inner"],
        )

        self.expose_direct(
            control=control,
            label="squint_outer",
            destination_attribute=connection_map[f"{location}_squint_outer"],
        )

    def setup_inner_brow(self, location, guide, parent, connection_map):

        control = self.resolve_control(
            description="brow_inner",
            identity_label=f"{location}_brow_inner",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tz"],
        )
        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_inner_up"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_inner_down"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_brow_inner_in"],
            clamp_min=-1,
        )

        self.expose_direct(
            control=control,
            label="mid_brow",
            destination_attribute=connection_map[f"{location}_brow_mid_up"]
        )
        self.expose_reversal_direct(
            control=control,
            label="mid_brow",
            destination_attribute=connection_map[f"{location}_brow_mid_down"]
        )

    def setup_nose(self, guide, parent, connection_map, scale=1):

        control = self.resolve_control(
            description="nose",
            identity_label="nose",
            location=self.config.middle,
            parent=parent,
            guide=guide,
        )

        self.expose_direct(
            control=control,
            label=f"left_nose_flare",
            destination_attribute=connection_map[f"left_nose_flare"]
        )
        self.expose_direct(
            control=control,
            label=f"right_nose_flare",
            destination_attribute=connection_map[f"right_nose_flare"]
        )

    def setup_central_lip(self, section, guide, parent, connection_map):

        control = self.resolve_control(
            description=f"{section}_lip",
            identity_label=f"{section}_lip",
            location=self.config.middle,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tx"],
        )

        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{section}_lip_pull"],
        )

        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{section}_lip_compress"],
        )

        self.clamped_connection(
            driving_attribute=control.attr("translateZ"),
            destination_attribute=connection_map[f"{section}_lip_curl_out"],
        )

        self.clamped_reversal(
            driving_attribute=control.attr("translateZ"),
            destination_attribute=connection_map[f"{section}_lip_curl_in"],
        )
        self.expose_direct(
            control=control,
            label=f"right_sneer",
            destination_attribute=connection_map[f"right_lip_sneer_{section}"],
            clamp_min=-1,
        )
        self.expose_direct(
            control=control,
            label=f"left_sneer",
            destination_attribute=connection_map[f"left_lip_sneer_{section}"],
            clamp_min=-1,
        )

        # -- Set up the sneering fixer
        add_sneers = mref.create("floatMath")
        control.attr("right_sneer").connect(add_sneers.attr("floatA"))
        control.attr("left_sneer").connect(add_sneers.attr("floatB"))

        divide_by_two = mref.create("floatMath")
        divide_by_two.attr("operation").set(2)  # -- Multiply
        divide_by_two.attr("floatB").set(0.5)
        add_sneers.attr("outFloat").connect(divide_by_two.attr("floatA"))

        add_direct = mref.create("floatMath")
        divide_by_two.attr("outFloat").connect(add_direct.attr("floatA"))

        self.expose_direct(
            control=control,
            label="sneer_fixup",
            destination_attribute=add_direct.attr("floatB"),
            clamp_min=-1,
            clamp_max=1,
            do_next=False,
        )
        clamp = mref.create("clamp")
        clamp.attr("minR").set(-1)
        clamp.attr("maxR").set(1)
        add_direct.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(connection_map[f"{section}_sneer"])

    def setup_lip_puller(self, location, guide, jaw, parent, connection_map):

        control = self.resolve_control(
            description=f"lip_puller",
            identity_label=f"{location}_lip_corner",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tz"],
        )
        # -- Multiply the jaw x against the pull in and drive the right_lip_corner_push_in_jaw_open
        multiply_jaw = mref.create("floatMath")
        multiply_jaw.operation.set(2) # - multiply
        multiply_jaw.floatB.set(1.0 / 25)
        jaw.rotateX.connect(multiply_jaw.floatA)

        multiply_inverter = mref.create("floatMath")
        multiply_inverter.operation.set(2)
        multiply_inverter.floatA.set(-1.0)
        control.translateX.connect(multiply_inverter.floatB)

        multiply_mix = mref.create("floatMath")
        multiply_mix.operation.set(2) # - Multiply
        multiply_jaw.outFloat.connect(multiply_mix.floatA)
        multiply_inverter.outFloat.connect(multiply_mix.floatB)


        self.clamped_connection(
            driving_attribute=multiply_mix.outFloat,
            destination_attribute=connection_map[f"{location}_lip_corner_push_in_jaw_open"],
        )

        # -- Pull Out Behaviour
        self.clamped_connection(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_out"],
        )

        # -- Push In Behaviour
        self.clamped_reversal(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_lip_corner_push_in"],
        )

        # -- Pull Down In Behaviour
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_down"],
        )

        # -- Push Up Behaviour
        corner_pull_up_setup = self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_up"],
        )

        # -- Now add the squint
        remap_node = mref.create("remapValue")
        corner_pull_up_setup["clamp"].attr("outputR").connect(
            remap_node.attr("inputValue"))
        remap_node.attr("inputMax").set(1)
        remap_node.attr("value[0].value_Position").set(0.25)
        remap_node.attr("value[0].value_FloatValue").set(0)
        remap_node.attr("value[0].value_Interp").set(2)  # Smooth
        remap_node.attr("value[1].value_Position").set(1)
        remap_node.attr("value[1].value_FloatValue").set(0.25)
        remap_node.attr("outValue").connect_next(
            connection_map[f"{location}_squint_outer"])

        # -- Set up our direct connections
        self.expose_direct(
            control=control,
            label="Blow",
            destination_attribute=connection_map[f"{location}_cheek_blow"],
        )
        self.expose_reversal_direct(
            control=control,
            label="Blow",
            destination_attribute=connection_map[f"{location}_cheek_suck"],
        )

    def initialise_driving_adds(self, attribute_dictionary):

        driving_additions = dict()

        for label, attribute in attribute_dictionary.items():
            node = mref.create("plusMinusAverage")
            node.attr("output1D").connect(attribute)

            driving_additions[label] = node.attr("input1D")
        return driving_additions

    def clamped_connection(self, driving_attribute, destination_attribute, clamp_min=0,
                           clamp_max=1):

        clamp = mref.create("clamp")
        clamp.attr(f"maxR").set(clamp_max)
        clamp.attr(f"minR").set(clamp_min)
        driving_attribute.connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

        return {
            "clamp": clamp,
        }

    def clamped_reversal(self, driving_attribute, destination_attribute, clamp_min=0,
                         clamp_max=1):

        # -- Push In Behaviour
        clamp = mref.create("clamp")
        inverse = mref.create("floatMath")
        inverse.attr("operation").set(2)  # -- Multiply
        inverse.attr("floatB").set(-1)
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)
        driving_attribute.connect(inverse.attr("floatA"))
        inverse.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

        return {
            "clamp": clamp,
            "multiplier": inverse,
        }

    def expose_reversal_direct(self, control: mref.ReferencedItem, label,
                               destination_attribute, clamp_min=0, clamp_max=1):

        if control.has_attribute(label):
            attribute = control.attr(label)
        else:
            attribute = control.add_attribute(
                label,
                value=0,
                attribute_type="float",
                keyable=True,
            )
        clamp = mref.create("clamp")
        inverse = mref.create("floatMath")

        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)

        inverse.attr("operation").set(2)  # -- Multiply
        inverse.attr("floatB").set(-1)

        attribute.connect(inverse.attr("floatA"))
        inverse.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

    def expose_direct(self, control: mref.ReferencedItem, label, destination_attribute,
                      clamp_min=0, clamp_max=1, do_next=True):

        if control.has_attribute(label):
            attribute = control.attr(label)
        else:
            attribute = control.add_attribute(
                label,
                value=0,
                attribute_type="float",
                keyable=True,
            )
        clamp = mref.create("clamp")
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)
        attribute.connect(clamp.attr("inputR"))

        if do_next:
            clamp.attr("outputR").connect_next(destination_attribute)
        else:
            clamp.attr("outputR").connect(destination_attribute)

        return {
            "clamp": clamp,
        }

    def resolve_control(self, description, identity_label, location, parent, guide,
                        lock_and_hide=None):
        control_name = self.input(f"{identity_label}_control").get()
        if control_name:
            return mref.get(
                control_name)  # , aniseed_toolkit.control.Control(control_name)

        new_control_setup = aniseed_toolkit.control.create(
            description="Facial" + description,
            location=location,
            parent=self.input(f"{identity_label}_parent").get() or parent,
            shape=self.input(f"{identity_label}_shape").get() or "core_cube",
            config=self.config,
            match_to=guide or None,
        )

        if lock_and_hide:
            aniseed_toolkit.attributes.lock_and_hide([new_control_setup.ctl],
                                                     lock_and_hide, lock=True,
                                                     hide=True)

        # -- Start by creating the control
        return mref.get(new_control_setup.ctl)  # , new_control_setup

    def snap_pose(self):

        mixer = self.mixer()
        if not mixer:
            return

        for pose in mref.selected():
            source_pose_name = pose.pose_name.get()

            for deformer in mixer.deformers():
                target = mixer.get_target(source_pose_name, deformer.deformer_name.get())
                target.set_matrix(deformer.get_matrix(space="world"), space="world")