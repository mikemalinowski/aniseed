"""
Provides the "Limb : Leg (Dynamic Pivot)" component, an ik/fk spring limb leg whose ik
is driven by a dynamic foot pivot, with a toe that blends between ik and fk,
and optional soft ik (see aniseed_experimental.rigging.flexi_leg). Twists
are added as an "Augment : Multi Chain Twists" child component.
"""
import os
import mref
import typing
import logging
import collections
import aniseed
import aniseed_utilities as au
from maya import cmds
from maya.api import OpenMaya as om
from aniseed_experimental.rigging import flexi_leg
from aniseed_experimental.rigging import multi_chain_twists

log = logging.getLogger(__name__)


# -- The joint inputs, in chain order
_JOINTS = ["Upper Leg Joint", "Mid Leg Joint", "Foot Joint", "Toe Joint"]

# -- The bones twist joints are created along: the label of each, the joint
# -- inputs it runs between, and the option giving how many it gets
_TWISTS = [
    ("Upper", "Upper Leg Joint", "Mid Leg Joint", "Upper Twist Count"),
    ("Lower", "Mid Leg Joint", "Foot Joint", "Lower Twist Count"),
]

_TWISTS_TYPE = "Augment : Multi Chain Twists"

# -- The guide inputs, which may be given the same node
_GUIDES = ["Pivot Guide Curve", "IK Target Guide", "Pivot Control Transform"]


class FlexiLegComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    """
    Builds an ik/fk leg on an upper leg, mid leg, foot and toe joint. The ik
    is a spring ik whose handle follows a dynamic foot pivot under the IK
    Target control, so the Pivot control rocks the foot along the Pivot Guide
    Curve and rolls the heel. In fk the FK controls drive the leg, foot and
    toe.

    The ikfk attribute is on the Root control (0 is ik, 1 is fk), and every
    other control carries it as a proxy. Soft ik attributes are on the IK
    Target control.

    When it enters the stack and creates its joints, twist joints are created
    along the upper and lower leg (as many as the Upper and Lower Twist Count
    options give) and, if there are any, an "Augment : Multi Chain Twists"
    component is added beneath it to drive them, which manages them from then
    on. While it has a twists child, the leg adds a ShowDetailedControls
    attribute to the Root control (proxied to every ik and fk control), which
    a "Utility : Connect Attribute (Multi)" under the twists connects to the
    visibility of the twist control shapes.
    """

    identifier = "Limb : Leg (Dynamic Pivot)"
    deprecated_names = ["Limb : Flexi Leg"]
    icon = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "flexi_two_bone_ik",
        "flexi_two_bone_ik.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, joint and guide inputs, the naming and
        behaviour options and an output per control.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        for input_name, description in zip(
            _JOINTS,
            [
                "The upper leg joint",
                "The mid leg (knee) joint, directly below the upper leg joint",
                "The foot joint, directly below the mid leg joint",
                "The toe joint, below the foot joint",
            ],
        ):
            self.declare_input(
                name=input_name,
                description=description,
                validate=True,
                group="Required Joints",
            )

        self.declare_input(
            name="Pivot Guide Curve",
            description="The curve the foot pivot slides along, lying in the xz plane with z forward",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="IK Target Guide",
            description="Optional transform to place the IK Target control at. If not given, it matches the Pivot Guide Curve.",
            validate=False,
            group="Optional Nodes",
        )

        self.declare_input(
            name="Pivot Control Transform",
            description="Optional transform to match the Pivot control's org to (position and rotation)",
            validate=False,
            group="Optional Nodes",
        )

        self.declare_option(
            name="Descriptive Prefix",
            description="Prefix used when naming the joints, controls and mechanical nodes",
            value="Leg",
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
            description="If enabled, soft ik (with stretch) is applied to the ik chain, with its attributes on the IK Target control",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Rotation Multiplier",
            description="Multiplies the Pivot control's rotation before it drives anything",
            value=2.0,
            group="Behaviour",
        )

        self.declare_option(
            name="Rotation Limit",
            description="The Pivot control's x and z rotation is limited to plus and minus this value",
            value=45.0,
            group="Behaviour",
        )

        self.declare_option(
            name="Invert Pivot Z",
            description="If True, the Pivot control's z rotation is inverted. Mirroring sets it to the opposite of the original's.",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Shape Scale",
            description="The scale of the control shapes. If zero, it is worked out from the length of the chain.",
            value=0.0,
            group="Behaviour",
        )

        self.declare_option(
            name="Debug",
            description="If True, a sphere is created which sits at the foot pivot point",
            value=False,
            group="Behaviour",
        )

        # -- Only used to create the joints, twists and space switches when
        # -- entering the stack
        self.declare_option(name="Create Joints", value=True, pre_expose=True)
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Apply Space Switches", value=True, pre_expose=True)

        for output_name in [
            "Root",
            "IK Target",
            "Pole Vector",
            "Pivot",
            "Heel",
            "IK Toe",
            "FK Upper",
            "FK Mid",
            "FK Foot",
            "FK Toe",
        ]:
            self.declare_output(output_name)

        self.declare_output(
            name="Blended Foot",
            description="The blend chain's foot, which the Foot Joint follows",
            is_default=True,
        )

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output,
        creates the joints and twists if the Create Joints option is set, and
        adds the space switches if the Apply Space Switches option is set.
        """
        create_joints = self.option("Create Joints")
        apply_space_switches = self.option("Apply Space Switches")
        twist_counts = [self.option(option_name) for *_, option_name in _TWISTS]

        for option in [create_joints, apply_space_switches] + twist_counts:
            option.set_hidden(True)

        self.input("Parent").hook_to_parent()

        if create_joints.get():
            self._create_joints(parent=au.core.selection.first_selected())
            self._add_twists()

        if apply_space_switches.get():
            self._create_space_switches()

    def _create_space_switches(self):
        """
        Adds space switch components beneath this one for the IK Target
        control (Parent and World, defaulting to World) and the Pole Vector
        control (Parent, Foot and World, defaulting to Foot). Parent is the
        Root control, Foot the IK Target control and World the Global
        Control Root's main control. Skipped with a logged message if there
        is no "Core : Global Control Root" component in the stack.
        """
        global_srt_component = self.stack.get_component_by_type("Core : Global Control Root")
        if not global_srt_component:
            log.info(f"{self.label()}: No Global Control Root found, so no space switches are added")
            return

        world = global_srt_component.output("Main Control").address()
        root = self.output("Root").address()
        ik_target = self.output("IK Target").address()

        space_switch = self.rig.component_library.request("Augment : Space Switch")

        space_switch.add_to(
            component=self,
            label=f"{self.label()} IK Space Switch",
            driven=ik_target,
            default_space="World",
            spaces=[
                ("Parent", root),
                ("World", world),
            ],
        )

        space_switch.add_to(
            component=self,
            label=f"{self.label()} Pole Vector Space Switch",
            driven=self.output("Pole Vector").address(),
            default_space="Foot",
            spaces=[
                ("Parent", root),
                ("Foot", ik_target),
                ("World", world),
            ],
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
        return aniseed.widgets.ObjectSelector(component=self)

    def _add_twists(self):
        """
        Creates the twist joints along the upper and lower leg (as many as the
        Upper and Lower Twist Count options give) and, if there are any, adds
        an "Augment : Multi Chain Twists" component beneath this one to drive
        them, from the upper leg to the foot. Its controls sit under the Root
        control, whose roll the upper leg's twist holds, and their visibility
        is driven by the Root control's ShowDetailedControls attribute. From
        then on the twists are managed by that component alone.
        """
        twist_joints = []

        for label, start, end, option_name in _TWISTS:
            count = self.option(option_name).get()
            if count < 1:
                continue

            twist_joints.extend(
                multi_chain_twists.create_twist_joints(
                    start_joint=self.input(start).get(),
                    end_joint=self.input(end).get(),
                    count=count,
                    config=self.config,
                    prefix=f"{self.option('Descriptive Prefix').get()}{label}",
                    location=self.option("Location").get(),
                ),
            )

        if not twist_joints:
            return

        root = self.output("Root").address()
        self.rig.component_library.request(_TWISTS_TYPE).add_to(
            component=self,
            label=f"{self.label()} Twists",
            parent=root,
            start_joint=self.input("Upper Leg Joint").get(),
            end_joint=self.input("Foot Joint").get(),
            twist_joints=twist_joints,
            root_twist_node=root,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            visibility_source=(root, flexi_leg.FlexiLeg.SHOW_DETAILED_CONTROLS),
        )

    def _twists(self) -> list:
        """
        Returns the Multi Chain Twists components beneath this component
        """
        return [child for child in self.children if child.identifier == _TWISTS_TYPE]

    def _create_joints(self, parent):
        """
        Creates an upper leg, mid leg, foot and toe chain under the given
        parent (or the world if there is none) and sets the joint inputs to it.
        """
        # -- The labels follow the Descriptive Prefix (so "Leg" gives LegUpper,
        # -- LegMid, LegFoot and LegToe)
        joint_data = collections.OrderedDict()
        joint_data["Upper"] = {"jointOrientX": 90, "jointOrientY": -4, "jointOrientZ": -90}
        joint_data["Mid"] = {"tx": 42, "jointOrientZ": -11}
        joint_data["Foot"] = {"tx": 42, "jointOrientZ": 55}
        joint_data["Toe"] = {"tx": 10, "jointOrientZ": 42}

        joints = au.scene.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=self.option("Location").get(),
            config=self.config,
            parent=None,
            prefix=self.option("Descriptive Prefix").get(),
        )

        # -- As with "Limb : Leg", the chain is built in world space and then
        # -- placed under, and at the position of, the parent
        if parent:
            root_joint = mref.get(joints[0])
            root_joint.set_parent(parent)
            root_joint.set_position(mref.get(parent).get_position(space="world"), space="world")

        for input_name, joint in zip(_JOINTS, joints):
            self.input(input_name).set(joint)

    def is_valid(self) -> bool:
        """
        Checks the upper leg to foot joints form a chain of exactly three
        joints with the toe below the foot, that the guide is a nurbs curve
        and that the ik target guide exists if it is given.
        """
        for input_name in _JOINTS:
            joint = self.input(input_name).get()
            if not joint or not mref.objExists(joint):
                log.warning(f"{self.label()}: The {input_name} must be set to an existing joint")
                return False

        upper, mid, foot, toe = [mref.get(self.input(name).get()).full_name() for name in _JOINTS]

        if self._chain() != [upper, mid, foot]:
            log.warning(
                f"{self.label()}: The Mid Leg Joint must be directly below the Upper Leg Joint, "
                f"and the Foot Joint directly below the Mid Leg Joint"
            )
            return False

        if not toe.startswith(f"{foot}|"):
            log.warning(f"{self.label()}: The Toe Joint must be below the Foot Joint")
            return False

        guide = self.input("Pivot Guide Curve").get()
        if not guide or not mref.objExists(guide):
            log.warning(f"{self.label()}: The Pivot Guide Curve must be set to an existing curve")
            return False

        if not mref.listRelatives(guide, shapes=True, type="nurbsCurve", noIntermediate=True):
            log.warning(f"{self.label()}: The Pivot Guide Curve ({guide}) is not a nurbs curve")
            return False

        # -- The IK Target control is matched to the guide, so it would take
        # -- on any scale the guide has (including scale from its parents)
        guide_matrix = om.MMatrix(cmds.xform(guide, query=True, matrix=True, worldSpace=True))
        guide_scale = om.MTransformationMatrix(guide_matrix).scale(om.MSpace.kWorld)
        if any(abs(value - 1.0) > 1e-4 for value in guide_scale):
            log.warning(
                f"{self.label()}: The Pivot Guide Curve ({guide}) has a world scale of "
                f"{[round(value, 4) for value in guide_scale]}. It must be 1 (freeze its scale)."
            )
            return False

        # -- A guide connected to another component's output may only be
        # -- created as that component builds, so only a given guide is checked
        for input_name in ["IK Target Guide", "Pivot Control Transform"]:
            optional_guide = self.input(input_name)
            if optional_guide.get() and not optional_guide.is_address() and not mref.objExists(optional_guide.get()):
                log.warning(f"{self.label()}: The {input_name} ({optional_guide.get()}) does not exist")
                return False

        return True

    def run(self) -> bool:
        """
        Builds the flexi leg and sets the outputs to its controls. The
        ShowDetailedControls attribute is added if there is a twists child.
        """
        leg = flexi_leg.FlexiLeg(
            upper_joint=self.input("Upper Leg Joint").get(),
            foot_joint=self.input("Foot Joint").get(),
            toe_joint=self.input("Toe Joint").get(),
            guide_curve=self.input("Pivot Guide Curve").get(),
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=self.input("Parent").get(),
            ik_target_transform=self.input("IK Target Guide").get() or None,
            shape_scale=self.option("Shape Scale").get() or None,
            soft_ik=self.option("Apply Soft Ik").get(),
            show_detailed_controls=bool(self._twists()),
            rotation_multiplier=self.option("Rotation Multiplier").get(),
            rotation_limit=self.option("Rotation Limit").get(),
            debug=self.option("Debug").get(),
            pivot_control_transform=self.input("Pivot Control Transform").get() or None,
            invert_pivot_z=self.option("Invert Pivot Z").get(),
        ).build()

        for output_name, node in [
            ("Root", leg.root_control.ctl),
            ("IK Target", leg.ik_target_control.ctl),
            ("Pole Vector", leg.pole_vector_control.ctl),
            ("Pivot", leg.foot_pivot.control.ctl),
            ("Heel", leg.foot_pivot.heel_control.ctl),
            ("IK Toe", leg.foot_pivot.toe_control.ctl),
            ("FK Upper", leg.fk_controls[0].ctl),
            ("FK Mid", leg.fk_controls[1].ctl),
            ("FK Foot", leg.fk_controls[2].ctl),
            ("FK Toe", leg.fk_toe_control.ctl),
            ("Blended Foot", leg.blend_chain[-1]),
        ]:
            self.output(output_name).set(node)

        return True

    def _joints_exist(self) -> bool:
        """
        Returns True if every leg joint input is set and exists
        """
        return all(
            self.input(name).get() and mref.objExists(self.input(name).get())
            for name in _JOINTS
        )

    def _chain(self) -> typing.List[str]:
        """
        Returns the joints from the upper leg joint to the foot joint, or an
        empty list if either is missing or the foot is not below the upper leg
        """
        upper = self.input("Upper Leg Joint").get()
        foot = self.input("Foot Joint").get()

        if not all(joint and mref.objExists(joint) for joint in [upper, foot]):
            return []

        upper = mref.get(upper).full_name()
        foot = mref.get(foot).full_name()
        if not foot.startswith(f"{upper}|"):
            return []

        return [mref.get(joint).full_name() for joint in au.scene.joints.get_between(start=upper, end=foot)]

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the leg joints, then the guides. Empty if any leg joint is
        missing.
        """
        if not self._joints_exist():
            return []

        return [self.input(name).get() for name in _JOINTS] + self._guides()

    def _guides(self) -> typing.List[str]:
        """
        Returns the pivot guide curve, then the IK Target Guide and Pivot
        Control Transform (when given), listing a node used by more than one
        only once
        """
        guides = []
        for input_name in _GUIDES:
            guide = self.input(input_name).get()
            if guide and guide not in guides:
                guides.append(guide)
        return guides

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the upper leg joint. Empty if there is no upper
        leg joint or it has no parent.
        """
        upper = self.input("Upper Leg Joint").get()
        if not upper or not mref.objExists(upper):
            return ""

        parent = mref.get(upper).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's joints and guides if they already exist (the
        search and replaced names), otherwise copies the original's into the
        mirrored hierarchy for this component to drive. Either way no joints
        are created on entering the stack, as this component already has them,
        and no twists or space switches are added, as the original's are
        mirrored with this component.
        """
        self.option("Create Joints").set(False)
        self.option("Apply Space Switches").set(False)

        original_items = mirrored_from.mirror_mixin_items_to_mirror()
        if not original_items:
            return

        if self.mirror_mixin_counterparts_exist(original_items, self.mirror_mixin_items_to_mirror()):
            return

        copies = self.mirror_mixin_copy_nodes(original_items)

        for input_name in _JOINTS:
            self.input(input_name).set(copies.pop(0))

        # -- A guide used by more than one input was only copied once
        guide_copies = dict(zip(mirrored_from._guides(), copies))
        for input_name in _GUIDES:
            guide = mirrored_from.input(input_name).get()
            if guide:
                self.input(input_name).set(guide_copies[guide])

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        Restores the Create Joints and Apply Space Switches options so this
        component's data matches the original, sets Invert Pivot Z to the
        opposite of the original's,
        and reflects the pivot guide curve's cvs. The mirror pass mirrors the
        curve's transform as it would a joint, which turns the curve's shape
        around, so its cvs are set to the reflection of the original's (in
        world space, across the YZ plane).
        """
        for option_name in ["Create Joints", "Apply Space Switches"]:
            self.option(option_name).set(mirrored_from.option(option_name).get(resolved=False))
        self.option("Invert Pivot Z").set(not mirrored_from.option("Invert Pivot Z").get())

        original = mirrored_from.input("Pivot Guide Curve").get()
        mirrored = self.input("Pivot Guide Curve").get()

        if not original or not mirrored or original == mirrored:
            return

        if not mref.objExists(original) or not mref.objExists(mirrored):
            return

        positions = cmds.xform(f"{original}.cv[*]", query=True, translation=True, worldSpace=True)
        if len(positions) != len(cmds.xform(f"{mirrored}.cv[*]", query=True, translation=True, worldSpace=True)):
            log.warning(f"{self.label()}: {mirrored} does not have the same cvs as {original}, so it is not reflected")
            return

        for idx in range(len(positions) // 3):
            x, y, z = positions[idx * 3:idx * 3 + 3]
            cmds.xform(f"{mirrored}.cv[{idx}]", translation=[-x, y, z], worldSpace=True)
