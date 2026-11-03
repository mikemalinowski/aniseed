"""
Provides the SoftIkConnection class, which applies soft ik (with stretch) to
a two bone ik chain by driving the translateX of its second and third joints.
It is built entirely from standard Maya nodes.

With a chain of length L (the bone lengths plus their additions), a distance
d from the root to the target and a soft distance s, the soft zone starts at
L - s. Beyond that point the distance the chain reaches is eased towards L
rather than hitting it:

    soft_distance = (L - s) + s * (1 - e^(-(d - (L - s)) / s))

and each bone is scaled by d / soft_distance, blended by the Stretch
attribute. Inside the soft zone the bones keep their rest length (plus their
addition).
"""
import math

from maya import cmds

import mref
import aniseed_utilities as au


# -- floatMath operations
_ADD = 0
_SUBTRACT = 1
_MULTIPLY = 2
_DIVIDE = 3
_POWER = 6

# -- condition operations
_GREATER_THAN = 2


class SoftIkConnection:
    """
    Applies soft ik to a two bone chain.

    The following attributes are added to the host:
        UpperAddition / LowerAddition: Added to each bone's length
        Stretch: How much the bones stretch beyond the soft zone (0-1)
        SoftDistance: The size of the soft zone at the end of the chain's reach
        DefaultUpperLength / DefaultLowerLength: The rest bone lengths
        root_matrix / target_matrix: The world matrices of the root and target

    Args:
        root: A node representing the root of the chain
        target: A node representing the ik target
        second_joint: The second joint of the chain
        third_joint: The third (end) joint of the chain
        host: The node to add the soft ik attributes to. A network node is
            created if this is not given.
        config: Optional aniseed rig configuration. If given, every node is
            named with it (mechanical, "<prefix>SoftIk<label>"), otherwise
            the nodes keep maya's default names.
        prefix: Placed in front of the description of every node name
        location: The location token (config.left, config.middle etc)

    Usage:
        SoftIkConnection(ik_root, ik_target, elbow, wrist, host=ik_target).build()
    """

    def __init__(self, root, target, second_joint, third_joint, host=None, config=None, prefix="", location=""):
        self.root = mref.get(root)
        self.target = mref.get(target)
        self.second_joint = mref.get(second_joint)
        self.third_joint = mref.get(third_joint)
        self.host = mref.get(host) if host else None
        self.config = config
        self.location = location

        # -- "arm" becomes "Arm" so it reads as part of a camel cased description
        self.prefix = prefix[:1].upper() + prefix[1:]

    def build(self) -> "SoftIkConnection":
        """
        Adds the attributes to the host and builds the soft ik network

        Returns:
            This instance
        """
        # -- floatMath comes from the lookdevKit plugin
        if not cmds.pluginInfo("lookdevKit", query=True, loaded=True):
            cmds.loadPlugin("lookdevKit", quiet=True)

        if not self.host:
            self.host = self._create("network", "Host")

        self._add_attributes()

        upper = self._float_math(_ADD, self._attr("DefaultUpperLength"), self._attr("UpperAddition"))
        lower = self._float_math(_ADD, self._attr("DefaultLowerLength"), self._attr("LowerAddition"))
        chain_length = self._float_math(_ADD, upper, lower)
        soft_start = self._float_math(_SUBTRACT, chain_length, self._attr("SoftDistance"))

        distance = self._create("distanceBetween", "Distance")
        self._attr("root_matrix").connect(distance.attr("inMatrix1"))
        self._attr("target_matrix").connect(distance.attr("inMatrix2"))
        distance = distance.attr("distance")

        scale = self._soft_scale(distance, soft_start)

        # -- Beyond the start of the soft zone the bones are scaled, before
        # -- it they keep their length
        condition = self._create("condition", "InSoftZone")
        condition.attr("operation").set(_GREATER_THAN)
        distance.connect(condition.attr("firstTerm"))
        soft_start.connect(condition.attr("secondTerm"))

        for channel, default_length, addition, joint in [
            ("R", "DefaultUpperLength", "UpperAddition", self.second_joint),
            ("G", "DefaultLowerLength", "LowerAddition", self.third_joint),
        ]:
            rigid = upper if channel == "R" else lower
            rigid.connect(condition.attr(f"colorIfFalse{channel}"))

            stretched = self._stretched_length(self._attr(default_length), self._attr(addition), scale)
            stretched.connect(condition.attr(f"colorIfTrue{channel}"))

            self._drive_translate_x(condition.attr(f"outColor{channel}"), joint)

        return self

    def _attr(self, name: str) -> mref.ReferencedItem:
        return self.host.attr(name)

    def _create(self, node_type: str, label: str) -> mref.ReferencedItem:
        """
        Creates a node, named for the label if there is a config
        """
        if not self.config:
            return mref.create(node_type)

        return mref.create(
            node_type,
            name=self.config.generate_name(
                classification=self.config.mechanical,
                description=f"{self.prefix}SoftIk{label}",
                location=self.location,
            ),
        )

    def _add_attributes(self):
        """
        Adds the soft ik attributes to the host. The default lengths are
        read from the joints and are not keyable.
        """
        au.core.attributes.add_separator(self.host.full_name())

        for name, value in [
            ("UpperAddition", 0),
            ("LowerAddition", 0),
            ("DefaultUpperLength", abs(self.second_joint.attr("translateX").get())),
            ("DefaultLowerLength", abs(self.third_joint.attr("translateX").get())),
            ("Stretch", 1),
            ("SoftDistance", 0),
        ]:
            self.host.add_attribute(
                name,
                value=None,
                attribute_type="float",
                keyable="Default" not in name,
                defaultValue=value,
            )

        for name, node in [("root_matrix", self.root), ("target_matrix", self.target)]:
            mref.addAttr(self.host.full_name(), shortName=name, attributeType="matrix")
            node.attr("worldMatrix[0]").connect(self._attr(name))

    def _soft_scale(self, distance, soft_start) -> mref.ReferencedItem:
        """
        Returns the plug for d / soft_distance, the amount to scale the bones
        by once the distance is in the soft zone
        """
        soft_distance = self._attr("SoftDistance")

        # -- e^(-(d - soft_start) / s)
        into_zone = self._float_math(_SUBTRACT, distance, soft_start)
        exponent = self._float_math(_DIVIDE, into_zone, soft_distance)
        exponent = self._float_math(_MULTIPLY, exponent, -1)
        falloff = self._float_math(_POWER, math.e, exponent)

        # -- soft_start + s * (1 - falloff)
        eased = self._float_math(_SUBTRACT, 1, falloff)
        eased = self._float_math(_MULTIPLY, eased, soft_distance)
        eased = self._float_math(_ADD, eased, soft_start)

        return self._float_math(_DIVIDE, distance, eased)

    def _stretched_length(self, default_length, addition, scale) -> mref.ReferencedItem:
        """
        Returns the plug for a bone's length in the soft zone:

            ((default * scale) - default) * Stretch + default + addition
        """
        length = self._float_math(_MULTIPLY, default_length, scale)
        length = self._float_math(_SUBTRACT, length, default_length)
        length = self._float_math(_MULTIPLY, length, self._attr("Stretch"))
        length = self._float_math(_ADD, length, default_length)
        return self._float_math(_ADD, length, addition)

    def _drive_translate_x(self, length, joint: mref.ReferencedItem):
        """
        Drives the joint's translateX by the length, keeping the sign of its
        rest translateX so chains which point down negative x keep doing so
        """
        if joint.attr("translateX").get() < 0:
            length = self._float_math(_MULTIPLY, length, -1)
        length.connect(joint.attr("translateX"))

    def _float_math(self, operation: int, first_term, second_term) -> mref.ReferencedItem:
        """
        Creates a floatMath node, connecting (plugs) or setting (numbers) its
        inputs, and returns its output plug
        """
        node = self._create("floatMath", "Math")
        node.attr("operation").set(operation)

        for term, plug in [(first_term, node.attr("floatA")), (second_term, node.attr("floatB"))]:
            if isinstance(term, (int, float)):
                plug.set(term)
            else:
                mref.get(term).connect(plug)

        return node.attr("outFloat")
