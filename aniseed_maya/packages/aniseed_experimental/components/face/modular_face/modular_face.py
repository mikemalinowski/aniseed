"""
Provides the "Limb : Modular Face" component. Rather than building the face
itself (as "Limb : Face" does), it adds the components which do as its
children when it enters the stack, and fills in all of their details:

    Limb : Mouth                  (jaw, upper and lower lip)
    Limb : Eyes                   (eyes, lids and pupils)
    Stack : Organiser             (grouping the Singulars)
        Basic : Singular          (one per other bone in skeleton.json)
    Utility : Matrix Mixer        (driving every bone's control, starting
                                   from the poses in default_pose_data.json)
    Face : High Level Controls    (the animator facing controls driving the
                                   mixer's poses)
    Face : Lip Smoothing          (the lips following the jaw)
    Utility : Drive Shape Visibility (the direct controls, and the teeth and
                                   tongue controls)

The mixer drives each control through its offsetParentMatrix, so it works
on top of whatever drives the control's offset. The default poses are those
of "Limb : Face", keyed by bone label (such as brow_inner_left), and are
re-keyed to the control addresses the mixer drives when it is added.

From then on everything is held by the children: add more Singulars, add
them to the mixer and add poses with the Matrix Mixer Pose Editor. The
face itself only builds the face org, which the children are built under.
"""
import os
import json
import logging

from maya import cmds

import mref
import aniseed
import aniseed_utilities as au

from aniseed_experimental.rigging import lip_smoothing

log = logging.getLogger(__name__)

_DIRECTORY = os.path.dirname(__file__)

with open(os.path.join(_DIRECTORY, "skeleton.json"), "r") as _f:
    # -- Each bone: name, location (left/right/middle), parent (a bone label,
    # -- or head_middle for the selection), matrix, and is_always_on for a
    # -- bone whose control is always shown
    FACE_BONES = json.load(_f)

_DEFAULT_POSE_DATA_PATH = os.path.join(_DIRECTORY, "default_pose_data.json")

# -- The bones driven by the mouth and eyes components: the joint input each
# -- is given to and the output holding its control
_MOUTH_BONES = {
    "jaw_middle": ("Jaw Joint", "Jaw Control"),
    "upper_lip_middle": ("Upper Lip Joint", "Upper Lip Control"),
    "lower_lip_middle": ("Lower Lip Joint", "Lower Lip Control"),
}

_EYE_BONES = {
    f"{part}_{side}": (f"{side.title()} {label} Joint", f"{side.title()} {label} Control")
    for side in ["left", "right"]
    for part, label in [
        ("eye", "Eye"),
        ("eye_upper_lid", "Upper Eye Lid"),
        ("eye_lower_lid", "Lower Eye Lid"),
        ("eye_pupil", "Pupil"),
    ]
}

# -- The guide of each high level control group: (description, location
# -- attribute on the config, the bone labels it sits at - midway between
# -- them if there are several). It takes its orientation from the first.
_GUIDE_BONES = {
    "left_lip_corner": ("FacialLipCorner", "left", ["upper_lip_outer_left", "lower_lip_outer_left"]),
    "right_lip_corner": ("FacialLipCorner", "right", ["upper_lip_outer_right", "lower_lip_outer_right"]),
    "upper_lip": ("FacialUpperLip", "middle", ["upper_lip_middle"]),
    "lower_lip": ("FacialLowerLip", "middle", ["lower_lip_middle"]),
    "nose": ("FacialNose", "middle", ["nose_middle"]),
    "left_brow_inner": ("FacialBrowInner", "left", ["brow_inner_left"]),
    "left_brow_outer": ("FacialBrowOuter", "left", ["brow_outer_left"]),
    "right_brow_inner": ("FacialBrowInner", "right", ["brow_inner_right"]),
    "right_brow_outer": ("FacialBrowOuter", "right", ["brow_outer_right"]),
}

# -- The options the eyes are created with, as "Limb : Face" sets them
_EYE_OPTIONS = {
    "Aim Distance": 30.0,
    "Max Blink Rotation": 65,
    "Add Blink": False,
    "Add Pupil": True,
}

# -- Bones whose controls are shown by the jaw's show_teeth_and_tongue
# -- attribute rather than the direct control visibility
_TEETH_AND_TONGUE = ("teeth", "tongue")


def bone_label(bone: dict) -> str:
    """
    Returns the label of a bone: its name and location (brow_inner_left)
    """
    return f"{bone['name']}_{bone['location']}"


class ModularFace(aniseed.RigComponent):
    """
    Creates the face joints and adds the mouth, eyes, singular, mixer, high
    level control, lip smoothing and visibility components beneath itself,
    wired together. It builds only the face org they are built under.
    """

    identifier = "Limb : Modular Face"
    icon = os.path.join(os.path.dirname(__file__), "modular_face.png")

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent and Attribute Host inputs and the Face Org and
        Attribute Host outputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The node the face org is parented under (typically the head control)",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Attribute Host",
            description="The node the animator facing attributes are put on. If not given, the face org is used.",
            validate=False,
            group="Control Rig",
        )

        self.declare_output(
            name="Face Org",
            description="The org the face components are built under",
            is_default=True,
        )

        self.declare_output(
            name="Attribute Host",
            description="The node the animator facing attributes are put on",
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for every input.
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def on_enter_stack(self):
        """
        Creates the face joints under the selection (or at the world origin),
        hooks the Parent input to the parent component, and adds the face
        components as children.
        """
        joints = self._create_joints()
        self.input("Parent").hook_to_parent()
        self._create_components(joints)

    def run(self) -> bool:
        """
        Creates the face org and sets the outputs.
        """
        org = au.scene.transforms.create(
            classification=self.config.organisational,
            description="face",
            location=self.config.middle,
            config=self.config,
            parent=self.input("Parent").get(),
        )

        self.output("Face Org").set(org)
        self.output("Attribute Host").set(self.input("Attribute Host").get() or org)
        return True

    def _create_joints(self) -> dict:
        """
        Creates a joint per bone, under its parent bone's joint (or the
        selection, for a bone under head_middle), set to its matrix.

        Returns:
            The joint name for each bone label
        """
        selected = mref.selected()
        root = selected[0] if selected else None

        sides = {
            "left": self.config.left,
            "right": self.config.right,
            "middle": self.config.middle,
        }

        joints = dict()
        for bone in FACE_BONES:
            parent = joints.get(bone["parent"]) or (root.name() if root else None)

            joint = mref.get(
                au.scene.joints.create(
                    description=bone["name"],
                    location=sides[bone["location"]],
                    parent=parent,
                    config=self.config,
                )
            )
            joint.set_matrix(bone["matrix"])
            joints[bone_label(bone)] = joint.name()

        return joints

    def _create_components(self, joints: dict):
        """
        Adds every face component beneath this one, in build order, wiring
        each to the outputs of those it depends on.

        Args:
            joints: The joint name for each bone label
        """
        sides = {
            "left": self.config.left,
            "right": self.config.right,
            "middle": self.config.middle,
        }
        face_org = self.output("Face Org").address()
        attribute_host = self.output("Attribute Host").address()

        # -- The address of the control of each bone, as it is added
        controls = dict()

        mouth = self._add_child(
            "Limb : Mouth",
            "Mouth",
            inputs=dict(
                {joint_input: joints[label] for label, (joint_input, _) in _MOUTH_BONES.items()},
                Parent=face_org,
            ),
        )
        for label, (_, output_name) in _MOUTH_BONES.items():
            controls[label] = mouth.output(output_name).address()

        # -- The Singulars are grouped under an organiser. It comes before the
        # -- eyes, which sit under one of the Singulars' controls.
        singular_group = self._add_child("Stack : Organiser", "Singulars")

        singulars = dict()
        eyes = None

        for bone in FACE_BONES:
            label = bone_label(bone)

            if label in _MOUTH_BONES:
                continue

            if label in _EYE_BONES:
                # -- The eyes sit under the upper head, which comes first
                if not eyes:
                    eyes = self._add_child(
                        "Limb : Eyes",
                        "Eyes",
                        inputs=dict(
                            {joint_input: joints[eye_label] for eye_label, (joint_input, _) in _EYE_BONES.items()},
                            Parent=controls[bone["parent"]],
                        ),
                        options=_EYE_OPTIONS,
                    )
                    for eye_label, (_, output_name) in _EYE_BONES.items():
                        controls[eye_label] = eyes.output(output_name).address()
                continue

            singular = self._add_child(
                "Basic : Singular",
                f"{bone['name'].replace('_', ' ').title()} {bone['location'].title()}",
                inputs=dict(
                    Parent=self._singular_parent(label, bone, controls, face_org),
                    Joint=joints[label],
                ),
                options={
                    "Description": bone["name"],
                    "Location": sides[bone["location"]],
                    "Create Joint": False,
                },
                parent=singular_group,
            )
            singulars[label] = singular
            controls[label] = singular.output("Control").address()

        mixer = self.rig.component_library.request("Utility : Matrix Mixer").add_to(
            component=self,
            label=f"{self.label()} Mixer",
            parent=face_org,
            driven=[controls[bone_label(bone)] for bone in FACE_BONES],
            prefix="Face",
            location=self.config.middle,
        )
        mixer.option("Data").set(self._default_pose_data(controls))

        self._add_child(
            "Face : High Level Controls",
            "High Level Controls",
            inputs=dict(
                {
                    f"{group}_guide": guide
                    for group, guide in self._create_guides(joints).items()
                },
                **{
                    "Parent": face_org,
                    "Attribute Host": attribute_host,
                    "Mixer": mixer.output("Mixer").address(),
                    "Jaw Control": controls["jaw_middle"],
                    "Left Eye Control": controls["eye_left"],
                    "Right Eye Control": controls["eye_right"],
                },
            ),
        )

        smoothing_inputs = {
            "Jaw Control": controls["jaw_middle"],
            "Upper Lip Control": controls["upper_lip_middle"],
            "Lower Lip Control": controls["lower_lip_middle"],
            "Space": face_org,
            "Attribute Host": attribute_host,
        }
        for label, *_ in lip_smoothing.SMOOTHING:
            for side in lip_smoothing.SIDES:
                smoothing_inputs[lip_smoothing.lip_input_name(label, side)] = controls[f"{label}_{side}"]

        self._add_child("Face : Lip Smoothing", "Lip Smoothing", inputs=smoothing_inputs)

        bones = {bone_label(bone): bone for bone in FACE_BONES}

        self._add_child(
            "Utility : Drive Shape Visibility",
            "Direct Control Visibility",
            inputs={
                "Attribute Host": attribute_host,
                "Transforms": [
                    controls[label]
                    for label in singulars
                    if not bones[label].get("is_always_on")
                ],
            },
            options={"Attribute Name": "direct_control_visibility"},
        )

        self._add_child(
            "Utility : Drive Shape Visibility",
            "Teeth And Tongue Visibility",
            inputs={
                "Attribute Host": controls["jaw_middle"],
                "Transforms": [
                    controls[label]
                    for label in singulars
                    if label.startswith(_TEETH_AND_TONGUE)
                ],
            },
            options={"Attribute Name": "show_teeth_and_tongue"},
        )

    def _create_guides(self, joints: dict) -> dict:
        """
        Creates a locator for each high level control to be placed at, in a
        single FaceGuides group under the world. Each sits at (and is
        oriented to) the bone it represents; a lip corner sits midway between
        the outer upper and lower lip bones of its side. They can be moved
        afterwards to place the controls.

        Args:
            joints: The joint name for each bone label

        Returns:
            The locator for each high level control group
        """
        group = au.scene.transforms.create(
            classification=self.config.organisational,
            description="FaceGuides",
            location=self.config.middle,
            config=self.config,
            parent=None,
        )

        guides = dict()
        for control_group, (description, side, labels) in _GUIDE_BONES.items():
            name = self.config.generate_name(
                classification="guide",
                description=description,
                location=getattr(self.config, side),
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

            guides[control_group] = cmds.ls(locator, long=True)[0]

        cmds.select(clear=True)
        return guides

    @staticmethod
    def _singular_parent(label: str, bone: dict, controls: dict, face_org: str) -> str:
        """
        Returns the address a bone's Singular is parented under: the mouth's
        upper or lower lip control for a lip bone (so the lips move with
        them), otherwise its parent bone's control, or the face org for a
        bone directly under the head.
        """
        for section in ["upper", "lower"]:
            if label.startswith(f"{section}_lip_"):
                return controls[f"{section}_lip_middle"]

        return controls.get(bone["parent"], face_org)

    def _add_child(self, component_type: str, label: str, inputs: dict = None, options: dict = None, parent=None):
        """
        Adds a component of the given type beneath this one (or beneath the
        given parent component), labelled with this component's label then
        the given label. Its on_enter_stack is not run, as everything it
        needs (such as its joints) is given.
        """
        component = self.stack.add_component(
            component_type=component_type,
            label=f"{self.label()} {label}",
            inputs=inputs,
            options=options,
            parent=parent or self,
            suppress_events=True,
        )
        if not component:
            raise RuntimeError(f"{self.label()} : Could not add a {component_type} component")
        return component

    @staticmethod
    def _default_pose_data(controls: dict) -> dict:
        """
        Returns the poses the mixer starts with: those of "Limb : Face",
        re-keyed from bone labels to the control addresses the mixer drives.

        Args:
            controls: The control address of each bone label
        """
        with open(_DEFAULT_POSE_DATA_PATH, "r") as f:
            data = json.load(f)

        return {
            "version": data.get("version", 1),
            "driven": [controls[label] for label in data.get("driven", []) if label in controls],
            "poses": [
                {
                    "name": pose["name"],
                    "matrices": {
                        controls[label]: matrix
                        for label, matrix in pose.get("matrices", dict()).items()
                        if label in controls
                    },
                }
                for pose in data.get("poses", [])
            ],
        }
