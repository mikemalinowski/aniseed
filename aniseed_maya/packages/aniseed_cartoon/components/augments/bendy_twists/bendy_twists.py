"""
Provides the "Augment : Bendy Twists" component, which drives a set of twist
joints along a bendy, twisting and squashing curve between two joints (see
aniseed_cartoon.rigging.bendy_twists).
"""
import os
import mref
import typing
import logging
import aniseed
import functools
import aniseed_utilities as au
from aniseed_cartoon.rigging import bendy_twists

log = logging.getLogger(__name__)


class BendyTwistsComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    """
    Drives the given twist joints along a four point curve between the Start
    Joint and End Joint. A bendy control sits at each point of the curve, and
    the twist joints take a twist blended from the Start Twist Node to the
    End Twist Node, and squash as the joints move together.

    The squashAndStretchAlpha and scaleFalloff attributes are on the first
    bendy control. The twist joints can be created from the right click menu.
    """

    identifier = "Augment : Bendy Twists"
    icon = os.path.join(
        os.path.dirname(__file__),
        "bendy_twists.png",
    )

    # -- How many bendy controls the setup creates (one per curve point)
    BENDY_CONTROL_COUNT = len(bendy_twists.BendyTwisters.POINT_PERCENTAGES)

    # -- Version 2 removed the Twist Count option, as the count comes from
    # -- the Twist Joints input
    version = 2

    @classmethod
    def migrate(cls, data: dict, from_version: int) -> dict:
        """
        Drops the Twist Count option saved by version 1.
        """
        if from_version < 2:
            (data.get("options") or dict()).pop("Twist Count", None)
        return data

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, joint and twist node inputs, the naming and
        twist count options and an output per bendy control.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the bendy controls",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Start Joint",
            description="The joint the curve starts at",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="End Joint",
            description="The joint the curve ends at",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Twist Joints",
            description="The joints to drive along the curve, ordered from the start joint to the end joint",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Start Twist Node",
            description=(
                "Optional node whose roll the start of the curve holds (such as a "
                "shoulder or ik root). If not given, the start joint's roll is used."
            ),
            validate=False,
            group="Twist",
        )

        self.declare_input(
            name="End Twist Node",
            description="Optional node whose roll the end of the curve reaches. If not given, the end joint is used.",
            validate=False,
            group="Twist",
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
            value=self.config.middle,
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Shape Scale",
            description="The scale of the control shapes. If zero, it is worked out from the distance between the joints.",
            value=0.0,
            group="Behaviour",
        )

        for idx in range(self.BENDY_CONTROL_COUNT):
            self.declare_output(f"Bendy {idx + 1}")

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output.
        """
        self.input("Parent").hook_to_parent()

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
        if requirement_name in ["Parent", "Start Joint", "End Joint", "Start Twist Node", "End Twist Node"]:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Twist Joints":
            return aniseed.widgets.ObjectList()

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Offers to create the twist joints when there are none. Mirroring is
        offered by au.mixins.MirrorMixin.
        """
        menu = super().user_functions()

        if self._joints_exist() and not self.input("Twist Joints").get():
            menu["Create Twist Joints"] = functools.partial(self.user_func_create_twist_joints)

        return menu

    def user_func_create_twist_joints(self, twist_count: int = None):
        """
        Creates twist joints under the start joint, and sets the Twist Joints
        input to them. The count is asked for if it is not given.
        """
        if not self._joints_exist():
            log.warning(f"{self.label()}: Set the Start Joint and End Joint before creating twist joints")
            return

        twist_count = aniseed.dialogs.request_count(
            twist_count,
            title="Twist Count",
            message="How many twist joints do you want?",
        )
        if not twist_count or twist_count < 1:
            return

        self.input("Twist Joints").set(
            bendy_twists.create_twist_joints(
                start_joint=self.input("Start Joint").get(),
                end_joint=self.input("End Joint").get(),
                count=twist_count,
                config=self.config,
                prefix=self.option("Descriptive Prefix").get(),
                location=self.option("Location").get(),
            ),
        )

    def is_valid(self) -> bool:
        """
        Checks the joints, the twist joints and any twist nodes exist.
        """
        if not self._joints_exist():
            log.warning(f"{self.label()}: The Start Joint and End Joint must be set to existing joints")
            return False

        twist_joints = self.input("Twist Joints").get() or []
        if not twist_joints:
            log.warning(f"{self.label()}: No twist joints given. Right click the component to create them.")
            return False

        ends = {mref.get(self.input(name).get()).full_name() for name in ["Start Joint", "End Joint"]}
        seen = set()

        for joint in twist_joints:
            if not mref.objExists(joint):
                log.warning(f"{self.label()}: The twist joint {joint} does not exist")
                return False

            full_name = mref.get(joint).full_name()
            if full_name in ends:
                log.warning(f"{self.label()}: {joint} is the Start or End Joint, so it cannot also be a twist joint")
                return False

            if full_name in seen:
                log.warning(f"{self.label()}: {joint} is in the Twist Joints more than once")
                return False
            seen.add(full_name)

        for input_name in ["Start Twist Node", "End Twist Node"]:
            node = self.input(input_name).get()
            if node and not mref.objExists(node):
                log.warning(f"{self.label()}: The {input_name} ({node}) does not exist")
                return False

        return True

    def run(self) -> bool:
        """
        Builds the bendy twists and sets the outputs to its controls.
        """
        setup = bendy_twists.BendyTwisters(
            start_joint=self.input("Start Joint").get(),
            end_joint=self.input("End Joint").get(),
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            count=0,
            parent=self.input("Parent").get(),
            shape_scale=self.option("Shape Scale").get() or None,
            start_twist_node=self.input("Start Twist Node").get() or None,
            end_twist_node=self.input("End Twist Node").get() or None,
            twist_joints=self.input("Twist Joints").get(),
        ).build()

        for idx, control in enumerate(setup.controls):
            self.output(f"Bendy {idx + 1}").set(control.ctl)

        return True

    def _joints_exist(self) -> bool:
        """
        Returns True if the start and end joints are set and exist
        """
        return all(
            joint and mref.objExists(joint)
            for joint in [self.input("Start Joint").get(), self.input("End Joint").get()]
        )

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the twist joints, which are the only joints this component
        owns.
        """
        return [joint for joint in self.input("Twist Joints").get() or [] if joint]

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the start joint, which the twist joints are created under.
        """
        return self.input("Start Joint").get() or ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's twist joints if they already exist (the search
        and replaced names), otherwise copies the original's twist joints into
        the mirrored hierarchy for this component to drive.
        """
        original_joints = mirrored_from.mirror_mixin_items_to_mirror()
        if not original_joints:
            return

        if self.mirror_mixin_counterparts_exist(original_joints, self.mirror_mixin_items_to_mirror()):
            return

        self.input("Twist Joints").set(self.mirror_mixin_copy_nodes(original_joints))
