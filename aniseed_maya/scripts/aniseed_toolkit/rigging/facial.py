"""
Shared builder for the high level, animator facing facial controls. These
controls drive a set of pose/shape attributes (transform mixer poses or
blendshape weights) through clamps and math nodes.

Used by the "Limb : Face" and "TPS : BlendShape Based Facial Rig" components.

Note: the order in which nodes are created here decides the default names of
the utility nodes (clamp1, floatMath2...) and the order of the setup calls
decides the plusMinusAverage array indices, so both must be preserved.
"""
import typing

import mref

from ..core import attributes as _attributes
from ..rig import control as _control


class FacialControlRig:
    """
    Creates the high level facial controls and wires them into the given
    connection map (a dictionary of pose label to plusMinusAverage.input1D
    attribute, as returned by initialise_driving_adds).

    Args:
        config: The aniseed rig configuration used for naming
        read_setting: Callable taking a setting name (such as "nose_control")
            and returning its value. This lets components store the per
            control settings as either inputs or options.
        attribute_host: If given, every animator facing attribute which is
            created is also exposed as a proxy attribute on this node.
        description_prefix: Prefixed onto the description of every control
            which is created.
        multiply_sneers: If True the central lip sneer fixup is driven by
            multiplying the left and right sneers, otherwise by averaging them.
    """

    def __init__(
            self,
            config,
            read_setting: typing.Callable[[str], typing.Any],
            attribute_host: mref.ReferencedItem = None,
            description_prefix: str = "",
            multiply_sneers: bool = False,
    ):
        self.config = config
        self.read_setting = read_setting
        self.attribute_host = attribute_host
        self.description_prefix = description_prefix
        self.multiply_sneers = multiply_sneers

    @staticmethod
    def initialise_driving_adds(attribute_dictionary: dict) -> dict:
        """
        Each pose can have multiple inputs. To ensure that we can reliably
        drive each pose by multiple mechanical approaches we add a
        plusMinusAverage node which drives the attribute.

        Args:
            attribute_dictionary: Dictionary of pose label to the attribute
                which drives that pose

        Returns:
            Dictionary of pose label to the input1D attribute of the
            plusMinusAverage node driving that pose
        """
        driving_additions = dict()

        for label, attribute in attribute_dictionary.items():
            node = mref.create("plusMinusAverage")
            node.attr("output1D").connect(attribute)

            driving_additions[label] = node.attr("input1D")

        return driving_additions

    def resolve_control(
            self,
            description,
            identity_label,
            location,
            parent,
            guide,
            lock_and_hide=None,
    ) -> mref.ReferencedItem:
        """
        We allow the user to specify a control directly, or to allow us to create
        it as part of the rig build. This function will return the existing control
        if one has been specified, otherwise it will generate a new one.
        """
        # -- If the user has specified a control then we use that rather
        # -- than create one.
        control_name = self.read_setting(f"{identity_label}_control")
        if control_name:
            return mref.get(control_name)

        # -- To reach here we need to construct a new control
        new_control_setup = _control.create(
            description=self.description_prefix + description,
            location=location,
            parent=self.read_setting(f"{identity_label}_parent") or parent,
            shape=self.read_setting(f"{identity_label}_shape") or "core_cube",
            config=self.config,
            match_to=guide or None,
        )

        # -- Lock and hide any attributes that should not be animatable.
        if lock_and_hide:
            _attributes.lock_and_hide(
                [new_control_setup.ctl],
                lock_and_hide,
                lock=True,
                hide=True,
            )

        return mref.get(new_control_setup.ctl)

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    @staticmethod
    def clamped_connection(
            driving_attribute,
            destination_attribute,
            clamp_min=0,
            clamp_max=1,
            do_next=True,
    ) -> dict:
        """
        This will connect the driving attribute to the destination attribute
        but with a clamp in between set to the given values. If do_next is
        True the destination is treated as an array attribute and the next
        free element is used.
        """
        # -- Create and setup the clamp node
        clamp = mref.create("clamp")
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)

        # -- Hook up the connections
        driving_attribute.connect(clamp.attr("inputR"))

        if do_next:
            clamp.attr("outputR").connect_next(destination_attribute)
        else:
            clamp.attr("outputR").connect(destination_attribute)

        # -- Return a dictionary for a consistent return type across all the
        # -- connection methods (some of which create multiple nodes).
        return {
            "clamp": clamp,
        }

    @staticmethod
    def clamped_reversal(
            driving_attribute,
            destination_attribute,
            clamp_min=0,
            clamp_max=1,
    ) -> dict:
        """
        This will connect the driving attribute to the destination attribute
        but with a reversal (*-1) and then clamping that result to the given
        clamp values.
        """
        clamp = mref.create("clamp")
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)

        # -- Setup the inversion node
        inverse = mref.create("floatMath")
        inverse.attr("operation").set(2)  # -- Multiply
        inverse.attr("floatB").set(-1)

        # -- Hook up the connections
        driving_attribute.connect(inverse.attr("floatA"))
        inverse.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

        return {
            "clamp": clamp,
            "multiplier": inverse,
        }

    def animator_attribute(self, control: mref.ReferencedItem, label, proxy_prefix=""):
        """
        Returns the animator facing float attribute with the given label on
        the control, creating it (and its proxy on the attribute host, if
        there is one) if it does not already exist.
        """
        if control.has_attribute(label):
            return control.attr(label)

        attribute = control.add_attribute(
            label,
            value=0,
            attribute_type="float",
            keyable=True,
        )

        if self.attribute_host is not None:
            proxy_name = attribute.name(include_node=False)
            if proxy_prefix:
                proxy_name = f"{proxy_prefix}_{proxy_name}"
            self.attribute_host.add_proxy(proxy_name, attribute)

        return attribute

    def expose_direct(
            self,
            control: mref.ReferencedItem,
            label,
            destination_attribute,
            clamp_min=0,
            clamp_max=1,
            do_next=True,
            proxy_prefix="",
    ) -> dict:
        """
        This will expose the attribute on the control, allowing the animator to drive
        it directly.
        """
        return self.clamped_connection(
            driving_attribute=self.animator_attribute(control, label, proxy_prefix),
            destination_attribute=destination_attribute,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
            do_next=do_next,
        )

    def expose_reversal_direct(
            self,
            control: mref.ReferencedItem,
            label,
            destination_attribute,
            clamp_min=0,
            clamp_max=1,
            proxy_prefix="",
    ) -> dict:
        """
        This will expose the given destination attribute up to the control
        but it will also reverse the value and clamp it.
        """
        return self.clamped_reversal(
            driving_attribute=self.animator_attribute(control, label, proxy_prefix),
            destination_attribute=destination_attribute,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )

    # ------------------------------------------------------------------
    # Control setups
    # ------------------------------------------------------------------
    def setup_lip_puller(self, location, guide, parent, connection_map, jaw=None):
        """
        This will create the control for the lip pullers (left and right). If
        a jaw is given then the push in is also blended against the jaw opening
        to drive the {location}_lip_corner_push_in_jaw_open pose.
        """
        control = self.resolve_control(
            description="lip_puller",
            identity_label=f"{location}_lip_corner",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tz"],
        )

        if jaw is not None:
            # -- Multiply the jaw rotation against the inverted pull in
            multiply_jaw = mref.create("floatMath")
            multiply_jaw.attr("operation").set(2)  # -- Multiply
            multiply_jaw.attr("floatB").set(1.0 / 25)
            jaw.attr("rotateX").connect(multiply_jaw.attr("floatA"))

            multiply_inverter = mref.create("floatMath")
            multiply_inverter.attr("operation").set(2)  # -- Multiply
            multiply_inverter.attr("floatA").set(-1.0)
            control.attr("translateX").connect(multiply_inverter.attr("floatB"))

            multiply_mix = mref.create("floatMath")
            multiply_mix.attr("operation").set(2)  # -- Multiply
            multiply_jaw.attr("outFloat").connect(multiply_mix.attr("floatA"))
            multiply_inverter.attr("outFloat").connect(multiply_mix.attr("floatB"))

            self.clamped_connection(
                driving_attribute=multiply_mix.attr("outFloat"),
                destination_attribute=connection_map[f"{location}_lip_corner_push_in_jaw_open"],
            )

        # -- Pull Out Behaviour
        self.clamped_connection(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_out"],
        )

        # -- Push In Behaviour
        self.clamped_reversal(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_lip_corner_push_in"],
        )

        # -- Pull Down Behaviour
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_down"],
        )

        # -- Pull Up Behaviour
        corner_pull_up_setup = self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_up"],
        )

        # -- Now add the squint
        remap_node = mref.create("remapValue")
        corner_pull_up_setup["clamp"].attr("outputR").connect(remap_node.attr("inputValue"))
        remap_node.attr("inputMax").set(1)
        remap_node.attr("value[0].value_Position").set(0.25)
        remap_node.attr("value[0].value_FloatValue").set(0)
        remap_node.attr("value[0].value_Interp").set(2)  # -- Smooth
        remap_node.attr("value[1].value_Position").set(1)
        remap_node.attr("value[1].value_FloatValue").set(0.25)
        remap_node.attr("outValue").connect_next(connection_map[f"{location}_squint_outer"])

        # -- Set up our direct connections
        self.expose_direct(
            control=control,
            label="Blow",
            destination_attribute=connection_map[f"{location}_cheek_blow"],
            proxy_prefix=location,
        )
        self.expose_reversal_direct(
            control=control,
            label="Blow",
            destination_attribute=connection_map[f"{location}_cheek_suck"],
            proxy_prefix=location,
        )

    def setup_central_lip(self, section, guide, parent, connection_map):
        """
        This sets up the control connections for the central lip (either upper
        or lower)

        Args:
            section: lower or upper
            guide: guide to denote the location/transformation of the control
            parent: parent for the control
            connection_map: A dictionary of labels where the value is the
                attribute it represents.
        """
        control = self.resolve_control(
            description=f"{section}_lip",
            identity_label=f"{section}_lip",
            location=self.config.middle,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tx"],
        )

        # -- Hook up our transformation connections
        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{section}_lip_pull"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{section}_lip_compress"],
        )
        self.clamped_connection(
            driving_attribute=control.attr("translateZ"),
            destination_attribute=connection_map[f"{section}_lip_curl_out"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateZ"),
            destination_attribute=connection_map[f"{section}_lip_curl_in"],
        )

        # -- Hook up our animator facing attributes
        self.expose_direct(
            control=control,
            label="right_sneer",
            destination_attribute=connection_map[f"right_lip_sneer_{section}"],
            clamp_min=-1,
            proxy_prefix=section,
        )
        self.expose_direct(
            control=control,
            label="left_sneer",
            destination_attribute=connection_map[f"left_lip_sneer_{section}"],
            clamp_min=-1,
            proxy_prefix=section,
        )

        # -- Set up the sneering fixer - this resolves the middle of the lips
        # -- when both sneers are dialed in
        if self.multiply_sneers:
            combined_sneers = mref.create("floatMath")
            combined_sneers.attr("operation").set(2)  # -- Multiply
            control.attr("right_sneer").connect(combined_sneers.attr("floatA"))
            control.attr("left_sneer").connect(combined_sneers.attr("floatB"))

        else:
            add_sneers = mref.create("floatMath")
            control.attr("right_sneer").connect(add_sneers.attr("floatA"))
            control.attr("left_sneer").connect(add_sneers.attr("floatB"))

            # -- As we're blending two float tracks we divide it in two.
            combined_sneers = mref.create("floatMath")
            combined_sneers.attr("operation").set(2)  # -- Multiply
            combined_sneers.attr("floatB").set(0.5)
            add_sneers.attr("outFloat").connect(combined_sneers.attr("floatA"))

        # -- As well as dialing it in automatically we also want to expose
        # -- it as a direct animatable attribute.
        add_direct = mref.create("floatMath")
        combined_sneers.attr("outFloat").connect(add_direct.attr("floatA"))

        self.expose_direct(
            control=control,
            label="sneer_fixup",
            destination_attribute=add_direct.attr("floatB"),
            clamp_min=-1,
            clamp_max=1,
            do_next=False,
            proxy_prefix=section,
        )

        # -- Ensure the result is always clamped.
        clamp = mref.create("clamp")
        clamp.attr("minR").set(-1)
        clamp.attr("maxR").set(1)
        add_direct.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(connection_map[f"{section}_sneer"])

    def setup_nose(self, guide, parent, connection_map):
        """
        This sets up the control connections for the nose control
        """
        control = self.resolve_control(
            description="nose",
            identity_label="nose",
            location=self.config.middle,
            parent=parent,
            guide=guide,
        )

        # -- Expose the direct animator facing controls
        for label in ["left_nose_flare", "right_nose_flare"]:
            self.expose_direct(
                control=control,
                label=label,
                destination_attribute=connection_map[label],
            )

    def setup_inner_brow(self, location, guide, parent, connection_map):
        """
        This sets up the control connections for the inner eye brow.
        """
        control = self.resolve_control(
            description="brow_inner",
            identity_label=f"{location}_brow_inner",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tz"],
        )

        # -- Hook up the transformation connections
        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_inner_up"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_inner_down"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_brow_inner_in"],
            clamp_min=-1,
        )

        # -- Hook up the animator-facing direct controls
        self.expose_direct(
            control=control,
            label="mid_brow",
            destination_attribute=connection_map[f"{location}_brow_mid_up"],
            proxy_prefix=location,
        )
        self.expose_reversal_direct(
            control=control,
            label="mid_brow",
            destination_attribute=connection_map[f"{location}_brow_mid_down"],
            proxy_prefix=location,
        )

    def setup_outer_brow(self, location, guide, parent, connection_map):
        """
        This will create the control for the outer brows (left and right)
        """
        control = self.resolve_control(
            description="brow_outer",
            identity_label=f"{location}_brow_outer",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tx", "tz"],
        )

        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_outer_up"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_outer_down"],
        )

        for label in ["squint_inner", "squint_outer"]:
            self.expose_direct(
                control=control,
                label=label,
                destination_attribute=connection_map[f"{location}_{label}"],
                proxy_prefix=location,
            )

    def setup_eye(self, location, control, connection_map):
        """
        Exposes the blink attribute on the given eye control
        """
        self.expose_direct(
            control=control,
            label="blink",
            destination_attribute=connection_map[f"{location}_blink"],
            proxy_prefix=location,
        )
