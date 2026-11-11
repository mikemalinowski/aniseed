"""
Provides the "Limb : Shoulder" component, an fk shoulder (a single bone,
driven only by its control) with an automated scapula, which stays upright
with the spine, follows the shoulder turning forward and is progressively
held as the shoulder turns back, dialled by the
scapulaAuto attribute on the Shoulder control (see
aniseed_cartoon.rigging.shoulder).
"""
import os
import mref
import typing
import logging
import collections
import aniseed
import aniseed_utilities as au
from maya import cmds
from aniseed_cartoon.rigging import shoulder

log = logging.getLogger(__name__)


# -- The joint inputs
_JOINTS = ["Shoulder Joint", "Scapula Joint"]


class ShoulderComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    """
    Builds a Shoulder control which drives the shoulder joint (with nothing
    automated), and a Scapula control which drives the scapula joint.

    The scapula only turns about the vertical axis, so it stays upright with
    the spine as the shoulder rotates up and down, and rises and falls
    without swinging out sideways. Turning forward it follows the shoulder
    like a child. Turning back it follows the shoulder progressively less,
    easing to a stop at the Retract Limit toward the spine, and turns out
    about its own -y by up to the Retract Turn. The scapulaAuto attribute on the Shoulder control (proxied
    onto the Scapula control) blends from a plain child of the shoulder (0)
    to this (1).

    The Shoulder output is the default, for an arm to hang from.
    """

    identifier = "Limb : Shoulder"
    icon = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "flexi_two_bone_ik",
        "flexi_two_bone_ik.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent and joint inputs, the naming and behaviour
        options and an output per control.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Shoulder Joint",
            description="The shoulder joint",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Scapula Joint",
            description="The scapula joint, which is automated by the shoulder's rotation",
            validate=True,
            group="Required Joints",
        )

        self.declare_option(
            name="Descriptive Prefix",
            description="Prefix used when naming the joints, controls and mechanical nodes",
            value="Shoulder",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            description="Location token (e.g. md/lf/rt) applied to generated node names",
            value=self.config.left,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Retract Limit",
            description=(
                "The furthest the scapula moves toward the spine as the shoulder turns back. It eases "
                "into this. If zero, it is 0.25 of the distance between the shoulder and scapula."
            ),
            value=0.0,
            group="Behaviour",
        )

        self.declare_option(
            name="Retract Turn",
            description=(
                "How far (in degrees) the scapula turns out about its own -y as the shoulder turns back, "
                "building steadily to this at the Retract Limit"
            ),
            value=20.0,
            group="Behaviour",
        )

        self.declare_option(
            name="Shape Scale",
            description=(
                "The scale of the control shapes. If zero, it is worked out from the distance between "
                "the shoulder and scapula."
            ),
            value=0.0,
            group="Behaviour",
        )

        # -- Only used to create the joints when entering the stack
        self.declare_option(name="Create Joints", value=True, pre_expose=True)

        self.declare_output(
            name="Shoulder",
            description="The Shoulder control, which drives the shoulder joint, for an arm to hang from",
            is_default=True,
        )
        self.declare_output("Scapula")

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output, and
        creates the joints if the Create Joints option is set.
        """
        create_joints = self.option("Create Joints")
        create_joints.set_hidden(True)

        self.input("Parent").hook_to_parent()

        if create_joints.get():
            self._create_joints(parent=au.core.selection.first_selected())

    def option_widget(self, option_name: str):
        """
        This allows us to provide dedicate widgets for specific options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config, self.option(option_name).get())

    def input_widget(self, requirement_name):
        """
        This allows us to provide dedicate widgets for specific inputs
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def _create_joints(self, parent):
        """
        Creates a shoulder joint, and a scapula joint under it (set back and
        down from the shoulder), under the given
        parent (or the world if there is none) at the parent's position, and
        sets the joint inputs to them
        """
        location = self.option("Location").get()
        prefix = self.option("Descriptive Prefix").get()

        joint_data = collections.OrderedDict()
        joint_data[""] = {}

        joints = au.scene.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=location,
            config=self.config,
            parent=None,
            prefix=prefix,
        )

        scapula = au.scene.joints.create(
            description=f"{prefix}Scapula",
            location=location,
            parent=joints[0],
            config=self.config,
        )
        mref.get(scapula).attr("translate").set(4, -6, -8)

        # -- As with the flexi limbs, the joints are built in world space and
        # -- then placed under, and at the position of, the parent
        if parent:
            root_joint = mref.get(joints[0])
            root_joint.set_parent(parent)
            root_joint.set_position(mref.get(parent).get_position(space="world"), space="world")

        self.input("Shoulder Joint").set(joints[0])
        self.input("Scapula Joint").set(mref.get(scapula).name())
        cmds.select(clear=True)

    def is_valid(self) -> bool:
        """
        Checks the shoulder and scapula joints exist and are different
        joints
        """
        for input_name in _JOINTS:
            joint = self.input(input_name).get()
            if not joint or not mref.objExists(joint):
                log.warning(f"{self.label()}: The {input_name} must be set to an existing joint")
                return False

        shoulder_joint, scapula_joint = [mref.get(self.input(name).get()).full_name() for name in _JOINTS]
        if shoulder_joint == scapula_joint:
            log.warning(f"{self.label()}: The Shoulder Joint and Scapula Joint must be different joints")
            return False

        return True

    def run(self) -> bool:
        """
        Builds the shoulder and sets the outputs to its controls.
        """
        built = shoulder.Shoulder(
            shoulder_joint=self.input("Shoulder Joint").get(),
            scapula_joint=self.input("Scapula Joint").get(),
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=self.input("Parent").get(),
            retract_limit=self.option("Retract Limit").get() or None,
            retract_turn=self.option("Retract Turn").get(),
            shape_scale=self.option("Shape Scale").get() or None,
        ).build()

        self.output("Shoulder").set(built.shoulder_control.ctl)
        self.output("Scapula").set(built.scapula_control.ctl)
        return True

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the shoulder and scapula joints. Empty if either is missing.
        """
        joints = [self.input(name).get() for name in _JOINTS]
        if not all(joint and mref.objExists(joint) for joint in joints):
            return []
        return joints

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the shoulder joint. Empty if there is no
        shoulder joint or it has no parent.
        """
        shoulder_joint = self.input("Shoulder Joint").get()
        if not shoulder_joint or not mref.objExists(shoulder_joint):
            return ""

        parent = mref.get(shoulder_joint).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's joints if they already exist (the search and
        replaced names), otherwise copies the original's into the mirrored
        hierarchy for this component to drive. Either way no joints are
        created on entering the stack, as this component already has them.
        """
        self.option("Create Joints").set(False)

        original_items = mirrored_from.mirror_mixin_items_to_mirror()
        if not original_items:
            return

        if self.mirror_mixin_counterparts_exist(original_items, self.mirror_mixin_items_to_mirror()):
            return

        copies = self.mirror_mixin_copy_nodes(original_items)
        for input_name, copy_ in zip(_JOINTS, copies):
            self.input(input_name).set(copy_)

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        Restores the Create Joints option so this component's data matches
        the original
        """
        self.option("Create Joints").set(mirrored_from.option("Create Joints").get(resolved=False))
