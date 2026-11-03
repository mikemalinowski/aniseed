"""
Provides the "Limb : Flexi Two Bone IK" component, which builds a two bone ik
with an fk style control riding on each bone (see
aniseed_cartoon.rigging.flexi_two_bone_ik), with optional soft ik and bendy
twists on the upper and lower bones.
"""
import os
import mref
import typing
import logging
import collections
import aniseed
import functools
import aniseed_utilities as au
from aniseed_cartoon.rigging import bendy_twists
from aniseed_cartoon.rigging import flexi_two_bone_ik

log = logging.getLogger(__name__)


# -- The twist joint inputs, with the label of the bone each set runs along
_TWISTS = [
    ("Upper Twist Joints", "Upper"),
    ("Lower Twist Joints", "Lower"),
]


class FlexiTwoBoneIkComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    """
    Builds a flexi two bone ik on a three joint chain (such as an arm or a
    leg). The limb is posed with the IK Target and Upvector controls, and
    the Top, Mid and Bottom FK controls riding on the chain push the elbow
    and wrist around on top of that solve.

    Twist joints given to the "Upper Twist Joints" and "Lower Twist Joints"
    inputs are driven by bendy twists, with a bendy control at each point of
    the curve. They can be created from the right click menu.
    """

    identifier = "Limb : Flexi Two Bone IK"
    icon = os.path.join(
        os.path.dirname(__file__),
        "flexi_two_bone_ik.png",
    )

    # -- Version 2 removed the twist count options, as the counts come from
    # -- the twist joint inputs. They have since returned as hidden options
    # -- which are only used to create the joints when entering the stack.
    version = 2

    @classmethod
    def migrate(cls, data: dict, from_version: int) -> dict:
        """
        Drops the Upper and Lower Twist Count options saved by version 1.
        """
        if from_version < 2:
            options = data.get("options") or dict()
            for option_name in ["Upper Twist Count", "Lower Twist Count"]:
                options.pop(option_name, None)
        return data

    # noinspection PyUnresolvedReferences
    def __init__(self, *args, **kwargs):
        """
        Declares the parent, root/tip joint and twist joint inputs, the naming
        and behaviour options and an output per control.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Root Joint",
            description="The first joint of the three joint chain (such as the upper arm)",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Tip Joint",
            description="The last joint of the three joint chain (such as the wrist)",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Upper Twist Joints",
            description="Joints between the root and middle joints, driven by a bendy twist setup",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_input(
            name="Lower Twist Joints",
            description="Joints between the middle and tip joints, driven by a bendy twist setup",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_input(
            name="IK Target Guide",
            description="Optional transform to place the IK Target control at. The ik still solves to the tip joint.",
            validate=False,
            group="Optional Nodes",
        )

        self.declare_option(
            name="Descriptive Prefix",
            description="Prefix used when naming the controls and mechanical nodes",
            value="",
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
            name="Apply Soft Ik",
            description=(
                "If enabled, soft ik (with stretch) is applied to the two bone ik, "
                "with its attributes on the IK Target control"
            ),
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="World Space IK Controls",
            description=(
                "If enabled, the IK Root, IK Target and Upvector controls are aligned "
                "to the world. Otherwise the IK Root matches the root joint, the IK "
                "Target matches the tip joint and the Upvector is aligned to the plane "
                "of the chain."
            ),
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Shape Scale",
            description="The scale of the control shapes. If zero, it is worked out from the length of the chain.",
            value=0.0,
            group="Behaviour",
        )

        # -- Declare our options which make it easier and quicker to generate
        # -- the joints if needed
        self.declare_option(name="Create Joints", value=True, pre_expose=True)
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)

        self.declare_output("IK Root")
        self.declare_output("IK Target")
        self.declare_output("Upvector")
        self.declare_output("Top FK")
        self.declare_output("Mid FK")
        self.declare_output(
            name="Bottom FK",
            description="The control the tip joint follows",
            is_default=True,
        )

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output, and
        creates the joints if the Create Joints option is set.
        """
        create_joints = self.option("Create Joints")
        upper_twist_count = self.option("Upper Twist Count")
        lower_twist_count = self.option("Lower Twist Count")

        # -- These options are only used when entering the stack, so we
        # -- hide them regardless of whether we create the joints
        for option in [create_joints, upper_twist_count, lower_twist_count]:
            option.set_hidden(True)

        self.input("Parent").hook_to_parent()

        if create_joints.get():
            self._create_joints(
                parent=au.core.selection.first_selected(),
                upper_twist_count=upper_twist_count.get(),
                lower_twist_count=lower_twist_count.get(),
            )

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
        if requirement_name in ["Parent", "Root Joint", "Tip Joint", "IK Target Guide"]:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name in ["Upper Twist Joints", "Lower Twist Joints"]:
            return aniseed.widgets.ObjectList()

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Offers to create the twist joints for whichever twist input is empty.
        Mirroring is offered by au.mixins.MirrorMixin.
        """
        menu = super().user_functions()

        if self._chain() and any(not self.input(input_name).get() for input_name, _ in _TWISTS):
            menu["Create Twist Joints"] = functools.partial(self.user_func_create_twist_joints)

        return menu

    def user_func_create_twist_joints(self, upper_twist_count: int = None, lower_twist_count: int = None):
        """
        Creates the twist joints for each twist input which is empty, and sets
        the input to them. Any count which is not given is asked for.
        """
        chain = self._chain()
        if not chain:
            log.warning(f"{self.label()}: Set the Root Joint and Tip Joint before creating twist joints")
            return

        counts = [upper_twist_count, lower_twist_count]

        for (input_name, label), (start, end), count in zip(_TWISTS, [chain[0:2], chain[1:3]], counts):
            if self.input(input_name).get():
                continue

            count = aniseed.dialogs.request_count(
                count,
                title=f"{label} Twist Count",
                message=f"How many twist joints do you want on the {label.lower()} bone?",
            )
            if count is None:
                return

            if count < 1:
                continue

            self.input(input_name).set(
                bendy_twists.create_twist_joints(
                    start_joint=start,
                    end_joint=end,
                    count=count,
                    config=self.config,
                    prefix=f"{self.option('Descriptive Prefix').get()}{label}",
                    location=self.option("Location").get(),
                ),
            )

    def _create_joints(self, parent, upper_twist_count: int, lower_twist_count: int):
        """
        Creates a three joint chain under the given parent (or the world if
        there is none), sets the Root Joint and Tip Joint inputs to it and
        creates the twist joints.
        """
        joint_data = collections.OrderedDict()
        joint_data["Upper"] = {}
        joint_data["Lower"] = {"tx": 24, "jointOrientY": -20}
        joint_data["Tip"] = {"tx": 24}

        joints = au.scene.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=self.option("Location").get(),
            config=self.config,
            parent=parent,
            prefix=self.option("Descriptive Prefix").get(),
        )

        self.input("Root Joint").set(joints[0])
        self.input("Tip Joint").set(joints[-1])

        self.user_func_create_twist_joints(
            upper_twist_count=upper_twist_count,
            lower_twist_count=lower_twist_count,
        )

    def is_valid(self) -> bool:
        """
        Checks the root and tip joints give a chain of exactly three joints,
        that every twist joint exists and that the ik target guide exists if
        it is given.
        """
        root_joint = self.input("Root Joint").get()
        tip_joint = self.input("Tip Joint").get()
        ik_target_guide = self.input("IK Target Guide").get()

        if ik_target_guide and not mref.objExists(ik_target_guide):
            log.warning(f"{self.label()}: The IK Target Guide ({ik_target_guide}) does not exist")
            return False

        for input_name, joint in [("Root Joint", root_joint), ("Tip Joint", tip_joint)]:
            if not joint or not mref.objExists(joint):
                log.warning(f"{self.label()}: The {input_name} input is not set to an existing joint")
                return False

        try:
            joints = au.scene.joints.get_between(start=root_joint, end=tip_joint)
        except ValueError:
            log.warning(f"{self.label()}: The Tip Joint ({tip_joint}) is not below the Root Joint ({root_joint})")
            return False

        if len(joints) != 3:
            log.warning(f"{self.label()}: Expected three joints from the Root Joint to the Tip Joint, got {joints}")
            return False

        # -- The chain joints are driven by the ik, and each twist joint by a
        # -- single bendy twist, so no joint may be used twice
        used = {mref.get(joint).full_name(): "Root Joint to Tip Joint chain" for joint in joints}

        for input_name, _ in _TWISTS:
            for joint in self.input(input_name).get() or []:
                if not mref.objExists(joint):
                    log.warning(f"{self.label()}: The {input_name} joint {joint} does not exist")
                    return False

                full_name = mref.get(joint).full_name()
                if full_name in used:
                    log.warning(
                        f"{self.label()}: {joint} is in the {input_name} but is already part of the "
                        f"{used[full_name]}. Twist joints must be separate joints."
                    )
                    return False
                used[full_name] = input_name

        return True

    def run(self) -> bool:
        """
        Builds the flexi two bone ik and sets the outputs to its controls.
        """
        upper, lower, tip = self._chain()

        setup = flexi_two_bone_ik.FlexiTwoBoneIk(
            upper_joint=upper,
            lower_joint=lower,
            wrist_joint=tip,
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=self.input("Parent").get(),
            shape_scale=self.option("Shape Scale").get() or None,
            soft_ik=self.option("Apply Soft Ik").get(),
            world_space_ik_controls=self.option("World Space IK Controls").get(),
            upper_twist_joints=self.input("Upper Twist Joints").get() or [],
            lower_twist_joints=self.input("Lower Twist Joints").get() or [],
            ik_target_guide=self.input("IK Target Guide").get() or None,
        ).build()

        for output_name, control in [
            ("IK Root", setup.ik_root_control),
            ("IK Target", setup.ik_target_control),
            ("Upvector", setup.upvector_control),
            ("Top FK", setup.top_fk_control),
            ("Mid FK", setup.mid_fk_control),
            ("Bottom FK", setup.bottom_fk_control),
        ]:
            self.output(output_name).set(control.ctl)

        return True

    def _chain(self) -> list:
        """
        Returns the joints from the root joint to the tip joint, or an empty
        list if either is missing or the tip is not below the root.
        """
        root_joint = self.input("Root Joint").get()
        tip_joint = self.input("Tip Joint").get()

        if not root_joint or not tip_joint or not mref.objExists(root_joint) or not mref.objExists(tip_joint):
            return []

        try:
            return au.scene.joints.get_between(start=root_joint, end=tip_joint)
        except ValueError:
            return []

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the root to tip chain followed by the upper and then the lower
        twist joints. Empty if the root or tip joint is missing.
        """
        chain = self._chain()
        if not chain:
            return []

        return chain + [
            joint
            for input_name, _ in _TWISTS
            for joint in self.input(input_name).get() or []
            if joint
        ]

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the root joint. Empty if there is no root joint
        or it has no parent.
        """
        root_joint = self.input("Root Joint").get()
        if not root_joint or not mref.objExists(root_joint):
            return ""

        parent = mref.get(root_joint).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's joints if they already exist (the search and
        replaced names), otherwise copies the original's chain and twist
        joints into the mirrored hierarchy for this component to drive.
        Either way no joints are created on entering the stack, as this
        component already has them.
        """
        self.option("Create Joints").set(False)

        original_items = mirrored_from.mirror_mixin_items_to_mirror()
        if not original_items:
            return

        if self.mirror_mixin_counterparts_exist(original_items, self.mirror_mixin_items_to_mirror()):
            return

        copies = self.mirror_mixin_copy_nodes(original_items)
        self.input("Root Joint").set(copies[0])
        self.input("Tip Joint").set(copies[2])

        remaining = copies[3:]
        for input_name, _ in _TWISTS:
            count = len([joint for joint in mirrored_from.input(input_name).get() or [] if joint])
            self.input(input_name).set(remaining[:count])
            remaining = remaining[count:]

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        Restores the Create Joints option so this component's data matches
        the original
        """
        self.option("Create Joints").set(mirrored_from.option("Create Joints").get(resolved=False))
