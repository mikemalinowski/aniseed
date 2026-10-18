"""
Provides the "Limb : Hand" component, which builds a hand control with fk
finger and thumb controls driven from the hand joint and finger/thumb tip
inputs, with optional metacarpals. It adds hand level attributes (such as
spread) weighted per finger, can generate and remove the hand skeleton and
supports mirroring.
"""
import os
import mref
import aniseed
import aniseed_toolkit


class HandComponent(aniseed.RigComponent, aniseed.mixins.MirrorMixin):
    identifier = "Limb : Hand"
    icon = os.path.join(
        os.path.dirname(__file__),
        "hand.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, hand joint, finger tips and thumb tip inputs, the
        naming options (prefix, location, finger and thumb labels), the
        metacarpal, digit count and attribute exposure behaviour options and
        the joint creation options. The single (default) output is the hand.
        """
        super(HandComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value=None,
            validate=False,
            group="Control Rig",
        )

        self.declare_input(
            name="Hand Joint",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Finger Tips",
            value=list(),
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Thumb Tip",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_option(
            name='Descriptive Prefix',
            value="",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="lf",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )
        self.declare_option(
            name="Finger Labels",
            value=[
                "index",
                "middle",
                "ring",
                "pinky",
            ],
            group="Naming",
            pre_expose=True,
        )
        self.declare_option(
            name="Thumb Label",
            value="thumb",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Use Metacarpals",
            value=True,
            group="Behaviour",
            description="If True, the component will assume that there is an additional bone which acts as the metacarpals.",
            pre_expose=True,
        )

        self.declare_option(
            name="Digit Count",
            value=3,
            group="Behaviour",
            description="How many joints (excluding the metacarpal) make up the finger.",
            pre_expose=True,
        )
        self.declare_option(
            name="Expose Attributes To Nodes",
            value=[],
            group="Behaviour",
        )

        self.declare_option(
            name="Create Joints",
            value=True,
            pre_expose=True,
            group="Creation",
        )

        self.declare_option(
            name="Omit Hand Joint",
            value=False,
            pre_expose=True,
            group="Creation",
        )

        self.declare_output("Hand", is_default=True)

    def on_enter_stack(self):
        """
        When the user adds this component to the stack, build the skeleton for them
        if they want to.
        """
        if self.option("Create Joints").get():
            self.user_func_create_skeleton()

        self.option("Omit Hand Joint").set_hidden(True)
        self.option("Create Joints").set_hidden(True)

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we need to remove the
        bones too.
        """
        # -- Remove the joints (re-parenting any children)
        new_parent = mref.get(self.input("Hand Joint").get()).parent()
        aniseed_toolkit.scene.joints.reparent_unknown_children(self.all_joints(), new_parent)

        # -- Now delete our joints
        mref.delete(self.all_joints())

    def input_widget(self, requirement_name: str):
        """
        Return bespoke widgets for specific inputs
        """
        if requirement_name in ["Finger Tips"]:
            return aniseed.widgets.ObjectList()

        if requirement_name in ["Parent", "Hand Joint", "Thumb Tip"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        """
        Return bespoke widgets for specific options
        """
        if option_name == "Expose Attributes To Nodes":
            return aniseed.widgets.ObjectList()

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

        if option_name == "Finger Labels":
            return aniseed.widgets.TextList()

    def user_functions(self):
        """
        This exposes various bits of functionality to the user
        """
        menu = super(HandComponent, self).user_functions()

        if not self.input("Hand Joint").get():
            menu["Create Joints"] = self.user_func_create_skeleton

        return menu

    def is_valid(self):
        """
        Check whether we have all the inputs we require in order to build
        """
        finger_tips = self.input("Finger Tips").get() or list()
        thumb_tip = self.input("Thumb Tip").get()

        if not len(finger_tips) > 0:
            print("You must specify at least one finger")
            return False

        if not thumb_tip:
            print("You must specify a thumb")
            return False

        finger_depth = self.option("Digit Count").get()

        for finger_tip in finger_tips:
            if not self.get_parent(finger_tip, parent_index=finger_depth - 1):
                print(f"{finger_tip} does not have {finger_depth} joints")
                return False

        return True

    def run(self):
        """
        This is triggered when the component is executed.
        """
        # -- Read our input data
        hand_joint = self.input("Hand Joint").get()
        finger_tips = self.input("Finger Tips").get() or list()
        thumb_tip = self.input("Thumb Tip").get()

        # -- Read our option data
        location = self.option("Location").get()
        finger_depth = self.option("Digit Count").get()
        proxy_to = self.option("Expose Attributes To Nodes").get()

        # -- This is the default rotation of our shapes based on X down the chain.
        # -- Note: this is switched (for this and all subsequent fingers) the
        # -- first time a finger is found to face down negative X.
        shape_rotation = [90, 90, 0]

        # -- Create our hand control
        hand = aniseed_toolkit.rig.control.create(
            description=f"{self.option('Descriptive Prefix').get()}Hand",
            location=location,
            parent=self.input("Parent").get(),
            shape="core_arrow_handle",
            config=self.config,
            match_to=hand_joint,
            shape_scale=45.0,
            rotate_shape=[0, -90, 0],
        )

        # -- Clear any constraints on the hand
        aniseed_toolkit.scene.constraints.remove_all(nodes=[hand_joint])

        # -- Constrain the hand bone to the hand control and set the output
        aniseed_toolkit.scene.constraints.parent_and_scale(hand.ctl, hand_joint, maintain_offset=False)
        self.output("Hand").set(hand.ctl)

        # -- Start adding our custom attributes
        aniseed_toolkit.core.attributes.add_separator(hand.ctl)

        # -- Add our finger control attributes
        finger_visibility = mref.get(hand.ctl).add_attribute(
            "finger_visibility",
            value=None,
            attribute_type="bool",
            defaultValue=1,
            keyable=False,
        )
        finger_visibility.set(channelBox=True)

        curl_attr = self._add_multiplied_attr(hand.ctl, "curl", 90, min=-0.25, proxy_to=proxy_to)
        spread_attr = self._add_multiplied_attr(hand.ctl, "spread", 90, proxy_to=proxy_to)
        cup_attr = self._add_multiplied_attr(hand.ctl, "cup", 90, proxy_to=proxy_to)

        finger_index_excluding_thumb = -1

        # -- Whilst we do need to treat the thumb a little differently
        # -- there is also a lot that is the same. Thus we use the same
        # -- iteration to deal with them all
        all_tips_including_thumb = finger_tips[:]
        all_tips_including_thumb.append(thumb_tip)

        # -- Get a list of all the finger labels as well as the thumb label
        finger_labels = self.option("Finger Labels").get()
        finger_labels.append(self.option("Thumb Label").get())

        # -- We now cycle over all the fingers (and thumb)
        for finger_idx, finger_tip in enumerate(all_tips_including_thumb):

            # -- Determine if this is a thumb
            is_thumb = finger_idx == len(all_tips_including_thumb) - 1

            # -- This will get the root bone of the finger from the tip
            # -- bone which we're given.
            finger_root = self.get_parent(finger_tip, finger_depth - 1)

            # -- If this is not the thumb, increment this value - as we
            # -- use this variable to specifically track the number of
            # -- normal fingers.
            if finger_tip != thumb_tip:
                finger_index_excluding_thumb += 1

            # -- Get the full finger chain
            finger_joints = aniseed_toolkit.scene.joints.get_between(finger_root, finger_tip)

            # -- Determine the facing direction of the fingers so that we
            # -- can adjust the default controls if required.
            facing_dir = aniseed_toolkit.scene.joints.get_chain_facing_direction(
                finger_joints[-2],
                finger_joints[-1],
            )
            if facing_dir == facing_dir.NegativeX:
                shape_rotation = [0, 0, 90]

            # -- If the finger root is not a direct child of the hand then its
            # -- parent is a metacarpal bone. These give functionality like
            # -- spreading and cupping.
            m_metacarpal = mref.get(finger_root).parent()
            metacarpal = None

            if m_metacarpal.name() != hand_joint:

                # -- Multiple fingers can share a metacarpal, so if this
                # -- metacarpal is already driven then we use its control
                if m_metacarpal.constraints():
                    metacarpal = aniseed_toolkit.rig.control.get(
                        m_metacarpal.constraints()[0].drivers()[0].name(),
                    )

                else:
                    metacarpal = aniseed_toolkit.rig.control.create(
                        description=self.config.extract_description(m_metacarpal.name()),
                        location=location,
                        parent=hand.ctl,
                        shape="core_paddle",
                        config=self.config,
                        match_to=self.get_parent(finger_tip, finger_depth),
                        shape_scale=5.0,
                        rotate_shape=shape_rotation,
                    )

                    # -- Constrain the joint
                    aniseed_toolkit.scene.constraints.parent_and_scale(
                        metacarpal.ctl,
                        m_metacarpal,
                        maintain_offset=False,
                    )

            # -- The ranged value gives us a float denoting how much influence
            # -- this finger should get from features that spread etc.
            ranged_value = self._get_ranged_value(
                finger_index_excluding_thumb,
                finger_tips,
            )

            # -- Create the attribute for curling the individual finger
            finger_label = finger_labels[finger_idx]

            finger_curl_attribute = self._add_multiplied_attr(
                hand.ctl,
                f"{finger_label}_curl",
                90,
                min=-0.25,
                proxy_to=proxy_to,
            )

            # -- We're now going to create the fk hierarchy - so start by defining
            # -- the hand (or metacarpal) as the parent, and we will update this
            # -- as we go.
            control_parent = metacarpal.ctl if metacarpal else hand.ctl
            finger_controls = []

            # -- Cycle all the digits
            for finger_joint in finger_joints:

                finger_control = aniseed_toolkit.rig.control.create(
                    description=finger_label,
                    location=location,
                    parent=control_parent,
                    shape="core_paddle",
                    config=self.config,
                    match_to=finger_joint,
                    shape_scale=5.0,
                    rotate_shape=shape_rotation,
                )
                finger_controls.append(finger_control)

                # -- Connect the finger visibility
                finger_visibility.connect(
                    mref.get(finger_control.off).attr("visibility"),
                    force=True,
                )

                # -- Constrain the joint
                aniseed_toolkit.scene.constraints.parent_and_scale(
                    finger_control.ctl,
                    finger_joint,
                    maintain_offset=False,
                )

                control_parent = finger_control.ctl

            if is_thumb:
                self.setup_thumb(
                    finger_controls,
                    finger_curl_attribute,
                )
            else:
                self.setup_finger(
                    finger_controls,
                    metacarpal,
                    ranged_value,
                    cup_attr,
                    curl_attr,
                    spread_attr,
                    finger_curl_attribute,
                    is_last=finger_idx == len(all_tips_including_thumb) - 2
                )

    def setup_thumb(self, finger_controls, finger_curl_attribute):
        """
        Drives the curl of the thumb controls from the thumb curl attribute
        """
        for control in finger_controls:
            self._connect_with_inversion(
                [finger_curl_attribute],
                f"{control.off}.rotateZ",
                -0.333,
            )

    def setup_finger(self, finger_controls, metacarpal, ranged_value, cup_attr, curl_attr, spread_attr, finger_curl_attribute, is_last):
        """
        Drives the curl, cup and spread of the finger controls (and the
        metacarpal if there is one) from the hand attributes
        """
        # -- Setup the curl
        for control in finger_controls:
            self._connect_with_inversion(
                [curl_attr, finger_curl_attribute],
                f"{control.off}.rotateZ",
                -1,
            )

        # -- Do the cup
        cup_control = metacarpal or finger_controls[0]
        self._connect_with_inversion(
            [cup_attr, curl_attr],
            f"{cup_control.off}.rotateX",
            1,
            multiplier=ranged_value * 0.25,
        )

        # -- Setup the spread
        spread_factor = -0.4

        if metacarpal:
            spread_factor *= 0.5
            self._connect_with_inversion(
                [spread_attr],
                f"{metacarpal.off}.rotateY",
                1,
                multiplier=ranged_value * spread_factor,
            )

        if is_last:
            spread_factor *= 2

        self._connect_with_inversion(
            [spread_attr],
            f"{finger_controls[0].off}.rotateY",
            1,
            multiplier=ranged_value * spread_factor,
        )

    def get_parent(self, node: str, parent_index: int) -> str:
        """
        This will return the parent with the given index
        """
        while parent_index > 0 and node:
            node = mref.get(node).parent().name()
            parent_index -= 1
        return node

    def user_func_create_skeleton(self, parent=None):
        """
        This will generate a skeleton for us.
        """
        # -- Determine the parent for the hand bones
        parent = parent or aniseed_toolkit.core.selection.first_selected()

        # -- Get the finger labels
        omit_hand = self.option("Omit Hand Joint").get()
        finger_labels = self.option("Finger Labels").get()
        digit_count = self.option("Digit Count").get()
        use_metacarpals = self.option("Use Metacarpals").get()
        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        thumb_label = self.option("Thumb Label").get()

        if prefix:
            prefix += "_"

        # -- Create the hand bone (if we are omitting it, it is removed
        # -- once the fingers are built)
        hand = aniseed_toolkit.scene.joints.create(
            description=f"{prefix}hand",
            location=location,
            parent=parent,
            config=self.config,
        )
        spread = 5.0

        for finger_index, label in enumerate([thumb_label] + finger_labels):
            ranged_value = self._get_ranged_value(finger_index, finger_labels)

            # -- By default the parent for our digits will be the
            # -- hand
            digit_parent = hand
            planar_offset = aniseed_toolkit.core.units.to_cm(ranged_value * (spread / 4))

            # -- Before we build the finger digits, build the metacarpal if we
            # -- need to
            if finger_index and use_metacarpals:
                metacarpal = aniseed_toolkit.scene.joints.create(
                    description=f"{prefix}metacarpal_{label}",
                    location=location,
                    parent=hand,
                    config=self.config,
                )

                # -- Adjust the transform of the metacarpal
                m_metacarpal = mref.get(metacarpal)
                m_metacarpal.translateZ.set(planar_offset)
                m_metacarpal.translateX.set(aniseed_toolkit.core.units.to_cm(1))

                # -- Ensure the metacarpal is the parent of the subsequent
                # -- digits
                digit_parent = metacarpal

            # -- Now we can start building our digits
            for digit_index in range(digit_count):

                digit = aniseed_toolkit.scene.joints.create(
                    description=f"{prefix}finger_{label}",
                    location=location,
                    parent=digit_parent,
                    config=self.config,
                )
                m_digit = mref.get(digit)

                # -- Match just the translate to the parent
                m_digit.set_position(
                    mref.get(digit_parent).get_position(space="world"),
                    space="world",
                )

                length = aniseed_toolkit.core.units.to_cm(spread * 2 if not digit_index else spread)
                m_digit.translateX.set(length)

                if finger_index == 0:  # -- Thumb
                    m_digit.rotateX.set(90)

                if digit_index == 0:
                    if finger_index == 0:  # -- First thumb
                        m_digit.translateX.set(length / 2.0)
                        m_digit.translateZ.set(planar_offset * 1.6)
                        m_digit.translateY.set(-length * 0.25)

                    else:  # -- First Finger
                        m_digit.translateZ.set(planar_offset)

                # -- Mark this digit as the parent for the next digit
                digit_parent = digit

            # -- Ensure the last digits are added
            if finger_index:
                tips = self.input("Finger Tips").get()
                tips.append(digit)
                self.input("Finger Tips").set(tips)
            else:
                self.input("Thumb Tip").set(digit)

        # -- Snap the hand to the parent
        m_hand = mref.get(hand)
        m_hand.set_position(
            mref.get(parent).get_position(space="world"),
            space="world",
        )

        # -- If we're omitting the hand, then move its children to the
        # -- parent and remove it
        output_hand = hand
        if omit_hand:
            for child in m_hand.children():
                child.set_parent(parent)
            m_hand.delete()
            output_hand = parent

        # -- Now we set our inputs
        self.input("Hand Joint").set(output_hand)

    def _mirror_digit_joints(self) -> list:
        """
        Returns the joints of each digit (thumb first), each walked up from
        its tip to the hand joint (exclusive) and given root first. A joint
        shared between digits (such as a shared metacarpal) is only given
        once. If a tip is not below the hand joint, only its Digit Count
        joints (plus the metacarpal of a finger) are taken.
        """
        hand_joint = self.input("Hand Joint").get()
        thumb_tip = self.input("Thumb Tip").get()
        finger_tips = self.input("Finger Tips").get() or list()
        digit_count = self.option("Digit Count").get()
        use_metacarpals = self.option("Use Metacarpals").get()

        joints = []

        for tip in [thumb_tip] + finger_tips:
            if not tip or not mref.objExists(tip):
                continue

            digit = []
            node = tip
            while node and node != hand_joint:
                digit.insert(0, node)
                parent = mref.get(node).parent()
                node = parent.name() if parent else ""

            # -- The walk never reached the hand joint
            if not node:
                depth = digit_count
                if use_metacarpals and tip != thumb_tip:
                    depth += 1
                digit = digit[-depth:]

            joints.extend(joint for joint in digit if joint not in joints)

        return joints

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the hand joint (unless Omit Hand Joint is set, in which case
        it belongs to another component) followed by the digit joints, thumb
        first. Empty if the hand joint is missing.
        """
        hand_joint = self.input("Hand Joint").get()
        if not hand_joint or not mref.objExists(hand_joint):
            return []

        joints = self._mirror_digit_joints()

        if self.option("Omit Hand Joint").get():
            return joints

        return [hand_joint] + joints

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the hand joint, which is where the mirrored component's hand
        skeleton is generated. With Omit Hand Joint the hand joint belongs to
        another component (such as an arm), so the hand joint itself is
        returned and the mirrored component's digits are generated under its mirror.
        """
        hand_joint = self.input("Hand Joint").get()
        if not hand_joint or not mref.objExists(hand_joint):
            return ""

        if self.option("Omit Hand Joint").get():
            return hand_joint

        parent = mref.get(hand_joint).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        If the other side already has its own (unused) hand joints, this component
        uses them. Otherwise this component generates its own hand skeleton. The
        tip inputs are cleared first, as the skeleton generation appends to
        them.
        """
        if self.mirror_mixin_counterparts_exist(mirrored_from.mirror_mixin_items_to_mirror()):
            self.option("Create Joints").set(False)

            # -- An omitted hand joint belongs to another component, so use
            # -- whatever that became in this mirror
            if self.option("Omit Hand Joint").get():
                self.input("Hand Joint").set(
                    self.mirror_mixin_mirrored_node(mirrored_from.input("Hand Joint").get()),
                )
            return

        finger_tips = mirrored_from.input("Finger Tips").get() or list()
        finger_labels = list(self.option("Finger Labels").get() or list())

        # -- The skeleton generation makes a finger per label. If there are
        # -- more labels than the original has fingers (a build appends the
        # -- thumb label to the stored labels), generate with just the first
        # -- ones and put the labels back afterwards.
        if finger_tips and len(finger_labels) > len(finger_tips):
            self._mirror_finger_labels = finger_labels
            self.option("Finger Labels").set(finger_labels[:len(finger_tips)])

        elif len(finger_tips) != len(finger_labels):
            print(
                f"Mirror : {mirrored_from.label()} has {len(finger_tips)} finger tips but "
                f"{len(finger_labels)} finger labels. {self.label()} is generated "
                f"with {len(finger_labels)} fingers."
            )

        self.option("Create Joints").set(True)
        self.input("Hand Joint").set("")
        self.input("Thumb Tip").set("")
        self.input("Finger Tips").set([])

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        Restores the Create Joints option (and any finger labels trimmed for
        the skeleton generation) so this component's data matches the original.
        """
        self.option("Create Joints").set(mirrored_from.option("Create Joints").get(resolved=False))

        finger_labels = getattr(self, "_mirror_finger_labels", None)
        if finger_labels is not None:
            self.option("Finger Labels").set(finger_labels)
            del self._mirror_finger_labels

    @classmethod
    def _add_multiplied_attr(cls, host, name, multiplier, proxy_to=None, min=-1.0, max=1.0) -> str:
        """
        Adds a keyable float attribute to the host, and returns the output
        of a node which multiplies that attribute by the given multiplier.
        A proxy of the attribute is added to every node in proxy_to.
        """
        attribute = mref.get(host).add_attribute(
            name,
            value=None,
            attribute_type="float",
            minValue=min,
            maxValue=max,
            defaultValue=0,
            keyable=True,
        )

        multiplied_attr = aniseed_toolkit.scene.node_math.multiply(
            attribute.full_name(),
            multiplier,
        )

        for proxy in proxy_to or list():
            mref.get(proxy).add_proxy(name, attribute)

        return multiplied_attr

    @classmethod
    def _connect_with_inversion(cls, connect_these, to_this, inversion, multiplier=1.0):
        """
        Sums the given attributes, multiplies the sum by the inversion and the
        multiplier and connects the result into to_this.
        """
        # -- Create an add node
        add_node = mref.create("plusMinusAverage")

        for connect_this in connect_these:
            mref.get(connect_this).connect_next(add_node.attr("input1D"))

            # -- Note: the inversion and multiply nodes are created for every
            # -- input (rather than once for the sum) and only the first
            # -- connection into to_this can succeed - any subsequent ones
            # -- fail silently. The extra nodes are kept for output parity.
            inverted_attr = aniseed_toolkit.scene.node_math.multiply(
                add_node.attr("output1D").full_name(),
                inversion,
            )
            multiplied_attr = aniseed_toolkit.scene.node_math.multiply(
                inverted_attr,
                multiplier,
            )

            # -- This silently does nothing if to_this is already connected
            mref.get(multiplied_attr).connect(to_this)

    @classmethod
    def _get_ranged_value(cls, idx, items):
        """
        Maps an index linearly into the range 1.0 to -1.0, where index 0
        gives 1.0 and index len(items) - 1 gives -1.0. Used to weight how
        much each finger is affected by features such as spread.

        Args:
            idx: The index of the finger
            items: The list the index relates to (only its length is used)

        Returns:
            The ranged float value
        """
        increment = 1.0 / (len(items) - 1)
        v = ((idx + 1) / (len(items) - 1)) - increment
        v = 1.0 - (v * 2.0)
        return v

    def all_joints(self):
        """
        Convenience function for returning all the joints driven
        by this component
        """
        all_joints = []
        finger_tips = self.input("Finger Tips").get()
        thumb_tip = self.input("Thumb Tip").get()
        use_metacarpals = self.option("Use Metacarpals").get()
        digit_count = self.option("Digit Count").get()
        omit_hand = self.option("Omit Hand Joint").get()
        search_distance = digit_count + (1 if use_metacarpals else 0)

        for finger_tip in [thumb_tip] + finger_tips:
            finger_root = self.get_parent(finger_tip, search_distance - 1)
            all_joints.extend(aniseed_toolkit.scene.joints.get_between(finger_root, finger_tip))

        if not omit_hand:
            all_joints.append(self.input("Hand Joint").get())

        return all_joints
