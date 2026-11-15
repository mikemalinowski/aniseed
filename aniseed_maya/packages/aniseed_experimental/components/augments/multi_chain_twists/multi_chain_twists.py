"""
Provides the "Augment : Multi Chain Twists" component, which drives a set of
twist joints along a chain of bendy, twisting and squashing curves between
two joints (see aniseed_experimental.rigging.multi_chain_twists).
"""
import os
import mref
import typing
import logging
import aniseed
import functools
import aniseed_utilities as au
from aniseed_experimental.rigging import multi_chain_twists

log = logging.getLogger(__name__)


class MultiChainTwistsComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    """
    Drives the given twist joints along a curve between each pair of key
    joints, where the key joints are the Start Joint, the End Joint and every
    joint between them. A key control sits at each key joint and a cv control
    at each curve cv, and the twist joints twist from one key control's roll
    to the next, squash as their curve shortens and scale with the cv
    controls and key controls (a key control's scale spreads over the
    segments either side of it).

    Each segment's squashAndStretchAlpha and scaleFalloff attributes are on
    the key control at its start. The twist joints can be created from the
    right click menu.
    """

    identifier = "Augment : Multi Chain Twists"
    icon = os.path.join(os.path.dirname(__file__), "multi_chain_twists.png")

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, joint and twist joint inputs, the naming and
        behaviour options, and the Control Shapes output. The control outputs
        are declared by run, as they depend on the length of the chain.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the controls",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Start Joint",
            description="The first key joint",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="End Joint",
            description="The last key joint, which must be below the Start Joint",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Twist Joints",
            description="The joints to drive along the curves, ordered from the start joint to the end joint",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Root Twist Node",
            description=(
                "Optional node whose roll the start of the first segment holds (such as a limb's "
                "root control), so the twists counter the start joint rolling. If not given, the "
                "start joint's roll is used."
            ),
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
            name="CVs Per Segment",
            description="How many cvs each curve between two key joints has, including the cvs at the key joints",
            value=4,
            group="Behaviour",
        )

        self.declare_option(
            name="Shape Scale",
            description="The scale of the control shapes. If zero, it is worked out from the length of the chain.",
            value=0.0,
            group="Behaviour",
        )

        self.declare_output(
            name="Control Shapes",
            description=(
                "The shape nodes of every key and cv control, for other components to drive (such as their "
                "visibility with \"Utility : Connect Attribute (Multi)\")"
            ),
        )

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
        if requirement_name in ["Parent", "Start Joint", "End Joint", "Root Twist Node"]:
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
        Creates twist joints in every segment, under each segment's start key
        joint, and sets the Twist Joints input to them. The count per segment
        is asked for if it is not given.
        """
        if not self._joints_exist():
            log.warning(f"{self.label()}: Set the Start Joint and End Joint before creating twist joints")
            return

        twist_count = aniseed.dialogs.request_count(
            twist_count,
            title="Twist Count",
            message="How many twist joints do you want in each segment?",
        )
        if not twist_count or twist_count < 1:
            return

        self.input("Twist Joints").set(
            multi_chain_twists.create_twist_joints(
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
        Checks the joints form a chain, the twist joints exist and the cv
        count is usable.
        """
        if not self._joints_exist():
            log.warning(f"{self.label()}: The Start Joint and End Joint must be set to existing joints")
            return False

        try:
            key_joints = multi_chain_twists.MultiChainTwisters._key_joints(
                mref.get(self.input("Start Joint").get()),
                mref.get(self.input("End Joint").get()),
            )
        except ValueError:
            log.warning(f"{self.label()}: The End Joint must be below the Start Joint")
            return False

        if len(key_joints) < 2:
            log.warning(f"{self.label()}: The Start Joint and End Joint must be different joints")
            return False

        if self.option("CVs Per Segment").get() < 2:
            log.warning(f"{self.label()}: CVs Per Segment must be at least 2")
            return False

        twist_joints = self.input("Twist Joints").get() or []
        if not twist_joints:
            log.warning(f"{self.label()}: No twist joints given. Right click the component to create them.")
            return False

        keys = {joint.full_name() for joint in key_joints}
        seen = set()

        for joint in twist_joints:
            if not mref.objExists(joint):
                log.warning(f"{self.label()}: The twist joint {joint} does not exist")
                return False

            full_name = mref.get(joint).full_name()
            if full_name in keys:
                log.warning(f"{self.label()}: {joint} is a key joint, so it cannot also be a twist joint")
                return False

            if full_name in seen:
                log.warning(f"{self.label()}: {joint} is in the Twist Joints more than once")
                return False
            seen.add(full_name)

        return True

    def run(self) -> bool:
        """
        Builds the multi chain twists, declares and sets an output for every
        key control and cv control, and sets the Control Shapes output.
        """
        setup = multi_chain_twists.MultiChainTwisters(
            start_joint=self.input("Start Joint").get(),
            end_joint=self.input("End Joint").get(),
            twist_joints=self.input("Twist Joints").get(),
            cvs_per_segment=self.option("CVs Per Segment").get(),
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=self.input("Parent").get(),
            shape_scale=self.option("Shape Scale").get() or None,
            root_twist_node=self.input("Root Twist Node").get() or None,
        ).build()

        # -- Remove the control outputs declared by any previous build, as the
        # -- length of the chain or the cv count may have changed since then
        for prefix in ["Key Control ", "Segment "]:
            au.rig.component_outputs.clear_outputs(self, prefix)

        for idx, control in enumerate(setup.key_controls):
            self.declare_output(f"Key Control {idx + 1}")
            self.output(f"Key Control {idx + 1}").set(control.ctl)

        for segment, controls in enumerate(setup.cv_controls):
            for idx, control in enumerate(controls):
                self.declare_output(f"Segment {segment + 1} Cv {idx + 1}")
                self.output(f"Segment {segment + 1} Cv {idx + 1}").set(control.ctl)

        controls = setup.key_controls + [control for controls in setup.cv_controls for control in controls]
        self.output("Control Shapes").set([
            shape.full_name()
            for control in controls
            for shape in mref.get(control.ctl).shapes()
        ])

        return True

    @classmethod
    def add_to(
            cls,
            component,
            label: str,
            parent: str,
            start_joint: str,
            end_joint: str,
            twist_joints: typing.List[str],
            root_twist_node: str = "",
            prefix: str = "",
            location: str = None,
            visibility_source: typing.Tuple[str, str] = None,
    ):
        """
        Adds a Multi Chain Twists component to the stack as a child of the
        given component, filled in with the given details. If a visibility
        source is given, a "Utility : Connect Attribute (Multi)" component is
        added beneath it, connecting that attribute to the visibility of every
        twist control shape (see the Control Shapes output).

        Other components can reach this without importing this module, via
        ``self.rig.component_library.request("Augment : Multi Chain Twists").add_to(...)``.

        Args:
            component: The component to add the twists beneath
            label: The label for the twists component
            parent: The node (or address) to parent the controls under
            start_joint: The first key joint
            end_joint: The last key joint
            twist_joints: The joints to drive, from the start joint to the end
            root_twist_node: Optional node (or address) whose roll the start
                of the first segment holds
            prefix: Sets the Descriptive Prefix option
            location: Sets the Location option. If not given, the given
                component's Location is used (if it has one).
            visibility_source: Optional (node or address, attribute name) to
                drive the visibility of the twist control shapes with

        Returns:
            The multi chain twists component
        """
        if location is None and component.option("Location") is not None:
            location = component.option("Location").get()

        options = {"Descriptive Prefix": prefix}
        if location is not None:
            options["Location"] = location

        # -- Events are suppressed so on_enter_stack does not hook the Parent
        # -- to the parent component's default output
        twists = component.stack.add_component(
            component_type=cls.identifier,
            label=label,
            parent=component,
            inputs={
                "Parent": parent,
                "Start Joint": start_joint,
                "End Joint": end_joint,
                "Twist Joints": list(twist_joints),
                "Root Twist Node": root_twist_node,
            },
            options=options,
            suppress_events=True,
        )

        if twists and visibility_source:
            source_node, source_attribute = visibility_source
            component.stack.add_component(
                component_type="Utility : Connect Attribute (Multi)",
                label=f"{label} Visibility",
                parent=twists,
                inputs={
                    "Source Node": source_node,
                    "Source Attribute": source_attribute,
                    "Destination Nodes": [twists.output("Control Shapes").address()],
                    "Destination Attribute": "visibility",
                },
                suppress_events=True,
            )

        return twists

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
