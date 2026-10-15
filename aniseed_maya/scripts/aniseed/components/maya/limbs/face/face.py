"""
Provides the "Limb : Face" component, which generates a face skeleton from
skeleton.json and builds a bone driven face rig. It reuses the mouth and eyes
components, creates direct controls for every face bone, drives them through
a transform mixer of poses (which behave like blendshapes) and adds a high
level animator control rig. It also defines the FacialTools widget and
MixerTools helpers used to edit, mirror, save and load the pose data.
"""
import os
import json
import mref
import copy
import qtility
import functools
import aniseed
import aniseed_toolkit
from Qt import QtWidgets


class FaceComponent(aniseed.RigComponent):
    """
    This will automatically create eye and mouth components as well
    as a series of singulars to represent face bones. It will then
    create a transform mixer and a construct a facial control rig
    to drive it all.
    """

    identifier = "Limb : Face"

    # -- When adding the face we construct a skeleton. All the data relating to
    # -- the skeleton and the hierarchy are stored in this json file.
    with open(os.path.join(os.path.dirname(__file__), "skeleton.json"), "r") as f:
        face_bones = json.load(f)

    # -- This is the pose data we will use by default if none are specified
    with open(os.path.join(os.path.dirname(__file__), "default_pose_data.json"), "r") as f:
        default_pose_data = json.load(f)

    # -- This is the equivalent of blendshapes. These are all the "facial shapes" we will
    # -- blend in or expose
    pose_list = [

        # -- Broad Mouth Movement
        "left_lip_corner_push_in",
        "left_lip_corner_push_in_jaw_open",
        "left_lip_corner_pull_out",
        "left_lip_corner_pull_up",
        "left_lip_corner_pull_down",
        "right_lip_corner_push_in",
        "right_lip_corner_push_in_jaw_open",
        "right_lip_corner_pull_out",
        "right_lip_corner_pull_up",
        "right_lip_corner_pull_down",
        "upper_lip_pull",
        "lower_lip_pull",
        "upper_lip_compress",
        "lower_lip_compress",
        "upper_lip_curl_out",
        "lower_lip_curl_out",
        "upper_lip_curl_in",
        "lower_lip_curl_in",

        # -- Sneering
        "left_lip_sneer_lower",
        "left_lip_sneer_upper",
        "right_lip_sneer_lower",
        "right_lip_sneer_upper",
        "upper_sneer",
        "lower_sneer",

        # -- Cheeks
        "left_cheek_suck",
        "left_cheek_blow",
        "right_cheek_suck",
        "right_cheek_blow",

        # -- Nose
        "left_nose_flare",
        "right_nose_flare",

        # -- Squinting
        "left_squint_inner",
        "left_squint_outer",
        "right_squint_inner",
        "right_squint_outer",

        # -- Brow Movement
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

        # -- Supporting Correctives
        "jaw_open",

        # -- Eyes
        "left_blink",
        "right_blink",
    ]

    # -- All our bones have "direct" controls which an animator can
    # -- pull around on an individual basis. However, these "control groups"
    # -- are higher level controls which drive the various pose shapes
    # -- listed above.
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
        """
        Declares the parent and attribute host inputs, one joint input per
        bone in skeleton.json, and control/parent/guide/shape inputs for each
        high level control group. Options store the mixer data and mixer name
        and pass settings through to the mouth and eyes sub components. The
        single output is the FaceRig org.
        """
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

        # -- We need to expose an input for each of the face bones defined
        # -- in the face_data.json. As we have that list in data we use that
        # -- to build the inputs rather than write a hard coded input list
        for bone_description in self.face_bones:
            self.declare_input(
                name=f"{bone_description['name']}_{bone_description['location']}",
                value="",
                group="Joints",
            )

        # -- The mixer (aniseed_toolkit.rig.pose_mixer.TransformMixer) is a special
        # -- structure and node setup which allows for poses to be defined through collections
        # -- of transforms. The deformers are then blended additively to these transforms. This
        # -- allows for a face rig which feels like a morph target rig but is bone driven.
        # -- This option specifically stores all the pose data. This is a bit like storing all
        # -- the morph targets in a blendshape setup.
        self.declare_option(
            name="Mixer Data",
            value=[],
            hidden=False,
        )

        # -- If set, the mixer targets are deleted once their pose data has
        # -- been applied
        self.declare_option(
            name="Optimise",
            value="",
            hidden=False,
        )

        # -- Store the name of the mixer so that our tools can easily interact
        # -- with it
        self.declare_option(
            name="Mixer",
            value="",
            hidden=False,
        )

        # -- The control groups represent each high level control for the
        # -- face rig. We allow the user to define pre-made controls or
        # -- guide locations if they want the rig to build the control. We
        # -- also allow them to specify the parent of the control.
        control_group_parts = ["control", "parent", "guide", "shape"]
        for control_label in self.control_groups:
            group = "Control : %s" % control_label.replace("_", " ").title()

            for part in control_group_parts:
                self.declare_input(
                    name=f"{control_label}_{part}",
                    value="",
                    group=group,
                    validate=False,
                )

        # -- We build the main mouth and eye setups through other components, so
        # -- we expose various options which those expose.
        self.declare_option(
            name="Mouth Target Distance Multiplier",
            value=1.0,
        )
        self.declare_option(
            name="Eye Target Distance",
            value=30.0,
        )

        self.declare_option(
            name="Max Blink Rotation",
            value=65,
        )

        # -- Now we declare our outputs
        self.declare_output("FaceRig")

        # -- Build properties
        self.eyes_component = None

    def on_enter_stack(self):
        """
        When this component is added we will generate the face bones
        """
        # -- Get the selection, if there is no selection then we just build
        # -- at world space
        selected = mref.selected()
        joint_parent = selected[0] if selected else None

        # -- Within the labelling of the face we use the terms left, right and middle
        # -- but we need to ensure we're always building with the config designated names
        # -- so lets create a mapping
        sides = {
            "left": self.config.left,
            "right": self.config.right,
            "middle": self.config.middle,
        }

        # -- The face bone list is not flat, therefore as we create joints
        # -- we need to add them to this dictionary so we can use it to look
        # -- up the expected parent joints
        created_joints = dict()

        for bone_description in self.face_bones:

            # -- Create label - this mimic's the input plug so we can auto
            # -- populate it, and it also allows us to look up the parenting
            bone_label = f"{bone_description['name']}_{bone_description['location']}"

            # -- Create the joint and set its matrix based on the data
            # -- in the face_bones.json file
            bone_parent = created_joints.get(bone_description["parent"], joint_parent)
            bone = mref.get(
                aniseed_toolkit.scene.joints.create(
                    description=bone_description["name"],
                    location=sides[bone_description["location"]],
                    parent=bone_parent.name() if bone_parent is not None else None,
                    config=self.config,
                )
            )
            bone.set_matrix(bone_description["matrix"])

            # -- Set the bone as an input
            self.input(bone_label).set(bone.name())

            # -- Store this as a created joint to allow us to look it up for
            # -- parenting if required.
            created_joints[bone_label] = bone

        self.input("Parent").hook_to_parent()

    def input_widget(self, requirement_name: str):
        """
        This is where we return any bespoke widgets for the inputs
        """
        if requirement_name in ["Parent", "Attribute Host"]:
            return aniseed.widgets.ObjectSelector()

        if requirement_name.endswith("_shape"):
            return aniseed.widgets.ShapeSelector(default_item="core_cube")

        attribute = self.input(requirement_name)
        if attribute.group() and attribute.group().startswith("Control :"):
            return aniseed.widgets.ObjectSelector()

        if self.get_data_by_label(requirement_name):
            return aniseed.widgets.ObjectSelector()

        return None

    def option_widget(self, option_name: str):
        """
        This is where we return any bespoke widgets for the options
        """
        if option_name == "Mixer Data":
            return FacialTools(component=self)
        return None

    def run(self):
        """
        This is the main function where we build the rig.
        """
        # -- Get the parent node which everything should be built under
        parent = self.input("Parent").get()

        # -- Create the org
        org = mref.get(
            aniseed_toolkit.scene.transforms.create(
                classification=self.config.organisational,
                description="face",
                location=self.config.middle,
                config=self.config,
                parent=parent,
            )
        )

        # -- The attribute host is where we store all of the user facing attributes.
        # -- If none is given we fall back to the org.
        attribute_host = mref.get(self.input("Attribute Host").get() or org)
        visibility_attribute = attribute_host.add_attribute(
            name="direct_control_visibility",
            value=0,
            attribute_type="bool",
            keyable=False,
        )
        visibility_attribute.set(channelBox=True)

        # -- Create the mouth using the mouth component rather than duplicate
        # -- the code.
        mouth_component = self.stack.component_library.request("Limb : Mouth")(label="", stack=self.stack)
        mouth_component.input("Parent").set(org.name())
        mouth_component.input("Jaw Joint").set(self.input("jaw_middle").get())
        mouth_component.input("Upper Lip Joint").set(self.input("upper_lip_middle").get())
        mouth_component.input("Lower Lip Joint").set(self.input("lower_lip_middle").get())
        mouth_component.option("Aim Control Distance Multiplier").set(self.option("Mouth Target Distance Multiplier").get())
        mouth_component.run()

        # -- Create the eyes - again using the eyes component so we do not duplicate
        # -- the code
        eyes_component = self.stack.component_library.request("Limb : Eyes")(label="", stack=self.stack)
        eyes_component.input("Parent").set(org.name())
        eyes_component.input("Left Eye Joint").set(self.input("eye_left").get())
        eyes_component.input("Left Upper Eye Lid Joint").set(self.input("eye_upper_lid_left").get())
        eyes_component.input("Left Lower Eye Lid Joint").set(self.input("eye_lower_lid_left").get())
        eyes_component.input("Left Pupil Joint").set(self.input("eye_pupil_left").get())
        eyes_component.input("Right Eye Joint").set(self.input("eye_right").get())
        eyes_component.input("Right Upper Eye Lid Joint").set(self.input("eye_upper_lid_right").get())
        eyes_component.input("Right Lower Eye Lid Joint").set(self.input("eye_lower_lid_right").get())
        eyes_component.input("Right Pupil Joint").set(self.input("eye_pupil_right").get())
        eyes_component.option("Aim Distance").set(self.option("Eye Target Distance").get())
        eyes_component.option("Max Blink Rotation").set(self.option("Max Blink Rotation").get())
        eyes_component.option("Add Blink").set(False)
        eyes_component.option("Add Pupil").set(True)
        eyes_component.run()
        self.eyes_component = eyes_component

        # -- Some of the controls come from the components we have just built, so we populate
        # -- our "created control" dictionary with the controls from those components to start
        # -- us off.
        created_controls = dict(
            jaw_middle=mouth_component.output("Jaw Control").get(),
            eye_left=eyes_component.output("Left Eye Control").get(),
            eye_right=eyes_component.output("Right Eye Control").get(),
            eye_upper_lid_left=eyes_component.output("Left Upper Eye Lid Control").get(),
            eye_upper_lid_right=eyes_component.output("Right Upper Eye Lid Control").get(),
            eye_lower_lid_left=eyes_component.output("Left Lower Eye Lid Control").get(),
            eye_lower_lid_right=eyes_component.output("Right Lower Eye Lid Control").get(),
            eye_pupil_left=eyes_component.output("Left Pupil Control").get(),
            eye_pupil_right=eyes_component.output("Right Pupil Control").get(),
            head=org.name(),
        )

        # -- This is the dictionary of controls we explicitly consider to be
        # -- direct driving controls
        direct_controls = dict()

        # -- Create a control for each joint (unless that joint has
        # -- already had a control created for it
        for input_plug in self.inputs():

            # -- If the plug has been marked as having already had
            # -- a control created for it through another process then
            # -- we do not create another one.
            if input_plug.name() in created_controls:
                continue

            # -- From the name of the plug, this will retrieve the dictionary
            # -- of data about the bone from the face_data.json file.
            data = self.get_data_by_label(input_plug.name())

            # -- If or any reason there is no data in the json file for this
            # -- input we ignore it.
            if not data:
                continue

            # -- If the bone is managed by another component, skip it
            if data["component"]:
                continue

            # -- Get the joint we need to drive
            joint = mref.get(input_plug.get())

            # -- As a safety measure lets just make sure its not being
            # -- driven by anything else
            for constraint in joint.constraints():
                constraint.delete()

            # -- Create a control to drive the joint
            control = aniseed_toolkit.rig.control.create(
                description="direct_" + data["name"],
                location=data["location"],
                parent=created_controls.get(
                    data["parent"],
                    direct_controls.get(data["parent"], org.name()),
                ),
                shape="core_cube",
                config=self.config,
                match_to=joint.name(),
            )

            # -- Hook up the constraints between the control
            # -- and the joint
            aniseed_toolkit.scene.constraints.parent_and_scale(
                control.ctl,
                joint,
                maintain_offset=True,
            )

            # -- If a joint is declared as being "always on" then we will
            # -- not hook up its visibility overrides.
            if not data.get("is_always_on", False):
                self.drive_shape_visibility(control.ctl, visibility_attribute)

            # -- Store the control
            direct_controls[input_plug.name()] = control.ctl

        mref.get(eyes_component.output("org").get()).set_parent(
            direct_controls["upper_head_middle"],
        )

        # -- Create the bespoke inserted controls
        for label, created_control in created_controls.items():

            data = self.get_data_by_label(label)
            if not data:
                continue

            # -- Create a control which we will insert into the hierarchy
            # -- above the control created by the sub component
            created_control = aniseed_toolkit.rig.control.get(created_control)
            created_control_org = mref.get(created_control.org)

            control = aniseed_toolkit.rig.control.create(
                description="direct_" + data["name"],
                location=data["location"],
                parent=created_control_org.parent().name(),
                shape="core_cube",
                config=self.config,
                match_to=created_control.ctl,
            )
            created_control_org.set_parent(control.ctl)

            # -- If a joint is declared as being "always on" then we will
            # -- not hook up its visibility overrides.
            if not data.get("is_always_on", False):
                self.drive_shape_visibility(control.ctl, visibility_attribute)

            direct_controls[label] = control.ctl

        # -- Place the lip controls under the mouth component's lip controls
        for section in ["upper", "lower"]:
            lip_control = mouth_component.output(f"{section.title()} Lip Control").get()
            for control_label, control in direct_controls.items():
                if f"{section}_lip_" in control_label:
                    mref.get(aniseed_toolkit.rig.control.get(control).org).set_parent(lip_control)

        # ----------------------------------------------------
        # -- Get the jaw as an mref object
        m_jaw = mref.get(mouth_component.output("Jaw Control").get())
        self.setup_jaw_behaviour(
            mouth_component.output("Upper Lip Control").get(),
            mouth_component.output("Lower Lip Control").get(),
            direct_controls,
            m_jaw,
            org,
            attribute_host,
        )

        # ----------------------------------------------------
        # -- The mixer is the functional heart of the whole setup. It is this mixer
        # -- which allows the transforms to behave like blendshapes. Therefore we
        # -- start by getting the stored transformation shape data
        mixer_data = self.option("Mixer Data").get()

        if not mixer_data:
            mixer_data = copy.deepcopy(self.default_pose_data)

        # -- Instance the mixer, but store a reference to the mixer in the component. This
        # -- allows any tools to inspect the component and know which mixer to interact
        # -- with.
        mixer = aniseed_toolkit.rig.pose_mixer.TransformMixer(parent=org.name())
        self.option("Mixer").set(mixer.node.name())

        # -- Cycle over all our direct controls and add them as deformers into our
        # -- mixer
        for plug_name, control in direct_controls.items():

            # -- Get the control, and then access the offset node
            control_instance = aniseed_toolkit.rig.control.get(control)
            controller = mref.get(control_instance.ctl)
            control_offset = mref.get(control_instance.off)

            # -- Add a new deformer (node controlled by the mixer) and ensure its parent
            # -- is transformed to the location of the control offset
            mixer_deformer = mixer.add_deformer(plug_name)
            mixer_deformer.parent().match_to(control_offset)

            # -- Add a link to the controller
            control_link = mixer_deformer.add_attribute(
                "control_link",
                attribute_type="message",
                value=None,
            )
            controller.attr("message").connect(control_link)

            # -- Finally we drive the control offsets local values through the mixers
            # -- deformer node.
            for channel in ["translate", "rotate", "scale"]:
                mixer_deformer.attr(channel).connect(control_offset.attr(channel))

        # -- Now we need to add each pose as defined in this components
        # -- pose list.
        for pose_name in self.pose_list:
            mixer.add_pose(name=pose_name)

        # -- Finally, using the stored data, we set the matrices of each
        # -- target. This is a little time consuming sadly, as its a LOT
        # -- of data! When optimising, each target is deleted once its
        # -- matrix has been applied.
        optimise = self.option("Optimise").get()

        if mixer_data:
            for pose in mixer_data["poses"]:
                for target_data in pose["targets"]:
                    target = mixer.get_target(pose["name"], target_data["name"])

                    if target:
                        target.set_matrix(target_data["transform"])

                        if optimise:
                            target.delete()

        # -- Create the high level control rig which drives everything.
        high_level_control_rig = HighLevelControlRig(
            component=self,
            attribute_host=attribute_host,
        )
        high_level_control_rig.create(m_jaw)

        # -- Finally, we expose some attributes to show/hide the tongue and teeth. This will be
        # -- driven by an attribute on the jaw
        attribute = m_jaw.add_attribute(
            "show_teeth_and_tongue",
            attribute_type="bool",
            value=False,
            keyable=False,
        )
        attribute.set(channelBox=True)

        # -- These controls already have their visibility driven by the direct
        # -- control visibility, so we force the connection to take over.
        for label, control in direct_controls.items():
            if "teeth" in label or "tongue" in label:
                self.drive_shape_visibility(control, attribute, force=True)

        # -- Push the eye keyables into the attribute host
        for side in ["left", "right"]:
            eye_control = mref.get(eyes_component.output(f"{side.title()} Eye Control").get())

            attribute_host.add_separator_attribute()
            for attr in eye_control.attributes(userDefined=True):

                # -- Skip separator attributes
                if not attr.name(include_node=False).replace("_", ""):
                    continue

                try:
                    attribute_host.add_proxy(f"{side}_" + attr.name(include_node=False), attr)
                except Exception:
                    pass

        # -- Set the outputs
        self.output("FaceRig").set(org.name())

    @staticmethod
    def drive_shape_visibility(control, attribute, force=False):
        """
        Connects the given attribute to the visibility of every shape
        of the given control.
        """
        for shape in mref.get(control).shapes():
            attribute.connect(shape.attr("visibility"), force=force)

    def setup_jaw_behaviour(
            self,
            upper_lip_control,
            lower_lip_control,
            direct_controls,
            jaw_control,
            org,
            attribute_host,
    ):
        """
        The jaw behaviour is a bespoke constraint setup which ensures the lips
        work together when the jaw opens. We cannot simply use a pose for this, as the
        jaw can shear.
        Instead we constrain the outer lips and mid lips progressively, but allow the
        animator to dial it in and out.

        :param upper_lip_control: The upper lip control of the mouth component
        :param lower_lip_control: The lower lip control of the mouth component
        :param direct_controls: A dictionary of all the created direct controls
        :param jaw_control: The jaw control
        :param org: This will be the parent of all the created nodes
        :param attribute_host: The node to expose the smoothing attributes on
        """
        # -- Add our smooth attributes - the animator can use these
        # -- to dial this behaviour in and out
        attribute_host.add_separator_attribute()
        for side in ["left", "right"]:
            smooth_attribute = jaw_control.add_attribute(
                f"smooth_lips_{side}",
                attribute_type="float",
                keyable=True,
                value=1,
            )
            attribute_host.add_proxy(
                smooth_attribute.name(include_node=False),
                source_attribute=smooth_attribute,
            )

        # -- Now build up the data structure. This determines what is constrained
        # -- to what and with what weights. Each row is applied to the left and
        # -- then the right control (in that order, as it decides node names):
        # -- (control label, constrain to, parent space, weights)
        mouth_constraint_data = [
            ("upper_lip_outer", jaw_control, upper_lip_control, [0.6, 0.4]),
            ("lower_lip_outer", lower_lip_control, org, [0.4, 0.6]),
            ("upper_lip_mid", jaw_control, upper_lip_control, [0.8, 0.2]),
            ("lower_lip_mid", lower_lip_control, org, [0.2, 0.8]),
            ("upper_lip_inner", jaw_control, upper_lip_control, [1, 0]),
            ("lower_lip_inner", lower_lip_control, org, [0, 1]),
            ("dimple", jaw_control, org, [0.5, 0.5]),
        ]

        # -- This setup will create a variety of proxy/buffer nodes. To keep the
        # -- rig clean we place them all under an organisational node, which we
        # -- create now.
        proxy_org = mref.create(
            "transform",
            name=self.config.generate_name(
                classification=self.config.organisational,
                description="mouth_smoothing_proxy",
                location=self.config.middle,
            ),
            parent=org,
        )
        proxy_org.match_to(org)

        for label, to_this, parent_space, weights in mouth_constraint_data:
            for location in ["left", "right"]:

                # -- From the control get the control instance class and
                # -- access the offset, zero and org
                control_name = direct_controls[f"{label}_{location}"]
                control_instance = aniseed_toolkit.rig.control.get(control_name)

                # -- Create the proxy node. This is the node that has the constraints
                # -- on which represents the behaviour.
                proxy = mref.create(
                    "transform",
                    name=self.config.generate_name(
                        classification=self.config.mechanical,
                        description=control_name + "_smooth_proxy",
                        location=self.config.middle,
                    ),
                    parent=proxy_org,
                )
                proxy.match_to(mref.get(control_instance.off))

                # -- Set up the two constraints on the proxy
                mref.parentConstraint(
                    parent_space,
                    proxy,
                    maintainOffset=True,
                )
                cns = mref.parentConstraint(
                    to_this,
                    proxy,
                    maintainOffset=True,
                )[0]

                # -- Ensure the constraint is set to shortest as it
                # -- gives the best and most predictable result
                cns.interpType.set(2)  # -- Shortest

                # -- Set the weights of that data based on the data
                for idx, weight in enumerate(weights):
                    cns.weight_attributes()[idx].set(weight)

                # -- We now constrain the control's zero to the proxy
                mref.parentConstraint(control_instance.org, control_instance.zero, maintainOffset=True)
                cns = mref.parentConstraint(proxy, control_instance.zero, maintainOffset=True)[0]
                cns.interpType.set(2)  # -- Shortest

                # -- Finally we drive the weight of that constraint based on the
                # -- attributes we expose to the user.
                aniseed_toolkit.scene.constraints.blend_weights(
                    jaw_control.attr(f"smooth_lips_{location}"),
                    cns,
                )

    def get_data_by_label(self, label: str):
        """
        The data inside the face_bones.json uses a key of name_location, and the
        label is considered to be those two elements jointed together. This
        function is a convenience function for returning the dictionary of data
        for that given label.

        :param label: The label of the face_bones.json file.
        """
        for data in self.face_bones:
            if data["name"] + "_" + data["location"] == label:
                return data
        return None

    def mixer(self, silent=False):
        """
        This will attempt to return the mixer for the component. The mixer is a
        class which points to a node in the scene and exposes an API to interact
        with the deformers and poses.
        """
        mixer_name = self.option("Mixer").get()

        # -- If the mixer does not exist then we cannot do anything. Providing
        # -- we're not asked to return it silently we should inform the user that
        # -- the mixer is not there.
        if not mixer_name or not mref.objExists(mixer_name):
            if not silent:
                qtility.request.message(
                    title="Cannot Snapshot Data",
                    message="You must build the rig before using the snapshot"
                )
            return None

        # -- Instance the mixer object and return it
        return aniseed_toolkit.rig.pose_mixer.TransformMixer(node=mixer_name)


class HighLevelControlRig(aniseed_toolkit.rigging.facial.FacialControlRig):
    """
    The high level control rig is a set of controls which ultimately drives
    the transformation mixer. This makes for a much nicer animator-friendly
    interface.

    The control settings are read from the component's inputs, every animator
    facing attribute is proxied onto the attribute host and the sneer fixup
    multiplies (rather than averages) the sneers.
    """

    def __init__(self, component, attribute_host):
        """
        Args:
            component: The face component whose inputs provide the control
                settings
            attribute_host: The node to proxy the animator facing attributes onto
        """
        super(HighLevelControlRig, self).__init__(
            config=component.config,
            read_setting=lambda name: component.input(name).get(),
            attribute_host=attribute_host,
            description_prefix="Facial",
            multiply_sneers=True,
        )
        self.component = component

    def create(self, jaw):
        """
        Builds all the high level controls

        :param jaw: The jaw control, used to blend the lip corner push in
        """
        # -- This will give us a dictionary where the key is the name
        # -- of the pose and the values are the attributes driving that
        # -- pose.
        attribute_dictionary = self.construct_attribute_dictionary()

        # -- To allow a pose to be driven by multiple inputs we pre-append
        # -- a plus node in front of each one. This means we can reliably
        # -- know that attribute we need to connect to is an array attribute.
        addition_nodes = self.initialise_driving_adds(attribute_dictionary)

        parent = self.component.input("Parent").get()

        # -- Note: the order of these calls decides the array indices on the
        # -- plusMinusAverage nodes, so it must be preserved.

        # -- Outer Lip Pullers
        self.attribute_host.add_separator_attribute()

        for side in ["left", "right"]:
            self.setup_lip_puller(
                location=side,
                guide=self.component.input(f"{side}_lip_corner_guide").get(),
                parent=parent,
                connection_map=addition_nodes,
                jaw=jaw,
            )

        # -- Top and Bottom Central Lips
        self.attribute_host.add_separator_attribute()

        for location in ["upper", "lower"]:
            self.setup_central_lip(
                section=location,
                guide=self.component.input(f"{location}_lip_guide").get(),
                parent=parent,
                connection_map=addition_nodes,
            )

        # -- Nose
        self.attribute_host.add_separator_attribute()

        self.setup_nose(
            guide=self.component.input("nose_guide").get(),
            parent=parent,
            connection_map=addition_nodes,
        )

        # -- Inner & Outer Brows and the eyes
        for side in ["left", "right"]:
            self.attribute_host.add_separator_attribute()

            self.setup_inner_brow(
                location=side,
                guide=self.component.input(f"{side}_brow_inner_guide").get(),
                parent=parent,
                connection_map=addition_nodes,
            )
            self.setup_outer_brow(
                location=side,
                guide=self.component.input(f"{side}_brow_outer_guide").get(),
                parent=parent,
                connection_map=addition_nodes,
            )
            self.setup_eye(
                location=side,
                control=mref.get(self.component.eyes_component.output(f"{side.title()} Eye Control").get()),
                connection_map=addition_nodes,
            )

    def construct_attribute_dictionary(self):
        """
        This will cycle the pose list and create a dictionary where the key
        is the name of the pose and value is the attribute that we intend to
        drive that pose with.
        """
        mixer = self.component.mixer(silent=True)
        return {
            pose: mixer.node.attr(pose)
            for pose in self.component.pose_list
        }


class FacialTools(QtWidgets.QWidget):
    """
    This is a QWidget which exposes various tools useful for interacting
    with the face.
    """
    # -- We essentially just show a big list of buttons currently (not pretty!). Ideally
    # -- it would get its own dedicated ui. But for now, whilst its a list we just declare
    # -- a dictionary of button labels, and function names which should be invoked when
    # -- that button is clicked.
    button_mapping = {
        "Snapshot Data": "snapshot_data",
        "Mirror Pose": "mirror_pose",
        "Show Pose": "show_pose",
        "Hide Pose": "hide_pose",
        "Save Data": "save_data",
        "Load Data": "load_data",
        "Clear Data": "clear_data",
        "Snap Pose": "snap_pose",
        "Reset Pose": "reset_pose",
        "Select Pose": "select_pose",
        "Select Active Poses": "select_active_poses",
        "Select Mixer": "select_mixer",
    }

    def __init__(self, component, parent=None):
        """
        Builds a vertical list of buttons, one per entry in button_mapping,
        each calling the matching MixerTools method.

        Args:
            component: The face component the tools operate on
            parent: Optional parent widget
        """
        super(FacialTools, self).__init__(parent=parent)

        # -- Store a reference to the component
        self.component = component

        # -- Instance the tools
        self.mixer_tools = MixerTools(component)

        # -- Build the base layout
        self.setLayout(QtWidgets.QVBoxLayout())

        # -- Cycle the button dictionary
        for button_label, function_name in FacialTools.button_mapping.items():

            # -- Create the button and connect the click event to the tool class
            button = QtWidgets.QPushButton(button_label)
            self.layout().addWidget(button)
            button.clicked.connect(
                functools.partial(
                    getattr(self.mixer_tools, function_name),
                )
            )


class MixerTools:
    """
    This class is a collection of functionality that makes it easier to interact
    with the mixer in the context of the face.
    """

    def __init__(self, component):
        """
        Args:
            component: The face component whose mixer the tools operate on
        """
        self.component = component

    def mirror_pose(self):
        """
        This needs some work! But essentially it will look for the side in the given
        pose
        """
        mixer = self.component.mixer()
        if not mixer:
            return

        # -- Construct our direction mapping
        left_to_right = ["left", "right"]
        right_to_left = ["right", "left"]

        skip_list = [
            "eye_lower_lid_left",
            "eye_lower_lid_right",
            "eye_upper_lid_left",
            "eye_upper_lid_right",
            "eye_pupil_left",
            "eye_pupil_right",
            "eye_left",
            "eye_right",
        ]
        for pose in mref.selected():

            # -- Get the name of the pose
            source_pose_name = pose.pose_name.get()

            # -- Determine the mapping direction
            if "left" in source_pose_name:
                direction_mapping = left_to_right
            else:
                direction_mapping = right_to_left

            # -- Get our active side, and declare the list where we will populate
            # -- the source targets to drive the mirror
            active_side = direction_mapping[0]
            source_targets = []

            # -- Cycle the deformers and get the targets for this pose and deformer.
            for deformer in mixer.deformers():
                deformer_name = deformer.deformer_name.get()

                if deformer_name in skip_list:
                    continue

                if active_side in deformer_name:
                    source_target = mixer.get_target(source_pose_name, deformer_name)
                    source_targets.append(source_target)

            # -- Select the nodes and instigate the mirror
            mref.select(source_targets)
            aniseed_toolkit.scene.mirror.mirror_transforms(
                transforms=[target.name() for target in source_targets],
                name_replacement=[direction_mapping[0], direction_mapping[1]],
                behaviour=True,
                rotate_flip=True,
            )

    def set_pose_visibility(self, value):
        """
        This will se the visibility of the given pose
        """
        # -- If we cannot resolve a mixer then we do nothing
        mixer = self.component.mixer()
        if not mixer:
            return

        # -- Cycle each selected pose
        for pose in mref.selected():

            # -- Get the visibility attribute for this pose and show it.
            pose_name = pose.pose_name.get()
            attribute_name = f"show_{pose_name}_targets"
            mixer.node.attr(attribute_name).set(value)

    def show_pose(self):
        """
        This will show the targets for the given pose.
        """
        self.set_pose_visibility(True)

    def hide_pose(self):
        """
        This will hide the targets for the given pose.
        """
        self.set_pose_visibility(False)

    @staticmethod
    def pose_targets(mixer, pose_name):
        """
        Returns a list of (deformer, target) pairs for the given pose
        """
        return [
            (deformer, mixer.get_target(pose_name, deformer.deformer_name.get()))
            for deformer in mixer.deformers()
        ]

    @staticmethod
    def zero_transform(node):
        """
        Resets the translation, rotation and scale of the given node, skipping
        any channels which cannot be set (such as locked channels).
        """
        for axis in ["X", "Y", "Z"]:
            for channel, value in [("translate", 0), ("rotate", 0), ("scale", 1)]:
                try:
                    node.attr(f"{channel}{axis}").set(value)
                except Exception:
                    pass

    def snap_pose(self):
        """
        This will snap the targets of the selected poses to the current
        (world space) transforms of their controls, and then zero the controls.
        """
        mixer = self.component.mixer()
        if not mixer:
            return

        for pose in mref.selected():
            pose_targets = self.pose_targets(mixer, pose.pose_name.get())

            # -- Store the world matrix of each deformer's control and
            # -- then zero that control
            matrices = dict()
            for deformer, target in pose_targets:
                controller = deformer.control_link.inputs()[0].node()

                matrices[target] = controller.get_matrix(space="world")
                self.zero_transform(controller)

            # -- Setting one target can move others which sit below it, so the
            # -- matrices are applied once per deformer to let them settle.
            for _ in range(len(pose_targets)):
                for target, matrix in matrices.items():
                    target.set_matrix(matrix, space="world")

    def select_pose(self):
        """
        Selects all the targets of the selected poses
        """
        mixer = self.component.mixer()
        if not mixer:
            return

        targets = []

        for pose in mref.selected():
            targets.extend(
                target
                for _, target in self.pose_targets(mixer, pose.pose_name.get())
            )

        mref.select(targets)

    def snapshot_data(self, silent=False):
        """
        Stores the current state of the mixer into the Mixer Data option
        """
        mixer = self.component.mixer(silent=silent)
        if not mixer:
            return

        self.component.option("Mixer Data").set(mixer.serialise())

        if not silent:
            qtility.request.message(
                title="Snapshot Complete",
                message="The snapshot has been made",
            )

    def save_data(self, filepath=None):
        """
        Saves the current state of the mixer to a json file
        """
        mixer = self.component.mixer()
        if not mixer:
            return

        if not filepath:
            filepath = qtility.request.filepath(
                title="Save Data",
                save=True,
            )
            if not filepath:
                return

        with open(filepath, "w") as f:
            json.dump(mixer.serialise(), f, indent=4)

        qtility.request.message(
            title="Save Complete",
            message="The data has been saved",
        )

    def load_data(self, filepath=None):
        """
        Loads mixer data from a json file into the Mixer Data option
        """
        if not filepath:
            filepath = qtility.request.filepath(
                title="Load Data",
                save=False,
            )
            if not filepath:
                return

        with open(filepath, "r") as f:
            self.component.option("Mixer Data").set(json.load(f))

        qtility.request.message(
            title="Load Complete",
            message="The data has been loaded, please rebuild the rig",
        )

    def clear_data(self):
        """
        Clears the stored mixer data
        """
        confirmation = qtility.request.confirmation(
            title="Clear Data",
            message="Are you sure you want to clear the data?",
        )
        if not confirmation:
            return

        self.component.option("Mixer Data").set([])

    def select_mixer(self):
        """
        Selects the mixer node
        """
        mixer = self.component.mixer()
        if mixer:
            mref.select(mixer.node)

    def select_active_poses(self):
        """
        Selects all the poses which are currently active
        """
        mixer = self.component.mixer()
        if not mixer:
            return

        active_poses = []
        for pose_attribute in mixer.pose_attributes():
            if pose_attribute.get() > 0.0001:
                pose_name = pose_attribute.name(include_node=False)
                active_poses.append(mixer.get_pose(pose_name))

        mref.select(active_poses)

    def reset_pose(self):
        """
        Resets all the targets of the selected poses
        """
        mixer = self.component.mixer()
        if not mixer:
            return

        confirmation = qtility.request.confirmation(
            title="Reset Pose",
            message="Are you sure you want to reset the selected poses?",
        )
        if not confirmation:
            return

        identity_matrix = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        for pose in mref.selected():
            for _, target in self.pose_targets(mixer, pose.pose_name.get()):
                target.set_matrix(identity_matrix)
