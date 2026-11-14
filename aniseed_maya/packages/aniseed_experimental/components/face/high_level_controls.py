"""
Provides the "Face : High Level Controls" component, which builds the
animator facing facial controls (lip corners, central lips, nose, brows and
blinks) and wires them into the pose attributes of a matrix mixer, using
aniseed_standard.rigging.facial.FacialControlRig. It also proxies the eye
controls' attributes onto the attribute host.

The "Limb : Modular Face" component adds one of these beneath itself, but it
can drive any mixer which has poses of the expected names (see POSE_NAMES).
"""
import logging

import mref
import aniseed
from aniseed_standard import rigging

log = logging.getLogger(__name__)


# -- The poses the controls drive, as the "Limb : Face" component builds them
POSE_NAMES = [
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
    "left_lip_sneer_lower",
    "left_lip_sneer_upper",
    "right_lip_sneer_lower",
    "right_lip_sneer_upper",
    "upper_sneer",
    "lower_sneer",
    "left_cheek_suck",
    "left_cheek_blow",
    "right_cheek_suck",
    "right_cheek_blow",
    "left_nose_flare",
    "right_nose_flare",
    "left_squint_inner",
    "left_squint_outer",
    "right_squint_inner",
    "right_squint_outer",
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
    "jaw_open",
    "left_blink",
    "right_blink",
]

# -- The high level controls. Each can be given a pre-made control, a
# -- parent, a guide (to place a created control) and a shape.
CONTROL_GROUPS = [
    "left_lip_corner",
    "right_lip_corner",
    "upper_lip",
    "lower_lip",
    "nose",
    "left_brow_inner",
    "left_brow_outer",
    "right_brow_inner",
    "right_brow_outer",
]

CONTROL_GROUP_PARTS = ["control", "parent", "guide", "shape"]

SIDES = ["left", "right"]


class FaceHighLevelControls(aniseed.RigComponent):
    """
    Builds the high level facial controls, which drive the pose attributes of
    the given mixer node. A pose the mixer does not have is reported, and its
    control is wired into a placeholder attribute instead, so poses can be
    removed from the mixer without breaking the build.
    """

    identifier = "Face : High Level Controls"

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, attribute host, mixer, jaw and eye control
        inputs, and the control, parent, guide and shape inputs of each
        control group.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The node created controls are parented under, unless their group gives a parent",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Attribute Host",
            description="The node every animator facing attribute is proxied onto",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Mixer",
            description="The matrix mixer node whose pose attributes the controls drive",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Jaw Control",
            description="The jaw control, which blends the lip corner push in",
            validate=True,
            group="Controls",
        )

        for side in SIDES:
            self.declare_input(
                name=f"{side.title()} Eye Control",
                description=f"The {side} eye control, which is given the {side} blink attribute",
                validate=True,
                group="Controls",
            )

        for control_label in CONTROL_GROUPS:
            group = "Control : %s" % control_label.replace("_", " ").title()

            for part in CONTROL_GROUP_PARTS:
                self.declare_input(
                    name=f"{control_label}_{part}",
                    value="",
                    group=group,
                    validate=False,
                )

    def input_widget(self, requirement_name: str):
        """
        Returns a shape selector for the "_shape" inputs and an object
        selector for every other input.
        """
        if requirement_name.endswith("_shape"):
            return aniseed.widgets.ShapeSelector(default_item="core_cube")

        return aniseed.widgets.ObjectSelector(component=self)

    def is_valid(self) -> bool:
        """
        Checks that the mixer node exists, if it is not given by another
        component's output (which only exists once that has built).
        """
        mixer = self.input("Mixer")
        if not mixer.is_address() and not mref.objExists(mixer.get()):
            log.warning(f"{self.label()} : The Mixer ({mixer.get()}) does not exist")
            return False

        return True

    def run(self) -> bool:
        """
        Builds the controls in the order "Limb : Face" does (the order sets
        the plusMinusAverage array indices), then proxies the eye controls'
        channel box attributes onto the attribute host.
        """
        parent = self.input("Parent").get()
        attribute_host = mref.get(self.input("Attribute Host").get())
        jaw = mref.get(self.input("Jaw Control").get())

        control_rig = rigging.facial.FacialControlRig(
            config=self.config,
            read_setting=lambda name: self.input(name).get(),
            attribute_host=attribute_host,
            description_prefix="Facial",
            multiply_sneers=True,
        )

        connection_map = control_rig.initialise_driving_adds(self._pose_attributes())

        attribute_host.add_separator_attribute()
        for side in SIDES:
            control_rig.setup_lip_puller(
                location=side,
                guide=self.input(f"{side}_lip_corner_guide").get(),
                parent=parent,
                connection_map=connection_map,
                jaw=jaw,
            )

        attribute_host.add_separator_attribute()
        for section in ["upper", "lower"]:
            control_rig.setup_central_lip(
                section=section,
                guide=self.input(f"{section}_lip_guide").get(),
                parent=parent,
                connection_map=connection_map,
            )

        attribute_host.add_separator_attribute()
        control_rig.setup_nose(
            guide=self.input("nose_guide").get(),
            parent=parent,
            connection_map=connection_map,
        )

        for side in SIDES:
            attribute_host.add_separator_attribute()

            control_rig.setup_inner_brow(
                location=side,
                guide=self.input(f"{side}_brow_inner_guide").get(),
                parent=parent,
                connection_map=connection_map,
            )
            control_rig.setup_outer_brow(
                location=side,
                guide=self.input(f"{side}_brow_outer_guide").get(),
                parent=parent,
                connection_map=connection_map,
            )
            control_rig.setup_eye(
                location=side,
                control=mref.get(self.input(f"{side.title()} Eye Control").get()),
                connection_map=connection_map,
            )

        self._proxy_eye_attributes(attribute_host)
        return True

    def _pose_attributes(self) -> dict:
        """
        Returns the mixer's attribute for each pose in POSE_NAMES. A pose the
        mixer does not have is given an attribute on a placeholder node, so
        its control still builds but drives nothing.
        """
        mixer = mref.get(self.input("Mixer").get())
        placeholder = None
        attributes = dict()

        for pose_name in POSE_NAMES:
            if mixer.has_attribute(pose_name):
                attributes[pose_name] = mixer.attr(pose_name)
                continue

            log.warning(f"{self.label()} : The mixer has no {pose_name} pose, so its control drives nothing")

            if not placeholder:
                placeholder = mref.create(
                    "transform",
                    name=self.config.generate_name(
                        classification=self.config.mechanical,
                        description="FacialMissingPoses",
                        location=self.config.middle,
                    ),
                    parent=mixer.parent(),
                )

            attributes[pose_name] = placeholder.add_attribute(pose_name, value=0.0, attribute_type="float")

        return attributes

    def _proxy_eye_attributes(self, attribute_host):
        """
        Proxies the channel box attributes of each eye control onto the
        attribute host, prefixed with the side. Only what the animator sees
        in the channel box is proxied, which skips the control's internal
        metadata (with which duplicating the host, as Studio Library does
        when saving animation, crashes Maya).
        """
        for side in SIDES:
            eye_control = mref.get(self.input(f"{side.title()} Eye Control").get())

            attribute_host.add_separator_attribute()
            for attribute in eye_control.attributes(userDefined=True):

                # -- Skip separator attributes
                if not attribute.name(include_node=False).replace("_", ""):
                    continue

                if not attribute.is_in_channel_box():
                    continue

                # -- Such as the blink, which setup_eye has already exposed
                proxy_name = f"{side}_" + attribute.name(include_node=False)
                if attribute_host.has_attribute(proxy_name):
                    continue

                try:
                    attribute_host.add_proxy(proxy_name, attribute)
                except RuntimeError:
                    log.warning(f"{self.label()} : Could not proxy {attribute.name()} onto the attribute host")
