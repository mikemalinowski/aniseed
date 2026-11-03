"""
Provides the "Limb : Flexi Leg" component, an ik/fk spring limb leg whose ik
is driven by a dynamic foot pivot, with a toe that blends between ik and fk,
and optional soft ik and multi chain twists (see
aniseed_cartoon.rigging.flexi_leg).
"""
import os
import mref
import typing
import logging
import collections
import aniseed
import functools
import aniseed_utilities as au
from maya import cmds
from aniseed_cartoon.rigging import flexi_leg
from aniseed_cartoon.rigging import multi_chain_twists

log = logging.getLogger(__name__)


# -- The joint inputs, in chain order
_JOINTS = ["Upper Leg Joint", "Mid Leg Joint", "Foot Joint", "Toe Joint"]

# -- The twist joint inputs, with the label of the bone each set runs along
# -- and the joint inputs it runs between
_TWISTS = [
    ("Upper Twist Joints", "Upper", "Upper Leg Joint", "Mid Leg Joint"),
    ("Lower Twist Joints", "Lower", "Mid Leg Joint", "Foot Joint"),
]

# -- The guide inputs, which may both be given the same node
_GUIDES = ["Pivot Guide Curve", "IK Target Guide"]


class FlexiLegComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    """
    Builds an ik/fk leg on an upper leg, mid leg, foot and toe joint. The ik
    is a spring ik whose handle follows a dynamic foot pivot under the IK
    Target control, so the Pivot control rocks the foot along the Pivot Guide
    Curve and rolls the heel. In fk the FK controls drive the leg, foot and
    toe.

    The ikfk attribute is on the Root control (0 is ik, 1 is fk), and every
    other control carries it as a proxy. Soft ik attributes are on the IK
    Target control. Twist joints given to the "Upper Twist Joints" and
    "Lower Twist Joints" inputs are driven by multi chain twists running from
    the upper leg to the foot, and can be created from the right click menu.
    """

    identifier = "Limb : Flexi Leg"
    icon = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "flexi_two_bone_ik",
        "flexi_two_bone_ik.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, joint, twist and guide inputs, the naming and
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
            name="Upper Twist Joints",
            description="Joints between the upper and mid leg joints, driven by the multi chain twists",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_input(
            name="Lower Twist Joints",
            description="Joints between the mid leg and foot joints, driven by the multi chain twists",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_input(
            name="IK Target Guide",
            description="Optional transform to place the IK Target control at. If not given, it matches the Foot Joint.",
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
            name="CVs Per Segment",
            description="How many cvs each twist curve (upper and lower leg) has, including the cvs at the leg joints",
            value=4,
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

        # -- Only used to create the joints when entering the stack
        self.declare_option(name="Create Joints", value=True, pre_expose=True)
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)

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

        # -- The twist control outputs are declared by run, as they depend
        # -- on the cv count
        self.declare_output(
            name="Blended Foot",
            description="The blend chain's foot, which the Foot Joint follows",
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
        if requirement_name in ["Upper Twist Joints", "Lower Twist Joints"]:
            return aniseed.widgets.ObjectList()

        return aniseed.widgets.ObjectSelector(component=self)

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Offers to create the twist joints for whichever twist input is empty.
        Mirroring is offered by au.mixins.MirrorMixin.
        """
        menu = super().user_functions()

        if self._joints_exist() and any(not self.input(input_name).get() for input_name, *_ in _TWISTS):
            menu["Create Twist Joints"] = functools.partial(self.user_func_create_twist_joints)

        return menu

    def user_func_create_twist_joints(self, upper_twist_count: int = None, lower_twist_count: int = None):
        """
        Creates the twist joints for each twist input which is empty, and sets
        the input to them. Any count which is not given is asked for.
        """
        if not self._joints_exist():
            log.warning(f"{self.label()}: Set the leg joints before creating twist joints")
            return

        for (input_name, label, start, end), count in zip(_TWISTS, [upper_twist_count, lower_twist_count]):
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
                multi_chain_twists.create_twist_joints(
                    start_joint=self.input(start).get(),
                    end_joint=self.input(end).get(),
                    count=count,
                    config=self.config,
                    prefix=f"{self.option('Descriptive Prefix').get()}{label}",
                    location=self.option("Location").get(),
                ),
            )

    def _create_joints(self, parent, upper_twist_count: int, lower_twist_count: int):
        """
        Creates an upper leg, mid leg, foot and toe chain under the given
        parent (or the world if there is none), sets the joint inputs to it
        and creates the twist joints.
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

        self.user_func_create_twist_joints(
            upper_twist_count=upper_twist_count,
            lower_twist_count=lower_twist_count,
        )

    def is_valid(self) -> bool:
        """
        Checks the upper leg to foot joints form a chain of exactly three
        joints with the toe below the foot, that the guide is a nurbs curve,
        that every twist joint exists (and is used once) and that the ik
        target guide exists if it is given.
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

        if self.option("CVs Per Segment").get() < 2:
            log.warning(f"{self.label()}: CVs Per Segment must be at least 2")
            return False

        # -- A guide connected to another component's output may only be
        # -- created as that component builds, so only a given guide is checked
        ik_target_guide = self.input("IK Target Guide")
        if ik_target_guide.get() and not ik_target_guide.is_address() and not mref.objExists(ik_target_guide.get()):
            log.warning(f"{self.label()}: The IK Target Guide ({ik_target_guide.get()}) does not exist")
            return False

        # -- The leg joints are driven by the limb, and each twist joint by the
        # -- twists, so no joint may be used twice
        used = {joint: "leg joints" for joint in [upper, mid, foot, toe]}

        for input_name, *_ in _TWISTS:
            for joint in self.input(input_name).get() or []:
                if not mref.objExists(joint):
                    log.warning(f"{self.label()}: The {input_name} joint {joint} does not exist")
                    return False

                full_name = mref.get(joint).full_name()
                if full_name in used:
                    log.warning(
                        f"{self.label()}: {joint} is in the {input_name} but is already one of the "
                        f"{used[full_name]}. Twist joints must be separate joints."
                    )
                    return False
                used[full_name] = input_name

        return True

    def run(self) -> bool:
        """
        Builds the flexi leg and sets the outputs to its controls.
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
            upper_twist_joints=self.input("Upper Twist Joints").get() or [],
            lower_twist_joints=self.input("Lower Twist Joints").get() or [],
            cvs_per_segment=self.option("CVs Per Segment").get(),
            rotation_multiplier=self.option("Rotation Multiplier").get(),
            rotation_limit=self.option("Rotation Limit").get(),
            debug=self.option("Debug").get(),
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

        # -- Remove the twist control outputs declared by any previous build,
        # -- as the cv count may have changed since then
        for prefix in ["Key Control ", "Segment "]:
            au.rig.component_outputs.clear_outputs(self, prefix)

        if leg.twisters:
            for idx, control in enumerate(leg.twisters.key_controls):
                self.declare_output(f"Key Control {idx + 1}")
                self.output(f"Key Control {idx + 1}").set(control.ctl)

            for segment, controls in enumerate(leg.twisters.cv_controls):
                for idx, control in enumerate(controls):
                    self.declare_output(f"Segment {segment + 1} Cv {idx + 1}")
                    self.output(f"Segment {segment + 1} Cv {idx + 1}").set(control.ctl)

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
        Returns the leg joints, then the upper and lower twist joints, then
        the guides. Empty if any leg joint is missing.
        """
        if not self._joints_exist():
            return []

        items = [self.input(name).get() for name in _JOINTS]
        for input_name, *_ in _TWISTS:
            items.extend(joint for joint in self.input(input_name).get() or [] if joint)

        return items + self._guides()

    def _guides(self) -> typing.List[str]:
        """
        Returns the pivot guide curve and the IK Target Guide (when given),
        listing a node used by both only once
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
        are created on entering the stack, as this component already has them.
        """
        self.option("Create Joints").set(False)

        original_items = mirrored_from.mirror_mixin_items_to_mirror()
        if not original_items:
            return

        if self.mirror_mixin_counterparts_exist(original_items, self.mirror_mixin_items_to_mirror()):
            return

        copies = self.mirror_mixin_copy_nodes(original_items)

        for input_name in _JOINTS:
            self.input(input_name).set(copies.pop(0))

        for input_name, *_ in _TWISTS:
            count = len([joint for joint in mirrored_from.input(input_name).get() or [] if joint])
            self.input(input_name).set(copies[:count])
            copies = copies[count:]

        # -- A guide used by both inputs was only copied once
        guide_copies = dict(zip(mirrored_from._guides(), copies))
        for input_name in _GUIDES:
            guide = mirrored_from.input(input_name).get()
            if guide:
                self.input(input_name).set(guide_copies[guide])

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        Restores the Create Joints option so this component's data matches
        the original, and reflects the pivot guide curve's cvs. The mirror
        pass mirrors the curve's transform as it would a joint, which turns
        the curve's shape around, so its cvs are set to the reflection of the
        original's (in world space, across the YZ plane).
        """
        self.option("Create Joints").set(mirrored_from.option("Create Joints").get(resolved=False))

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
