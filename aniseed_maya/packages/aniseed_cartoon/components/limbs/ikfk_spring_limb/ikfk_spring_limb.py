"""
Provides the "Limb : IKFK Spring Limb" component, an ik/fk limb for a chain of
three or more joints, using maya's spring ik solver for the ik (see
aniseed_cartoon.rigging.ikfk_spring_limb).
"""
import os
import re
import mref
import typing
import logging
import aniseed
import aniseed_utilities as au
from aniseed_cartoon.rigging import ikfk_spring_limb

log = logging.getLogger(__name__)


class IkfkSpringLimbComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    """
    Builds an fk chain, a spring solved ik chain and a chain blended between
    the two, which drives the joints from the Start Joint to the End Joint.

    Everything sits under the Root control, which holds the ikfk attribute
    (0 is ik, 1 is fk). Every other control carries ikfk as a proxy of it.
    The IK Target control holds a springBias attribute for each joint which
    bends, to share the bend between them.
    """

    identifier = "Limb : IKFK Spring Limb"

    # -- The outputs declared per joint by run, e.g. "FK 1", "IK 2", "Blended 3"
    _NUMBERED_OUTPUT = re.compile(r"^(FK|IK|Blended) \d+$")
    icon = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "flexi_two_bone_ik",
        "flexi_two_bone_ik.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, joint and ik target guide inputs, the naming and
        shape scale options, and the outputs which do not depend on the
        length of the chain. The FK, IK and Blended outputs are declared by
        run.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Start Joint",
            description="The first joint of the limb",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="End Joint",
            description="The last joint of the limb, which must be below the Start Joint with at least one joint between",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="IK Target Guide",
            description="Optional transform to place the IK Target control at. If not given, it matches the End Joint.",
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
            value=self.config.middle,
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Shape Scale",
            description="The scale of the control shapes. If zero, it is worked out from the length of the chain.",
            value=0.0,
            group="Behaviour",
        )

        self.declare_output("Root")
        self.declare_output("IK Target")
        self.declare_output("Pole Vector")
        self.declare_output(
            name="IK Handle Transform",
            description="The parent of the ik handle, under the IK Target control and matched to the handle",
        )
        self.declare_output(
            name="Blended End",
            description="The last joint of the blend chain, which the End Joint follows",
            is_default=True,
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
        if requirement_name in ["Parent", "Start Joint", "End Joint", "IK Target Guide"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def is_valid(self) -> bool:
        """
        Checks the joints form a chain of at least three joints and that any
        IK Target Guide exists.
        """
        for input_name in ["Start Joint", "End Joint"]:
            joint = self.input(input_name).get()
            if not joint or not mref.objExists(joint):
                log.warning(f"{self.label()}: The {input_name} must be set to an existing joint")
                return False

        chain = self._chain()
        if not chain:
            log.warning(f"{self.label()}: The End Joint must be below the Start Joint")
            return False

        if len(chain) < 3:
            log.warning(f"{self.label()}: The limb needs at least three joints from the Start Joint to the End Joint")
            return False

        # -- A guide connected to another component's output may only be
        # -- created as that component builds, after validation, so only a
        # -- guide given directly is checked
        ik_target_guide = self.input("IK Target Guide")
        if ik_target_guide.get() and not ik_target_guide.is_address() and not mref.objExists(ik_target_guide.get()):
            log.warning(f"{self.label()}: The IK Target Guide ({ik_target_guide.get()}) does not exist")
            return False

        return True

    def run(self) -> bool:
        """
        Builds the limb and sets the outputs, declaring an FK output for every
        fk control and an IK and Blended output for every ik and blend joint.
        """
        limb = ikfk_spring_limb.IkfkSpringLimb(
            start_joint=self.input("Start Joint").get(),
            end_joint=self.input("End Joint").get(),
            ik_target_transform=self.input("IK Target Guide").get() or None,
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=self.input("Parent").get(),
            shape_scale=self.option("Shape Scale").get() or None,
        ).build()

        self.output("Root").set(limb.root_control.ctl)
        self.output("IK Target").set(limb.ik_target_control.ctl)
        self.output("Pole Vector").set(limb.pole_vector_control.ctl)
        self.output("IK Handle Transform").set(limb.ik_handle_transform)
        self.output("Blended End").set(limb.blend_chain[-1])

        # -- Remove the numbered outputs declared by any previous build, as
        # -- the number of joints may have changed since then
        for output in list(self.outputs()):
            if self._NUMBERED_OUTPUT.match(output.name()):
                self.remove_output(output.name())

        for label, nodes in [
            ("FK", [control.ctl for control in limb.fk_controls]),
            ("IK", limb.ik_chain),
            ("Blended", limb.blend_chain),
        ]:
            for idx, node in enumerate(nodes):
                self.declare_output(f"{label} {idx + 1}")
                self.output(f"{label} {idx + 1}").set(node)

        return True

    def _chain(self) -> typing.List[str]:
        """
        Returns the joints from the start joint to the end joint, or an empty
        list if either is missing or the end joint is not below the start
        """
        start_joint = self.input("Start Joint").get()
        end_joint = self.input("End Joint").get()

        if not all(joint and mref.objExists(joint) for joint in [start_joint, end_joint]):
            return []

        start = mref.get(start_joint).full_name()
        end = mref.get(end_joint).full_name()
        if not end.startswith(f"{start}|"):
            return []

        return au.scene.joints.get_between(start=start, end=end)

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the start to end chain, followed by the IK Target Guide if
        there is one. Empty if the chain is not valid.
        """
        chain = self._chain()
        if not chain:
            return []

        ik_target_guide = self.input("IK Target Guide").get()
        return chain + ([ik_target_guide] if ik_target_guide else [])

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the start joint. Empty if there is no start
        joint or it has no parent.
        """
        start_joint = self.input("Start Joint").get()
        if not start_joint or not mref.objExists(start_joint):
            return ""

        parent = mref.get(start_joint).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's joints (and guide) if they already exist (the
        search and replaced names), otherwise copies the original's into the
        mirrored hierarchy for this component to drive.
        """
        original_items = mirrored_from.mirror_mixin_items_to_mirror()
        if not original_items:
            return

        if self.mirror_mixin_counterparts_exist(original_items, self.mirror_mixin_items_to_mirror()):
            return

        copies = self.mirror_mixin_copy_nodes(original_items)
        chain_length = len(mirrored_from._chain())

        self.input("Start Joint").set(copies[0])
        self.input("End Joint").set(copies[chain_length - 1])
        if len(copies) > chain_length:
            self.input("IK Target Guide").set(copies[chain_length])
