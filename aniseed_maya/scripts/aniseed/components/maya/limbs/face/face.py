import os
import json
import mref
import qtility
import functools
import aniseed
import aniseed_toolkit
from maya import cmds
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
    with open(os.path.join(os.path.dirname(__file__), "face_data.json"), "r") as f:
        face_bones = json.load(f)

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

        # -- The mixer (from aniseed_toolkit.transformation.TransformationMixer) is a special
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

        # -- Store the name of the mixer so that our tools can easily interact
        # -- with it
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

        # -- Now we declare our outputs
        self.declare_output("FaceRig")

        # -- Build properties
        self.eyes_component = None

    def on_enter_stack(self):
        """
        When this component is added we will generate the face bones
        """
        # -- Get he selection, if there is no selection then we just build
        # -- at world space
        joint_parent = mref.selected()[0]

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
            bone = mref.get(
                aniseed_toolkit.joints.create(
                    description=bone_description["name"],
                    location=sides[bone_description["location"]],
                    parent=created_joints.get(bone_description["parent"], joint_parent).name(),
                    config=self.config,
                )
            )
            bone_matrix = bone_description["matrix"]
            bone.set_matrix(bone_matrix)

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
            aniseed_toolkit.transforms.create(
                classification=self.config.organisational,
                description="face",
                location=self.config.middle,
                config=self.config,
                parent=parent,
            )
        )

        # -- The attribute host is where we store all of the user facing attributes
        attribute_host = mref.get(self.input("Attribute Host").get() or org)
        visibility_attribute = attribute_host.add_attribute(
            name="direct_control_visibility",
            value=0,
            attribute_type="bool",
            keyable=False,
        )
        visibility_attribute.set(channelBox=True)
        print("i am in here")

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
        eyes_component.option("Add Blink").set(False)
        eyes_component.option("Add Pupil").set(True)
        eyes_component.run()
        self.eyes_component = eyes_component

        # -- Some of the controls come from the components we have just built, so we populate
        # -- our "created control" dictionary with the controls from those components to start
        # -- us off.
        created_controls = dict(
            jaw_middle=mouth_component.output("Jaw Control").get(),
            # upper_lip_middle=mouth_component.output("Upper Lip Control").get(),
            # lower_lip_middle=mouth_component.output("Lower Lip Control").get(),
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

            # -- Get teh joint we need to drive
            joint = mref.get(input_plug.get())

            # -- As a safety measure lets just make sure its not being
            # -- driven by anything else
            for constraint in joint.constraints():
                cmds.delete(constraint.name())

            # -- Create a control to drive the joint
            parent_label = data["parent"]
            control = aniseed_toolkit.control.create(
                description="direct_" + data["name"],
                location=data["location"],
                parent=created_controls.get(
                    parent_label,
                    direct_controls.get(data["parent"], org.name()),
                ),
                shape="core_cube",
                config=self.config,
                match_to=joint.name(),
            )

            # -- Hook up the constraints between the control
            # -- and the joint
            cmds.parentConstraint(
                control.ctl,
                joint.name(),
                maintainOffset=True,
            )
            cmds.scaleConstraint(
                control.ctl,
                joint.name(),
                maintainOffset=True,
            )

            # -- If a joint is declared as being "always on" then we will
            # -- not hook up its visibility overrides.
            is_always_on = data.get("is_always_on", False)
            if not is_always_on:
                for shape in mref.get(control.ctl).shapes():
                    visibility_attribute.connect(shape.visibility)

            # -- Store the offset node for the control
            direct_controls[input_plug.name()] = control.ctl

        cmds.parent(
            eyes_component.output("org").get(),
            direct_controls["upper_head_middle"],
        )
        # -- Create the bespoke inserted controls
        for label, created_control in created_controls.items():

            data = self.get_data_by_label(label)
            if not data:
                continue

            # -- Create a control which we will insert into the hierarchy
            created_control = aniseed_toolkit.control.get(created_control)

            # MARKER: These are not direct, they are something else
            control = aniseed_toolkit.control.create(
                description="direct_" + data["name"],
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

            # -- If a joint is declared as being "always on" then we will
            # -- not hook up its visibility overrides.
            is_always_on = data.get("is_always_on", False)
            if not is_always_on:
                for shape in mref.get(control.ctl).shapes():
                    visibility_attribute.connect(shape.visibility)

            direct_controls[label] = control.ctl

        for section in ["upper", "lower"]:
            for control_label in direct_controls.keys():
                if f"{section}_lip_" in control_label:
                    cmds.parent(
                        aniseed_toolkit.control.get(direct_controls[control_label]).org,
                        mouth_component.output(f"{section.title()} Lip Control").get(),
                    )

        # ----------------------------------------------------
        # -- Get the jaw as an mref object
        m_jaw = mref.get(mouth_component.output("Jaw Control").get())
        self.setup_jaw_behaviour(
            mouth_component.output("Upper Lip Control").get(),
            mouth_component.output("Lower Lip Control").get(),
            direct_controls,
            m_jaw,
            org,
        )

        # ----------------------------------------------------
        # -- The mixer is the functional heart of the whole setup. It is this mixer
        # -- which allows the transforms to behave like blendshapes. Therefore we
        # -- start by getting the stored transformation shape data
        mixer_data = self.option("Mixer Data").get()

        # -- Instance the mixer, but store a reference to the mixer in the component. This
        # -- allows any tools to inspect the component and know which mixer to interact
        # -- with.
        mixer = aniseed_toolkit.transformation.TransformMixer(parent=org.name())
        self.option("Mixer").set(mixer.node.name())

        # -- Cycle over all our direct controls and add them as deformers into our
        # -- mixer
        for plug_name, control in direct_controls.items():

            # -- Get the control, and then access the offset node
            control_instance = aniseed_toolkit.control.get(control)
            controller = mref.get(control_instance.ctl)
            control_offset = mref.get(control_instance.off)

            # -- Add a new deformer (node controlled by the mixer) and ensure its parent
            # -- is transformed to the location of the control offset
            mixer_deformer = mixer.add_deformer(plug_name)
            mixer_deformer.parent().match_to(control_offset)

            # -- Add a link to the controller
            mixer_deformer.add_attribute(
                "control_link",
                attribute_type="message",
                value=None,
            )
            controller.message.connect(mixer_deformer.control_link)

            # -- Finally we drive the control offsets local values through the mixers
            # -- deformer node.
            mixer_deformer.translate.connect(control_offset.translate)
            mixer_deformer.rotate.connect(control_offset.rotate)
            mixer_deformer.scale.connect(control_offset.scale)

        # -- Now we need to add each pose as defined in this components
        # -- pose list.
        for pose_name in self.pose_list:
            mixer.add_pose(name=pose_name)

        # -- Finally, using the stored data, we set the matrices of each
        # -- target. This is a little time consuming sadly, as its a LOT
        # -- of data!
        optimise = self.option("Optimise").get()

        if mixer_data:
            for pose in mixer_data["poses"]:
                for target_data in pose["targets"]:
                    deformer_name = target_data["name"]
                    pose_name = pose["name"]
                    target = mixer.get_target(pose_name, deformer_name)

                    if target:
                        target.set_matrix(target_data["transform"])

                        if optimise:
                            target.delete()

        # -- Create the high level control rig which drives everything.
        high_level_control_rig = HighLevelControlRig(component=self)
        high_level_control_rig.create(m_jaw)

        # -- Finally, we expose some attributes to show/hide the tongue and teeth. This will be
        # -- driven by an attribute on the jaw
        attribute = mref.get(mouth_component.output("Jaw Control").get()).add_attribute(
            "show_teeth_and_tongue",
            attribute_type="bool",
            value=False,
            keyable=False,
        )
        attribute.set(channelBox=True)

        for control in direct_controls.keys():
            if "teeth" in control or "tongue" in control:
                for shape in mref.get(direct_controls[control]).shapes():
                    attribute.connect(shape.visibility)

        # -- Set the outputs
        self.output("FaceRig").set(org.name())

    def setup_jaw_behaviour(self, upper_lip_control, lower_lip_control, direct_controls, jaw_control, org):
        """
        The jaw behaviour is a bespoke constraint setup which ensures the lips
        work together when the jaw opens. We cannot simply use a pose for this, as the
        jaw can shear.
        Instead we constrain the outer lips and mid lips progressively, but allow the
        animator to dial it in and out.

        :param direct_controls: A dictionary of all the created direct controls
        :param jaw_control: The jaw control
        :param org: This will be the parent of all the created nodes
        """

        # -- Add our smooth attributes - the animator can use these
        # -- to dial this behaviour in and out
        jaw_control.add_attribute("smooth_lips_left", attribute_type="float", keyable=True, value=1)
        jaw_control.add_attribute("smooth_lips_right", attribute_type="float", keyable=True, value=1)

        # -- Now build up the data structure. This determines what is constrained
        # -- to what and with what weights etc. It just means we only have to code
        # -- the actual logic once, and cycle over the data. The only reason this is
        # -- not in a data file (json) is because we're using variables within it.
        # upper_lip_control = direct_controls["upper_lip_middle"]
        # lower_lip_control = direct_controls["lower_lip_middle"]

        mouth_constraint_data = [
            {
                "constrain_this": direct_controls["upper_lip_outer_left"],
                "to_this": jaw_control.name(),
                "parent_space": upper_lip_control,
                "weights": [0.6, 0.4],
                "location": "left",
            },
            {
                "constrain_this": direct_controls["upper_lip_outer_right"],
                "to_this": jaw_control.name(),
                "parent_space": upper_lip_control,
                "weights": [0.6, 0.4],
                "location": "right",
            },
            {
                "constrain_this": direct_controls["lower_lip_outer_left"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0.4, 0.6],
                "location": "left",
            },
            {
                "constrain_this": direct_controls["lower_lip_outer_right"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0.4, 0.6],
                "location": "right",
            },
            {
                "constrain_this": direct_controls["upper_lip_mid_left"],
                "to_this": jaw_control,
                "parent_space": upper_lip_control,
                "weights": [0.8, 0.2],
                "location": "left",
            },
            {
                "constrain_this": direct_controls["upper_lip_mid_right"],
                "to_this": jaw_control,
                "parent_space": upper_lip_control,
                "weights": [0.8, 0.2],
                "location": "right",
            },
            {
                "constrain_this": direct_controls["lower_lip_mid_left"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0.2, 0.8],
                "location": "left",
            },
            {
                "constrain_this": direct_controls["lower_lip_mid_right"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0.2, 0.8],
                "location": "right",
            },
            {
                "constrain_this": direct_controls["upper_lip_inner_left"],
                "to_this": jaw_control.name(),
                "parent_space": upper_lip_control,
                "weights": [1, 0],
                "location": "left",
            },
            {
                "constrain_this": direct_controls["upper_lip_inner_right"],
                "to_this": jaw_control.name(),
                "parent_space": upper_lip_control,
                "weights": [1, 0],
                "location": "right",
            },
            {
                "constrain_this": direct_controls["lower_lip_inner_left"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0, 1],
                "location": "left",
            },
            {
                "constrain_this": direct_controls["lower_lip_inner_right"],
                "to_this": lower_lip_control,
                "parent_space": org.name(),
                "weights": [0, 1],
                "location": "right",
            },
            {
                "constrain_this": direct_controls["dimple_left"],
                "to_this": jaw_control,
                "parent_space": org.name(),
                "weights": [0.5, 0.5],
                "location": "left",
            },
            {
                "constrain_this": direct_controls["dimple_right"],
                "to_this": jaw_control,
                "parent_space": org.name(),
                "weights": [0.5, 0.5],
                "location": "right",
            },

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

        for constraint_data in mouth_constraint_data:

            # -- From the control get the control instance class and
            # -- access the offset, zero and org
            control_instance = aniseed_toolkit.control.get(constraint_data["constrain_this"])
            control_offset = control_instance.off
            control_zero = control_instance.zero
            control_org = control_instance.org

            # -- Get the control offset as an mref object
            constrain_this = mref.get(control_offset)

            # -- Create the proxy node. This is the node that has the constraints
            # -- on which represents the behaviour.
            proxy = mref.create(
                "transform",
                name=self.config.generate_name(
                    classification=self.config.mechanical,
                    description=constraint_data["constrain_this"] + "_smooth_proxy",
                    location=self.config.middle,
                ),
                parent=proxy_org,
            )
            proxy.match_to(constrain_this)

            # -- Set up the two constraints on the proxy
            cmds.parentConstraint(
                constraint_data["parent_space"],
                proxy.name(),
                maintainOffset=True,
            )
            cns = mref.get(
                mref.parentConstraint(
                    constraint_data["to_this"],
                    proxy.name(),
                    maintainOffset=True,
                )[0]
            )
            # -- Ensure the constraint is set to shortest as it
            # -- gives the best and most predictable result
            cns.interpType.set(2) # -- Shortest

            # -- Set the weights of that data based on the data
            for idx, weight in enumerate(constraint_data["weights"]):
                cns.weight_attributes()[idx].set(weight)

            # -- We now constrain the the control's zero to the proxy
            mref.parentConstraint(control_org, control_zero, maintainOffset=True)
            cns = mref.parentConstraint(proxy, control_zero, maintainOffset=True)[0]
            cns.interpType.set(2) # -- Shortest

            # -- Finally we drive the weight of that constraint based on the
            # -- attributes we expose to the user.
            attr = jaw_control.attr(f"smooth_lips_{constraint_data['location']}")
            attr.connect(cns.weight_attributes()[-1])

    def get_data_by_label(self, label: str):
        """
        The data inside the face_bones.json uses a key of name_location, and the
        lobael is considered to be those two elements jointed together. This
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
        if not mixer_name or not cmds.objExists(mixer_name):
            if not silent:
                qtility.request.message(
                    title="Cannot Snapshot Data",
                    message="You must build the rig before using the snapshot"
                )
            return

        # -- Instance the mixer object and return it
        mixer = aniseed_toolkit.transformation.TransformMixer(node=mixer_name)
        return mixer


class HighLevelControlRig:
    """
    The high level control rig is a set of controls which utlimately drives
    the transformation mixer. This makes for a much nicer animator-friendly
    interface.
    """

    def __init__(self, component):
        self.component = component

    def create(self, jaw):

        # -- This will give us a dictionary where the key is the name
        # -- of the pose and the values are the attributes driving that
        # -- pose.
        attribute_dictionary = self.construct_attribute_dictionary()

        # -- To allow a pose to be driven by multiple inputs we pre-append
        # -- a plus node in front of each one. This means we can reliably
        # -- know that attribute we need to connect to is an array attribute.
        addition_nodes = self.initialise_driving_adds(attribute_dictionary)

        # -- Outer Lip Pullers
        for side in ["left", "right"]:
            self.setup_lip_puller(
                location=side,
                guide=self.component.input(f"{side}_lip_corner_guide").get(),
                jaw=jaw,
                parent=self.component.input("Parent").get(),
                connection_map=addition_nodes,
            )

        # -- Top and Bottom Central Lips
        for location in ["upper", "lower"]:
            self.setup_central_lip(
                section=location,
                guide=self.component.input(f"{location}_lip_guide").get(),
                parent=self.component.input("Parent").get(),
                connection_map=addition_nodes,
            )

        # -- Nose
        self.setup_nose(
            guide=self.component.input("nose_guide").get(),
            parent=self.component.input("Parent").get(),
            connection_map=addition_nodes,
        )

        # -- Inner & Outer Brows
        for side in ["left", "right"]:
            self.setup_inner_brow(
                location=side,
                guide=self.component.input(f"{side}_brow_inner_guide").get(),
                parent=self.component.input("Parent").get(),
                connection_map=addition_nodes,
            )

            self.setup_outer_brow(
                location=side,
                guide=self.component.input(f"{side}_brow_outer_guide").get(),
                parent=self.component.input("Parent").get(),
                connection_map=addition_nodes,
            )
            self.setup_eye(
                location=side,
                control=mref.get(self.component.eyes_component.output(f"{side.title()} Eye Control").get()),
                connection_map=addition_nodes,
            )

    def initialise_driving_adds(self, attribute_dictionary):
        """
        Each pose can have multiple inputs. To ensure that we can reliably
        drive each pose by multiple mechanical approaches we add a
        plusMinusAverage node which drives the attribute. We then
        update the dictionary such that the plus minue average attribute
        is the value instead of the pose attribute itself.
        """
        driving_additions = dict()

        for label, attribute in attribute_dictionary.items():
            node = mref.create("plusMinusAverage")
            node.attr("output1D").connect(attribute)

            driving_additions[label] = node.attr("input1D")
        return driving_additions

    def construct_attribute_dictionary(self):
        """
        This will cycle the pose list and create a dictionary where the key
        is the name of the pose and value is the attribute that we intend to
        drive that pose with.
        """
        mixer = self.component.mixer(silent=True)
        attribute_dictionary = dict()
        for pose in self.component.pose_list:
            attribute_dictionary[pose] = mixer.node.attr(pose)

        return attribute_dictionary

    def resolve_control(
            self,
            description,
            identity_label,
            location,
            parent,
            guide,
            lock_and_hide=None
    ):
        """
        We allow the user to specify a control directly, or to allow us to create
        it as part of the rig build. This function will return the existing control
        if one has been specified, otherwise it will generate a new one.
        """
        # -- Read the input value If it is not blank then we return that
        # -- node rather than create one.
        control_name = self.component.input(f"{identity_label}_control").get()
        if control_name:
            return mref.get(control_name)

        # -- To reach here we need to construct a new control
        new_control_setup = aniseed_toolkit.control.create(
            description="Facial" + description,
            location=location,
            parent=self.component.input(f"{identity_label}_parent").get() or parent,
            shape=self.component.input(f"{identity_label}_shape").get() or "core_cube",
            config=self.component.config,
            match_to=guide or None,
        )

        # -- Lock and hide any attributes that should not be animatable.
        if lock_and_hide:
            aniseed_toolkit.attributes.lock_and_hide(
                [new_control_setup.ctl],
                lock_and_hide,
                lock=True,
                hide=True,
            )

        # -- Start by creating the control
        return mref.get(new_control_setup.ctl)

    def clamped_connection(
            self,
            driving_attribute,
            destination_attribute,
            clamp_min=0,
            clamp_max=1,
    ):
        """
        This will connect the driving attribute to the destination attribute
        but with a clamp in between set to the given values.
        """
        # -- Create and setup the clamp node
        clamp = mref.create("clamp")
        clamp.attr(f"maxR").set(clamp_max)
        clamp.attr(f"minR").set(clamp_min)

        # -- Hook up the connections
        driving_attribute.connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

        # -- Return a dictionary. We do this because we have a variety of different
        # -- connection methods, some of which return mutliple objects, therefore this
        # -- just creates a consistent return type for them all.
        return {
            "clamp": clamp,
        }

    def clamped_reversal(
            self,
            driving_attribute,
            destination_attribute,
            clamp_min=0,
            clamp_max=1,
    ):
        """
        This will connect the driving attribute to the destination attribute
        but with a reversal (*-1) and then clamping that result to the given
        clamp values.
        """
        # -- Push In Behaviour
        clamp = mref.create("clamp")
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)

        # -- Setup the inversion node
        inverse = mref.create("floatMath")
        inverse.attr("operation").set(2)  # -- Multiply
        inverse.attr("floatB").set(-1)

        # -- Hook up the connections
        driving_attribute.connect(inverse.attr("floatA"))
        inverse.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

        return {
            "clamp": clamp,
            "multiplier": inverse,
        }

    def expose_reversal_direct(
            self,
            control: mref.ReferencedItem,
            label,
            destination_attribute,
            clamp_min=0,
            clamp_max=1,
    ):
        """
        This will expose the given destination attribute up to the control
        but it will also reverse the value and clamp it.
        """
        # -- Create the attribute if it does not already exist
        if control.has_attribute(label):
            attribute = control.attr(label)
        else:
            attribute = control.add_attribute(
                label,
                value=0,
                attribute_type="float",
                keyable=True,
            )

        # -- Setup the clamp
        clamp = mref.create("clamp")
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)

        # -- Set up the inversion
        inverse = mref.create("floatMath")
        inverse.attr("operation").set(2)  # -- Multiply
        inverse.attr("floatB").set(-1)

        # -- Hook up the connections
        attribute.connect(inverse.attr("floatA"))
        inverse.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

    def expose_direct(
            self,
            control: mref.ReferencedItem,
            label, destination_attribute,
            clamp_min=0,
            clamp_max=1,
            do_next=True,
    ):
        """
        This will expose the attribute on the control, allowing the animator to drive
        it directly.
        """
        # -- Create the attribute if it does not already exist
        if control.has_attribute(label):
            attribute = control.attr(label)
        else:
            attribute = control.add_attribute(
                label,
                value=0,
                attribute_type="float",
                keyable=True,
            )

        # -- Setup the clamp
        clamp = mref.create("clamp")
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)

        # -- Have the animator facing attribute drive the clamp
        attribute.connect(clamp.attr("inputR"))

        # -- Hook up the clamp to the destination
        if do_next:
            clamp.attr("outputR").connect_next(destination_attribute)
        else:
            clamp.attr("outputR").connect(destination_attribute)

        return {
            "clamp": clamp,
        }

    def setup_eye(self, location, control, connection_map):
        """
        Sets up the blinks
        """
        self.expose_direct(
            control=control,
            label=f"blink",
            destination_attribute=connection_map[f"{location}_blink"],
        )

    def setup_inner_brow(self, location, guide, parent, connection_map):
        """
        This sets up the control connections for the inner eye
        brow.
        """
        # -- Create the control
        control = self.resolve_control(
            description="brow_inner",
            identity_label=f"{location}_brow_inner",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tz"],
        )

        # -- Hook up the transformation connections
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

        # -- Hook up the animator-facing direct controls
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

    def setup_nose(self, guide, parent, connection_map):
        """
        This sets up the control connections for the nose control
        """
        # -- Create the control
        control = self.resolve_control(
            description="nose",
            identity_label="nose",
            location=self.component.config.middle,
            parent=parent,
            guide=guide,
        )

        # -- Expose the direct animator facing controls
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
        """
        This sets up the control connections for the central lip (either upper
        or lower)

        :param section: lower or upper
        :param guide: guide to denote the location/transformation of the control
        :param parent: parent for the control
        :param connection_map: A dictionary of labels where the value is the
            attribute it represents.
        """
        # -- Create our control
        control = self.resolve_control(
            description=f"{section}_lip",
            identity_label=f"{section}_lip",
            location=self.component.config.middle,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tx"],
        )

        # -- Hook up out transformation connections
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

        # -- Hook up our animator facing attributes
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
        #
        # # -- Set up the sneering fixer - this resolves the middle of the lips
        # # -- when both sneers are dialed in
        # add_sneers = mref.create("floatMath")
        # control.attr("right_sneer").connect(add_sneers.attr("floatA"))
        # control.attr("left_sneer").connect(add_sneers.attr("floatB"))
        #
        # # -- As we're blending two float tracks we divide it in two.
        # divide_by_two = mref.create("floatMath")
        # divide_by_two.attr("operation").set(2)  # -- Multiply
        # divide_by_two.attr("floatB").set(0.5)
        # add_sneers.attr("outFloat").connect(divide_by_two.attr("floatA"))
        #
        # # -- As well as dialing it in automatically we also want to expose
        # # -- it as a direct animatable attribute.
        # add_direct = mref.create("floatMath")
        # divide_by_two.attr("outFloat").connect(add_direct.attr("floatA"))

        # -- Set up the sneering fixer - this resolves the middle of the lips
        # -- when both sneers are dialed in
        multiply_sneers = mref.create("floatMath")
        multiply_sneers.attr("operation").set(2)  # -- Multiply
        control.attr("right_sneer").connect(multiply_sneers.attr("floatA"))
        control.attr("left_sneer").connect(multiply_sneers.attr("floatB"))

        # # -- As we're blending two float tracks we divide it in two.
        # divide_by_two = mref.create("floatMath")
        # divide_by_two.attr("operation").set(2)  # -- Multiply
        # divide_by_two.attr("floatB").set(0.5)
        # add_sneers.attr("outFloat").connect(divide_by_two.attr("floatA"))

        # -- As well as dialing it in automatically we also want to expose
        # -- it as a direct animatable attribute.
        add_direct = mref.create("floatMath")
        multiply_sneers.attr("outFloat").connect(add_direct.attr("floatA"))

        self.expose_direct(
            control=control,
            label="sneer_fixup",
            destination_attribute=add_direct.attr("floatB"),
            clamp_min=-1,
            clamp_max=1,
            do_next=False,
        )

        # -- Ensure the result is always clamped.
        clamp = mref.create("clamp")
        clamp.attr("minR").set(-1)
        clamp.attr("maxR").set(1)
        add_direct.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(connection_map[f"{section}_sneer"])

    def setup_lip_puller(self, location, guide, jaw, parent, connection_map):
        """
        This will create the control for the lip pullers (left and right)
        """
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
        multiply_jaw.operation.set(2)  # - multiply
        multiply_jaw.floatB.set(1.0 / 25)
        jaw.rotateX.connect(multiply_jaw.floatA)

        multiply_inverter = mref.create("floatMath")
        multiply_inverter.operation.set(2)
        multiply_inverter.floatA.set(-1.0)
        control.translateX.connect(multiply_inverter.floatB)

        multiply_mix = mref.create("floatMath")
        multiply_mix.operation.set(2)  # - Multiply
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

    def setup_outer_brow(self, location, guide, parent, connection_map):
        """
        This will create the control for the outer brows (left and right)
        """
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
            aniseed_toolkit.mirror.global_mirror(
                transforms=[target.name() for target in source_targets],
                name_replacement=[direction_mapping[0], direction_mapping[1]],
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

    def snap_pose(self):
        """
        This will snap the targets of the given pose to the controls.
        """
        mixer = self.component.mixer()
        if not mixer:
            return

        matrices = dict()

        for pose in mref.selected():
            source_pose_name = pose.pose_name.get()
            deformers = mixer.deformers()

            for deformer in deformers:
                target = mixer.get_target(source_pose_name, deformer.deformer_name.get())
                controller = deformer.control_link.inputs()[0].node()

                matrices[target] = controller.get_matrix(space="world")

                for axis in ["X", "Y", "Z"]:
                    try: controller.attr(f"translate{axis}").set(0)
                    except: pass
                    try: controller.attr(f"rotate{axis}").set(0)
                    except: pass
                    try: controller.attr(f"scale{axis}").set(1)
                    except: pass

                if "deformer_upper_lip_inner_left" in target.name():
                    print(deformer.name())
            print(matrices)
            for i in range(len(deformers)):
                for target, matrix in matrices.items():
                    n = mref.create("transform", name="exampl_" + target.name())
                    n.set_matrix(matrix, space="world")
                    cmds.xform(target.name(), matrix=matrix, worldSpace=True)
                    #target__deformer_upper_lip_inner_left__pose_upper_lip_curl_out
                    # target.set_matrix(matrix, space="world")

    def select_pose(self):
        mixer = self.component.mixer()
        if not mixer:
            return

        targets = []

        for pose in mref.selected():
            source_pose_name = pose.pose_name.get()

            for deformer in mixer.deformers():
                targets.append(mixer.get_target(source_pose_name, deformer.deformer_name.get()))

        mref.select(targets)

    def snapshot_data(self, silent=False):
        mixer_name = self.component.option("Mixer").get()
        # mixer_name = "transformMixer"
        if not mixer_name or not cmds.objExists(mixer_name):
            if not silent:
                qtility.request.message(
                    title="Cannot Snapshot Data",
                    message="You must build the rig before using the snapshot"
                )
            return

        mixer = aniseed_toolkit.transformation.TransformMixer(node=mixer_name)
        self.component.option("Mixer Data").set(mixer.serialise())

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
            json.dump(self.component.mixer().serialise(), f, indent=4)

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
            self.component.option("Mixer Data").set(json.load(f))

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

        self.component.option("Mixer Data").set([])

    def select_mixer(self):
        mixer = self.component.mixer()
        if mixer:
            cmds.select(mixer.node.name())

    def select_active_poses(self):
        mixer = self.component.mixer()
        if not mixer:
            print("no mixer")
            return

        active_poses = []
        for pose_attribute in mixer.pose_attributes():
            if pose_attribute.get() > 0.0001:
                pose_name = pose_attribute.name(include_node=False)
                pose_node = mixer.get_pose(pose_name)
                active_poses.append(pose_node)

        mref.select(active_poses)

    def reset_pose(self):
        mixer = self.component.mixer()

        if not mixer:
            return

        confirmation = qtility.request.confirmation(
            title="Reset Pose",
            message=f"Are you sure you want to reset the selected poses?",
        )
        if not confirmation:
            return

        identify_matrix = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        for pose in mref.selected():
            pose_name = pose.pose_name.get()
            deformers = mixer.deformers()

            for deformer in deformers:
                target = mixer.get_target(pose_name, deformer.deformer_name.get())
                target.set_matrix(identify_matrix)