"""
Provides the "Limb : FK Spine" component, which builds a sequential chain of
fk controls from the hip joint to the chest joint, plus a hip sway control that
drives the hip without affecting the controls above it. It can generate a
spine joint chain of a requested length when added to the stack.
"""
import os
import logging
import mref
import typing
import aniseed
import qtility
import aniseed_toolkit
from aniseed_maya_standard.mixins import MirrorMixin

log = logging.getLogger(__name__)


class FKSpineComponent(aniseed.RigComponent, MirrorMixin):
    """
    This component will create a rig where all controls are sequential except the
    hip sway which can be manipulated without adjusting the children.
    """

    identifier = "Limb : FK Spine"
    icon = os.path.join(
        os.path.dirname(__file__),
        "spine.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, hip and chest inputs, the label, location, world
        alignment and joint count options, and the hip and chest control
        outputs.
        """
        super().__init__(*args, **kwargs)

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
            value=self.config.middle,
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Align Controls To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Joint Count",
            value=4,
            hidden=False,
            pre_expose=True,
        )

        self.declare_output(name="Hip")
        self.declare_output(name="Chest")

    def on_enter_stack(self):
        """
        Hides the Joint Count option and, if it is non-zero, creates that many
        spine joints under the current selection. Then attempts to hook the
        parent input to the parent component.
        """
        # -- Now that we have used the joint count option we dont want
        # -- the user to see it again so we hide it.
        self.option("Joint Count").set_hidden(True)

        # -- Providing the number of joints was not zero then we build
        # -- the joints
        joint_count = self.option("Joint Count").get()
        if joint_count:
            self.user_func_create_skeleton(joint_count=joint_count)

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def option_widget(self, option_name: str):
        """
        Returns a location selector for the Location option.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the hip, chest and parent inputs.
        """
        if requirement_name in ["Hip", "Chest", "Parent"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Always exposes a "Create Joints" menu entry. The base class menu
        entries are not included.
        """
        return {
            "Create Joints": self.user_func_create_skeleton,
        }

    def is_valid(self):
        """
        Checks that the hip and chest joints exist and that the chain between
        them faces along positive X. The summed joint translations may stray
        up to 20 scene units off the X axis.
        """

        hip = self.input("Hip").get()
        chest = self.input("Chest").get()

        if not hip or not chest:
            log.warning(f"{self.label()} : Hip and Chest must both be set")
            return False

        if not mref.objExists(hip):
            log.warning(f"{hip} does not exist")
            return False

        if not mref.objExists(chest):
            log.warning(f"{chest} does not exist")
            return False

        facing_dir = aniseed_toolkit.scene.joints.get_chain_facing_direction(
            start=hip,
            end=chest,
            epsilon=20,
        )

        if facing_dir != facing_dir.PositiveX:
            log.warning("The spine joints are expected to point along positive x")
            return False

        return True

    def run(self):
        """
        Builds a hip control, a hip sway control (a child of the hip which
        drives the hip joint but has no children), a chain of spine controls
        for the joints between the hip and chest and finally a chest control.
        The joints are read from the dag path of the chest, so the chest must
        be a descendant of the hip.
        """

        hip_bone = self.input("Hip").get()
        chest_bone = self.input("Chest").get()

        # -- Get all the joints that make up part of the continuous hierarchy
        # -- by reading the dag path of the chest from the hip downward
        chain = mref.get(chest_bone).full_name().split("|")
        joints = chain[chain.index(hip_bone):]

        hip_control = self._create_control(
            label="Hip",
            parent=self.input("Parent").get(),
            match_to=hip_bone,
            shape_scale=24,
        )

        # -- Store the output
        self.output("Hip").set(hip_control.ctl)

        # -- The hip sway is a child of the hip, but nothing else is a child
        # -- of the sway, so it can be manipulated independently
        sway_control = self._create_control(
            label="HipSway",
            parent=hip_control.ctl,
            match_to=hip_bone,
            shape_scale=20,
        )

        aniseed_toolkit.scene.constraints.parent_and_scale(
            sway_control.ctl,
            hip_bone,
        )

        control_parent = hip_control.ctl

        for joint in joints[1:-1]:

            spine_control = self._create_control(
                label="Spine",
                parent=control_parent,
                match_to=joint,
                shape_scale=16,
            )

            aniseed_toolkit.scene.constraints.parent_and_scale(
                spine_control.ctl,
                joint,
            )

            control_parent = spine_control.ctl

        chest_control = self._create_control(
            label="Chest",
            parent=control_parent,
            match_to=chest_bone,
            shape_scale=24,
        )

        # -- Store the chest output
        self.output("Chest").set(chest_control.ctl)

        aniseed_toolkit.scene.constraints.parent_and_scale(
            chest_control.ctl,
            chest_bone,
        )

        return True

    def _create_control(self, label, parent, match_to, shape_scale):
        """
        Creates a spine control, aligning it to the world if the option
        to do so is enabled.
        """
        control = aniseed_toolkit.rig.control.create(
            description=label + self.option("Label").get(),
            location=self.option("Location").get(),
            shape_scale=shape_scale,
            parent=parent,
            match_to=match_to,
            config=self.config,
            shape="core_rounded_square",
            rotate_shape=[90, 90, 0],
        )

        if self.option("Align Controls To World").get():
            mref.get(control.org).set_rotation([0, 0, 0], space="world")
            aniseed_toolkit.scene.shapes.rotate(control.ctl, x=0, y=0, z=90)

        return control

    def user_func_create_skeleton(self, joint_count=None):
        """
        Creates a hip to chest joint chain under the first selected node, with
        the hip placed at a fixed world position and the joints evenly spaced
        along X. The hip and chest inputs are set and the hip is selected.

        Args:
            joint_count: The number of joints including the hip and chest. If
                not given the user is prompted for it.
        """

        if not joint_count:
            joint_count = qtility.request.text(
                title="Joint Count",
                message="How many joints (including hip and chest) do you want?"
            )

            if not joint_count:
                return

            try:
                joint_count = int(joint_count)
            except ValueError:
                log.warning(f"'{joint_count}' is not a whole number of joints")
                return

        if joint_count < 2:
            log.warning("A spine needs at least two joints (the hip and the chest)")
            return

        parent = aniseed_toolkit.core.selection.first_selected()

        increment = 25 / (joint_count - 1)

        hip_joint = self._create_joint("Hip", parent)
        self.input("Hip").set(hip_joint)

        mref.get(hip_joint).xform(
            rotation=[-90, 0, 90],
            translation=[0, 105, 0],
            worldSpace=True,
        )

        parent = hip_joint

        for _ in range(joint_count - 2):
            spine_joint = self._create_joint("Spine", parent)
            mref.get(spine_joint).translateX.set(increment)
            parent = spine_joint

        chest_joint = self._create_joint("Chest", parent)
        self.input("Chest").set(chest_joint)

        mref.get(chest_joint).translateX.set(increment)
        mref.select(hip_joint)

    def _create_joint(self, label, parent):
        """
        Creates a spine joint as a child of (and matched to) the given parent
        """
        return aniseed_toolkit.scene.joints.create(
            description=label + self.option("Label").get(),
            location=self.option("Location").get(),
            parent=parent,
            match_to=parent,
            config=self.config,
        )

    def _mirror_chain(self) -> list:
        """
        Returns the joints from the hip to the chest, or an empty list if
        either is missing or the chest is not below the hip.
        """
        hip = self.input("Hip").get()
        chest = self.input("Chest").get()

        if not hip or not chest or not mref.objExists(hip) or not mref.objExists(chest):
            return []

        try:
            return aniseed_toolkit.scene.joints.get_between(hip, chest)
        except ValueError:
            return []

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the joints from the hip to the chest.
        """
        return self._mirror_chain()

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the hip, which is where the mirrored component creates its
        joints.
        """
        hip = self.input("Hip").get()
        if not hip or not mref.objExists(hip):
            return ""

        parent = mref.get(hip).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        If the other side joints already exist this component uses them. Otherwise
        it creates a chain of the same length as the original's when it
        enters the stack.
        """
        original_chain = mirrored_from._mirror_chain()

        if self.mirror_mixin_counterparts_exist(original_chain, self._mirror_chain()):
            self.option("Joint Count").set(0)
            return

        self.option("Joint Count").set(len(original_chain) if len(original_chain) >= 2 else 0)

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        The mirror reflects the joints' behaviour, which negates their local
        translations, so the chain would point down negative X (which
        is_valid rejects). Each joint is turned 180 degrees about its own Z
        axis, so the chain points down positive X again.

        Children mirrored by this mirror (such as a child component's
        joints) keep their mirrored transforms. Any other children (for
        instance when this component uses existing joints) keep their place
        relative to their parent joint.
        """
        chain = self._mirror_chain()
        if len(chain) < 2:
            return

        mirrored_nodes = set(self.mirror_mixin_mirrored_nodes().values())

        held = []
        for joint in chain:
            for child in mref.get(joint).children(include_shapes=False):
                if child.name() in mirrored_nodes and child.name() not in chain:
                    held.append(
                        (child, mref.xform(child.full_name(), query=True, matrix=True, worldSpace=True)),
                    )

        # -- Work out every new matrix before changing any, then apply them
        # -- from the hip down. Turning 180 degrees about Z negates the X
        # -- and Y axes, which are the first two rows of the world matrix.
        matrices = []
        for joint in chain:
            matrix = mref.xform(joint, query=True, matrix=True, worldSpace=True)
            for index in range(8):
                if index % 4 != 3:
                    matrix[index] *= -1
            matrices.append(matrix)

        for joint, matrix in zip(chain, matrices):
            mref.xform(joint, matrix=matrix, worldSpace=True)

        for child, matrix in held:
            mref.xform(child.full_name(), matrix=matrix, worldSpace=True)
