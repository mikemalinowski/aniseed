"""
Provides the "Limb : Face (refined experimental)" component: a reworking of
"Limb : Face" (aniseed_standard, which is used in production and so is left
untouched) to iterate on.

Like "Limb : Face" it generates a face skeleton from skeleton.json and builds
a bone driven face rig as a single component: the mouth and eyes (built by
the "Limb : Mouth" and "Limb : Eyes" components, run internally), a control
for every other face bone, a matrix mixer of poses driving the controls
(see au.rig.matrix_mixer) and a high level animator control rig driving the
poses. It differs in that:

    * Every control is named by the rig configuration from its bone (there
      are no "direct" controls), and the high level controls are prefixed
      with control_prefix so they cannot clash with the bone controls.
    * The mixer drives the mouth and eyes controls themselves, rather than
      extra controls inserted above them, and any other control can be added
      to it in the Matrix Mixer Pose Editor (stored in Driven Objects).
    * The high level controls are placed at guide locators created with the
      skeleton, rather than through per control overrides.
"""
import os
import copy
import json
import logging

from maya import cmds

import mref
import qtility
import aniseed
import aniseed_utilities as au
from aniseed import toolkits
from aniseed_standard import rigging

log = logging.getLogger(__name__)

_DIRECTORY = os.path.dirname(__file__)

with open(os.path.join(_DIRECTORY, "skeleton.json"), "r") as _f:
    # -- Each bone: name, location (left/right/middle), parent (a bone label,
    # -- or head_middle for the head), matrix, and is_always_on for a bone
    # -- whose control is always shown
    FACE_BONES = json.load(_f)

with open(os.path.join(_DIRECTORY, "default_pose_data.json"), "r") as _f:
    # -- The poses used when the component has none stored, keyed by bone label
    DEFAULT_POSE_DATA = json.load(_f)

# -- The bones whose controls are made by the mouth: the joint input each is
# -- given to and the output holding its control
MOUTH_BONES = {
    "jaw_middle": ("Jaw Joint", "Jaw Control"),
    "upper_lip_middle": ("Upper Lip Joint", "Upper Lip Control"),
    "lower_lip_middle": ("Lower Lip Joint", "Lower Lip Control"),
}

# -- The bones whose controls are made by the eyes, in the same form
EYE_BONES = {
    f"{part}_{side}": (f"{side.title()} {label} Joint", f"{side.title()} {label} Control")
    for side in ["left", "right"]
    for part, label in [
        ("eye", "Eye"),
        ("eye_upper_lid", "Upper Eye Lid"),
        ("eye_lower_lid", "Lower Eye Lid"),
        ("eye_pupil", "Pupil"),
    ]
}

# -- The high level controls, in build order: (description, location, the
# -- bone labels its guide is placed at - midway between them if there are
# -- several - taking its orientation from the first)
HIGH_LEVEL_CONTROLS = {
    "left_lip_corner": ("lip_corner", "left", ["upper_lip_outer_left", "lower_lip_outer_left"]),
    "right_lip_corner": ("lip_corner", "right", ["upper_lip_outer_right", "lower_lip_outer_right"]),
    "upper_lip": ("upper_lip", "middle", ["upper_lip_middle"]),
    "lower_lip": ("lower_lip", "middle", ["lower_lip_middle"]),
    "nose": ("nose", "middle", ["nose_middle"]),
    "left_brow_inner": ("brow_inner", "left", ["brow_inner_left"]),
    "left_brow_outer": ("brow_outer", "left", ["brow_outer_left"]),
    "right_brow_inner": ("brow_inner", "right", ["brow_inner_right"]),
    "right_brow_outer": ("brow_outer", "right", ["brow_outer_right"]),
}

# -- Bones whose controls are shown by the jaw's show_teeth_and_tongue
# -- attribute rather than the detail control visibility
TEETH_AND_TONGUE = ("teeth", "tongue")

# -- The lips which follow the jaw as it opens. Each row is applied to the
# -- left and then the right control: (bone name, constrained towards, in
# -- the space of, weights). The jaw is a special case of the mouth's
# -- controls, so these are resolved when the face is built.
LIP_SMOOTHING = [
    ("upper_lip_outer", "jaw", "upper_lip", [0.6, 0.4]),
    ("lower_lip_outer", "lower_lip", "org", [0.4, 0.6]),
    ("upper_lip_mid", "jaw", "upper_lip", [0.8, 0.2]),
    ("lower_lip_mid", "lower_lip", "org", [0.2, 0.8]),
    ("upper_lip_inner", "jaw", "upper_lip", [1, 0]),
    ("lower_lip_inner", "lower_lip", "org", [0, 1]),
    ("dimple", "jaw", "org", [0.5, 0.5]),
]


def bone_label(bone: dict) -> str:
    """
    Returns the label of a bone: its name and location (brow_inner_left)
    """
    return f"{bone['name']}_{bone['location']}"


class FaceRefinedComponent(aniseed.RigComponent):
    """
    Creates the face skeleton when added, and builds the mouth, eyes, a
    control for every other bone, a matrix mixer of poses driving all of
    those controls (plus any added in the pose editor) and a high level
    control rig driving the poses.
    """

    identifier = "Limb : Face (refined experimental)"
    icon = os.path.join(os.path.dirname(__file__), "face_refined.png")

    # -- Prefixed onto the description of every high level control (and the
    # -- guides and mixer nodes), so they cannot clash with the bone controls
    control_prefix = "facial"

    # -- The options naming the mixer node and holding its data, and the
    # -- option holding the extra driven objects, which the Matrix Mixer Pose
    # -- Editor stores into
    mixer_options = ("Mixer", "Mixer Data")
    mixer_driven_option = "Driven Objects"

    # -- The poses the face always builds, each driven by the high level
    # -- controls. These are the equivalent of blendshapes.
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

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent and Attribute Host inputs, a joint input per bone
        in skeleton.json and a guide input per high level control. Options
        hold the extra driven objects, the mixer data and node, and the mouth
        and eyes settings. The single output is the face org.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the face is built under (typically the head control)",
            group="Control Rig",
        )

        self.declare_input(
            name="Attribute Host",
            value="",
            description="The node the animator facing attributes are put on. If not given, the face org is used.",
            group="Control Rig",
        )

        for bone in FACE_BONES:
            self.declare_input(
                name=bone_label(bone),
                value="",
                group="Joints",
            )

        for control_label in HIGH_LEVEL_CONTROLS:
            self.declare_input(
                name=f"{control_label}_guide",
                value="",
                description="The node this high level control is placed at",
                group="Guides",
                validate=False,
            )

        self.declare_option(
            name="Driven Objects",
            value=[],
            description=(
                "Controls (or addresses) the mixer drives as well as the face's own. They are added and removed "
                "in the Matrix Mixer Pose Editor, and their poses are stored under these names."
            ),
        )

        self.declare_option(
            name="Open Pose Editor",
            value=None,
            description="Opens the Matrix Mixer Pose Editor on the built face, to edit, mirror, save and load its poses",
        )

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

        # -- The poses ({"poses": [{"name": ..., "matrices": {key: matrix}}]}),
        # -- keyed by bone label for the face's own controls and by Driven
        # -- Objects entry for the others. When empty, the defaults are used.
        self.declare_option(
            name="Mixer Data",
            value={},
            hidden=True,
        )

        self.declare_option(
            name="Mixer",
            value="",
            hidden=True,
            description="The name of the mixer node made by the last build",
        )

        self.declare_output("FaceRig")

    # ----------------------------------------------------------------------
    def on_enter_stack(self):
        """
        Creates the face joints under the selection (or at the world origin)
        and a guide for each high level control, fills in their inputs and
        hooks the Parent input to the parent component.
        """
        joints = self._create_joints()
        self._create_guides(joints)
        self.input("Parent").hook_to_parent()

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for every input.
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        """
        Returns an object list for the Driven Objects and a button for Open
        Pose Editor.
        """
        if option_name == "Driven Objects":
            return aniseed.widgets.ObjectList()

        if option_name == "Open Pose Editor":
            return aniseed.widgets.ButtonWidget(button_name="Open Pose Editor", func=self.open_pose_editor)

        return None

    # ----------------------------------------------------------------------
    def run(self) -> bool:
        """
        Builds the face: the org, the mouth and eyes, the bone controls, the
        lips following the jaw, the mixer, the high level controls, the
        control visibilities and the eye attributes on the attribute host.
        """
        org = mref.get(
            au.scene.transforms.create(
                classification=self.config.organisational,
                description="face",
                location=self.config.middle,
                config=self.config,
                parent=self.input("Parent").get(),
            )
        )
        attribute_host = mref.get(self.input("Attribute Host").get() or org)

        detail_visibility = attribute_host.add_attribute(
            name="detail_control_visibility",
            value=0,
            attribute_type="bool",
            keyable=False,
        )
        detail_visibility.set(channelBox=True)

        mouth = self._build_mouth(org)
        eyes = self._build_eyes(org)

        # -- The control of every bone, keyed by bone label: first those of
        # -- the mouth and eyes, then one made for each of the other bones
        controls = {
            label: mouth.output(output_name).get()
            for label, (_, output_name) in MOUTH_BONES.items()
        }
        controls.update(
            {
                label: eyes.output(output_name).get()
                for label, (_, output_name) in EYE_BONES.items()
            }
        )
        bone_controls = self._create_bone_controls(org, controls)
        controls.update(bone_controls)

        # -- The eyes are built under the face org, so their central aim
        # -- control stays in face space, but the eyes themselves follow the
        # -- upper head
        mref.get(eyes.output("org").get()).set_parent(controls["upper_head_middle"])

        for label, control in bone_controls.items():
            if not self._bone(label).get("is_always_on", False):
                self.drive_shape_visibility(control, detail_visibility)

        jaw = mref.get(controls["jaw_middle"])
        self._setup_lip_smoothing(controls, org, attribute_host)

        mixer = self._build_mixer(org, controls)

        HighLevelControlRig(component=self, attribute_host=attribute_host).create(
            mixer=mixer,
            parent=self.input("Parent").get(),
            jaw=jaw,
            eye_controls={side: mref.get(controls[f"eye_{side}"]) for side in ["left", "right"]},
        )

        teeth_and_tongue_visibility = jaw.add_attribute(
            "show_teeth_and_tongue",
            attribute_type="bool",
            value=False,
            keyable=False,
        )
        teeth_and_tongue_visibility.set(channelBox=True)

        # -- The teeth and tongue are always on, so nothing else drives
        # -- their visibility
        for label, control in bone_controls.items():
            if label.startswith(TEETH_AND_TONGUE):
                self.drive_shape_visibility(control, teeth_and_tongue_visibility)

        self._proxy_eye_attributes(controls, attribute_host)

        self.output("FaceRig").set(org.name())
        return True

    # ----------------------------------------------------------------------
    def _create_joints(self) -> dict:
        """
        Creates a joint per bone, under its parent bone's joint (or the
        selection, for a bone under the head), set to its matrix, and sets
        the bone's input to it.

        Returns:
            The joint name for each bone label
        """
        selected = mref.selected()
        root = selected[0].name() if selected else None

        joints = dict()
        for bone in FACE_BONES:
            joint = mref.get(
                au.scene.joints.create(
                    description=bone["name"],
                    location=bone["location"],
                    parent=joints.get(bone["parent"], root),
                    config=self.config,
                )
            )
            joint.set_matrix(bone["matrix"])

            label = bone_label(bone)
            joints[label] = joint.name()
            self.input(label).set(joint.name())

        return joints

    def _create_guides(self, joints: dict):
        """
        Creates a locator for each high level control, in a guides group at
        the world, and sets the control's guide input to it. Each sits at
        (and is oriented to) the bone it represents; a lip corner sits midway
        between the outer upper and lower lip bones of its side. They can be
        moved afterwards to place the controls.

        Args:
            joints: The joint name for each bone label
        """
        group = au.scene.transforms.create(
            classification=self.config.organisational,
            description=f"{self.control_prefix}_guides",
            location=self.config.middle,
            config=self.config,
            parent=None,
        )

        for control_label, (description, location, labels) in HIGH_LEVEL_CONTROLS.items():
            name = self.config.generate_name(
                classification="guide",
                description=f"{self.control_prefix}_{description}",
                location=location,
            )
            locator = cmds.spaceLocator(name=name)[0]
            locator = cmds.parent(locator, group)[0]

            cmds.xform(locator, worldSpace=True, matrix=cmds.xform(joints[labels[0]], query=True, worldSpace=True, matrix=True))
            positions = [cmds.xform(joints[label], query=True, worldSpace=True, translation=True) for label in labels]
            cmds.xform(
                locator,
                worldSpace=True,
                translation=[sum(axis) / len(positions) for axis in zip(*positions)],
            )

            self.input(f"{control_label}_guide").set(cmds.ls(locator, long=True)[0])

        cmds.select(clear=True)

    def _build_mouth(self, org):
        """
        Builds the mouth (jaw, upper and lower lip controls) under the org,
        through the "Limb : Mouth" component run internally.

        Returns:
            The mouth component
        """
        mouth = self.stack.component_library.request("Limb : Mouth")(label="", stack=self.stack)
        mouth.input("Parent").set(org.name())

        for label, (joint_input, _) in MOUTH_BONES.items():
            mouth.input(joint_input).set(self.input(label).get())

        mouth.option("Aim Control Distance Multiplier").set(self.option("Mouth Target Distance Multiplier").get())
        mouth.run()
        return mouth

    def _build_eyes(self, org):
        """
        Builds the eyes (eye, lid and pupil controls and a central aim) under
        the org, through the "Limb : Eyes" component run internally.

        Returns:
            The eyes component
        """
        eyes = self.stack.component_library.request("Limb : Eyes")(label="", stack=self.stack)
        eyes.input("Parent").set(org.name())

        for label, (joint_input, _) in EYE_BONES.items():
            eyes.input(joint_input).set(self.input(label).get())

        eyes.option("Aim Distance").set(self.option("Eye Target Distance").get())
        eyes.option("Max Blink Rotation").set(self.option("Max Blink Rotation").get())
        eyes.option("Add Blink").set(False)
        eyes.option("Add Pupil").set(True)
        eyes.run()
        return eyes

    def _create_bone_controls(self, org, controls: dict) -> dict:
        """
        Creates a control for every bone the mouth and eyes do not control,
        named from the bone, and constrains the bone's joint to it. Each is
        parented under its parent bone's control (or the org, for a bone
        under the head), except the lip bones, which go under the mouth's
        upper or lower lip control so the lips move together.

        Args:
            org: The face org
            controls: The control of each bone the mouth and eyes control

        Returns:
            The control for each bone label, in skeleton order
        """
        bone_controls = dict()

        for bone in FACE_BONES:
            label = bone_label(bone)

            if label in controls:
                continue

            parent = controls.get(bone["parent"]) or bone_controls.get(bone["parent"]) or org.name()
            for section in ["upper", "lower"]:
                if label.startswith(f"{section}_lip_"):
                    parent = controls[f"{section}_lip_middle"]

            joint = mref.get(self.input(label).get())

            control = au.rig.control.create(
                description=bone["name"],
                location=bone["location"],
                parent=parent,
                shape="core_cube",
                config=self.config,
                match_to=joint.name(),
            )

            au.scene.constraints.parent_and_scale(
                control.ctl,
                joint,
                maintain_offset=True,
            )

            bone_controls[label] = control.ctl

        return bone_controls

    def _setup_lip_smoothing(self, controls: dict, org, attribute_host):
        """
        Makes the lips follow the jaw as it opens. We cannot simply use a pose
        for this, as the jaw can shear. Instead each lip control's zero is
        constrained, by the weights in LIP_SMOOTHING, between the control's
        own space and the jaw (or lower lip), dialled in and out by the
        smooth_lips_<side> attributes on the jaw.

        Args:
            controls: The control of each bone label
            org: The face org
            attribute_host: The node the smoothing attributes are proxied onto
        """
        jaw = mref.get(controls["jaw_middle"])
        targets = {
            "jaw": jaw,
            "upper_lip": controls["upper_lip_middle"],
            "lower_lip": controls["lower_lip_middle"],
            "org": org,
        }

        attribute_host.add_separator_attribute()
        for side in ["left", "right"]:
            smooth_attribute = jaw.add_attribute(
                f"smooth_lips_{side}",
                attribute_type="float",
                keyable=True,
                value=1,
            )
            attribute_host.add_proxy(
                smooth_attribute.name(include_node=False),
                source_attribute=smooth_attribute,
            )

        # -- The proxies the constraints act through are kept together
        proxy_org = mref.create(
            "transform",
            name=self.config.generate_name(
                classification=self.config.organisational,
                description="lip_smoothing",
                location=self.config.middle,
            ),
            parent=org,
        )
        proxy_org.match_to(org)

        for name, towards, space, weights in LIP_SMOOTHING:
            for side in ["left", "right"]:
                control = au.rig.control.get(controls[f"{name}_{side}"])

                # -- The proxy carries the behaviour: it sits in the
                # -- control's space, weighted towards the jaw (or lower lip)
                proxy = mref.create(
                    "transform",
                    name=self.config.generate_name(
                        classification=self.config.mechanical,
                        description=f"{name}_smoothing",
                        location=side,
                    ),
                    parent=proxy_org,
                )
                proxy.match_to(mref.get(control.off))

                mref.parentConstraint(targets[space], proxy, maintainOffset=True)
                constraint = mref.parentConstraint(targets[towards], proxy, maintainOffset=True)[0]
                constraint.interpType.set(2)  # -- Shortest

                for index, weight in enumerate(weights):
                    constraint.weight_attributes()[index].set(weight)

                # -- The control's zero blends between its own org and the
                # -- proxy, by the smooth_lips attribute
                mref.parentConstraint(control.org, control.zero, maintainOffset=True)
                constraint = mref.parentConstraint(proxy, control.zero, maintainOffset=True)[0]
                constraint.interpType.set(2)  # -- Shortest

                au.scene.constraints.blend_weights(
                    jaw.attr(f"smooth_lips_{side}"),
                    constraint,
                )

    def _build_mixer(self, org, controls: dict) -> au.rig.matrix_mixer.MatrixMixer:
        """
        Builds the mixer, driving every control of the face (keyed by bone
        label) and every Driven Objects entry that exists, then adds the
        built-in poses (in pose_list order) and applies the stored poses (or
        the defaults), which adds any custom poses they hold.

        Args:
            org: The face org, which the mixer node goes under
            controls: The control of each bone label

        Returns:
            The mixer
        """
        mixer = au.rig.matrix_mixer.MatrixMixer(parent=org.name(), namer=self._mixer_namer())
        self.option("Mixer").set(mixer.node.name())

        with mixer:
            for label, control in controls.items():
                mixer.add_driven(control, key=label)

            for entry in self.option("Driven Objects").get() or list():
                node_name = self._resolve(entry)

                if not node_name or not mref.objExists(node_name):
                    log.warning(f"{self.label()} : {entry!r} resolves to {node_name!r}, which does not exist")
                    continue

                try:
                    mixer.add_driven(node_name, key=entry)

                except ValueError as error:
                    log.warning(f"{self.label()} : {error}")

            for pose_name in self.pose_list:
                mixer.add_pose(name=pose_name)

            missing = mixer.apply_data(self.option("Mixer Data").get() or copy.deepcopy(DEFAULT_POSE_DATA))

        for key in missing:
            log.warning(f"{self.label()} : Poses are stored for {key!r}, which is not driven. They are kept.")

        return mixer

    def _proxy_eye_attributes(self, controls: dict, attribute_host):
        """
        Proxies the animator facing attributes of each eye control onto the
        attribute host, prefixed with the side.
        """
        for side in ["left", "right"]:
            eye_control = mref.get(controls[f"eye_{side}"])

            attribute_host.add_separator_attribute()
            for attr in eye_control.attributes(userDefined=True):

                # -- Skip separator attributes
                if not attr.name(include_node=False).replace("_", ""):
                    continue

                # -- Only proxy what the animator sees in the channel box. This
                # -- skips the control's internal metadata (the link_* message
                # -- attributes and the naming_data string), which have no use
                # -- on the face host, and with which duplicating the host (as
                # -- Studio Library does when saving animation) crashes Maya.
                if not attr.is_in_channel_box():
                    continue

                try:
                    attribute_host.add_proxy(f"{side}_" + attr.name(include_node=False), attr)
                except RuntimeError:
                    log.warning(f"Could not proxy {attr.name()} onto the face attribute host")

    # ----------------------------------------------------------------------
    @staticmethod
    def drive_shape_visibility(control, attribute, force=False):
        """
        Connects the given attribute to the visibility of every shape
        of the given control.
        """
        for shape in mref.get(control).shapes():
            attribute.connect(shape.attr("visibility"), force=force)

    @staticmethod
    def _bone(label: str) -> dict:
        """
        Returns the skeleton.json data of the bone with the given label, or an
        empty dictionary if there is none.
        """
        for bone in FACE_BONES:
            if bone_label(bone) == label:
                return bone
        return dict()

    def _resolve(self, value):
        """
        Returns the value of the attribute the given value addresses, or the
        value itself if it is not an address.
        """
        if not value:
            return value

        attribute = self.rig.resolve_attribute(value)
        return attribute.get() if attribute else value

    def _mixer_namer(self):
        """
        Returns the callable which names the mixer's nodes with the rig
        configuration (mechanical, prefixed with control_prefix).
        """
        return lambda label: self.config.generate_name(
            classification=self.config.mechanical,
            description=f"{self.control_prefix}_{label}",
            location=self.config.middle,
        )

    # ----------------------------------------------------------------------
    def mixer(self, silent=False):
        """
        Returns the mixer built by the last build, or None if it does not
        exist (after telling the user, unless silent).
        """
        mixer_name = self.option("Mixer").get()

        if not au.rig.matrix_mixer.MatrixMixer.is_mixer(mixer_name):
            if not silent:
                qtility.request.message(
                    title="No Face Mixer",
                    message="You must build the rig before editing the face poses",
                )
            return None

        return au.rig.matrix_mixer.MatrixMixer(node=mixer_name, namer=self._mixer_namer())

    def driven_list(self, mixer) -> list:
        """
        Returns the Driven Objects option updated to match the mixer, for the
        pose editor to store: the face's own controls (keyed by bone label)
        are left out, as they are always driven. Entries the mixer drives
        keep their place (as do entries which did not build, so nothing is
        lost), and newly driven objects are added at the end.
        """
        built_in = {bone_label(bone) for bone in FACE_BONES}
        driven_keys = mixer.driven_keys()
        current = list(self.option("Driven Objects").get() or list())

        kept = [
            entry
            for entry in current
            if entry in driven_keys or not mref.objExists(self._resolve(entry) or "")
        ]
        added = [
            key
            for key in driven_keys
            if key not in current and key not in built_in
        ]
        return kept + added

    def open_pose_editor(self):
        """
        Opens the Matrix Mixer Pose Editor on this component's mixer
        """
        mixer = self.mixer()
        if mixer:
            toolkits.run("Matrix Mixer Pose Editor", options={"Mixer Node": mixer.node.name()})


class HighLevelControlRig(rigging.facial.FacialControlRig):
    """
    The animator facing controls which drive the pose weights of the mixer.
    Each is placed at its guide, prefixed with the component's
    control_prefix, and every animator facing attribute is proxied onto the
    attribute host. The sneer fixup multiplies (rather than averages) the
    sneers.
    """

    def __init__(self, component, attribute_host):
        """
        Args:
            component: The face component, whose guide inputs place the controls
            attribute_host: The node to proxy the animator facing attributes onto
        """
        super().__init__(
            config=component.config,
            # -- There are no per control overrides (an existing control,
            # -- parent or shape), so every control is built
            read_setting=lambda name: None,
            attribute_host=attribute_host,
            description_prefix=f"{component.control_prefix}_",
            multiply_sneers=True,
        )
        self.component = component

    def create(self, mixer, parent, jaw, eye_controls: dict):
        """
        Builds all the high level controls.

        Args:
            mixer: The face's MatrixMixer, whose pose weights are driven
            parent: The node the controls are built under
            jaw: The jaw control, used to blend the lip corner push in
            eye_controls: The eye control of each side, which are given the
                blink attribute
        """
        # -- To allow a pose to be driven by multiple inputs a plus node is
        # -- put in front of each pose weight
        addition_nodes = self.initialise_driving_adds(
            {pose_name: mixer.node.attr(pose_name) for pose_name in self.component.pose_list},
        )

        def guide(control_label):
            return self.component.input(f"{control_label}_guide").get()

        # -- Note: the order of these calls decides the array indices on the
        # -- plusMinusAverage nodes

        # -- Outer Lip Pullers
        self.attribute_host.add_separator_attribute()

        for side in ["left", "right"]:
            self.setup_lip_puller(
                location=side,
                guide=guide(f"{side}_lip_corner"),
                parent=parent,
                connection_map=addition_nodes,
                jaw=jaw,
            )

        # -- Top and Bottom Central Lips
        self.attribute_host.add_separator_attribute()

        for section in ["upper", "lower"]:
            self.setup_central_lip(
                section=section,
                guide=guide(f"{section}_lip"),
                parent=parent,
                connection_map=addition_nodes,
            )

        # -- Nose
        self.attribute_host.add_separator_attribute()

        self.setup_nose(
            guide=guide("nose"),
            parent=parent,
            connection_map=addition_nodes,
        )

        # -- Inner & Outer Brows and the eyes
        for side in ["left", "right"]:
            self.attribute_host.add_separator_attribute()

            self.setup_inner_brow(
                location=side,
                guide=guide(f"{side}_brow_inner"),
                parent=parent,
                connection_map=addition_nodes,
            )
            self.setup_outer_brow(
                location=side,
                guide=guide(f"{side}_brow_outer"),
                parent=parent,
                connection_map=addition_nodes,
            )
            self.setup_eye(
                location=side,
                control=eye_controls[side],
                connection_map=addition_nodes,
            )
