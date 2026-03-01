import os

from pygments.lexers import q

import mref
import qtility
import aniseed
import aniseed_toolkit
from maya import cmds


class HandComponent(aniseed.RigComponent):

    identifier = "Limb : Hand"
    icon = os.path.join(
        os.path.dirname(__file__),
        "hand.png",
    )

    def __init__(self, *args, **kwargs):
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
            pre_expose = True,
        )

        self.declare_option(
            name="Digit Count",
            value=3,
            group="Behaviour",
            description="How many joints (excluding the metacarpal) make up the finger.",
            pre_expose = True,
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

        self.declare_option(
            name="LinkedGuide",
            value="",
            hidden=True,
        )
        self.declare_output("Hand")

    def on_enter_stack(self):
        """
        When the user adds this componen to the stack, build the skeleton for them
        if they want to.
        """
        if self.option("Create Joints").get():
            self.user_func_create_skeleton()

        self.option("Omit Hand Joint").set_hidden(True)
        self.option("Create Joints").set_hidden(True)

    def on_build_started(self) -> None:
        if self.guide():
            self.user_func_remove_guide()

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

        if self.guide():
            menu["Remove Guide"] = self.user_func_remove_guide
            menu["Toggle Joint Selectability"] = self.user_func_toggle_joint_selectability
        else:
            menu["Create Guide"] = self.user_func_create_guide

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
        parent = self.input("Parent").get()
        finger_tips = self.input("Finger Tips").get() or list()

        # -- Read our option data
        prefix = self.option('Descriptive Prefix').get()
        location = self.option("Location").get()
        assume_metacarpals = self.option("Use Metacarpals").get()
        finger_depth = self.option("Digit Count").get()

        # -- Read our option data

        finger_roots = [
            self.get_parent(tip, finger_depth - 1)
            for tip in finger_tips
        ]

        # -- This is the default rotation of our shapes based on X down the chain
        shape_rotation = [90, 90, 0]
        hand_shape_rotation = [0, -90, 0]

        # -- Create our hand control
        hand = aniseed_toolkit.control.create(
            description=f"{self.option('Descriptive Prefix').get()}Hand",
            location=location,
            parent=parent,
            shape="core_arrow_handle",
            config=self.config,
            match_to=hand_joint,
            shape_scale=45.0,
            rotate_shape=hand_shape_rotation,
        )

        # -- Clear any constraints on the hand
        aniseed_toolkit.containts.remove_all(nodes=[hand_joint])

        # -- Constrain the hand bone to the hand control and set the output
        cmds.parentConstraint(hand.ctl, hand_joint, maintainOffset=False)
        cmds.scaleConstraint(hand.ctl, hand_joint, maintainOffset=False)
        self.output("Hand").set(hand.ctl)

        # -- Start adding our custom attributes
        aniseed_toolkit.attributes.add_separator(hand.ctl)

        # -- Add our finger control attributes
        cmds.addAttr(
            hand.ctl,
            shortName="finger_visibility",
            attributeType='bool',
            defaultValue=1,
            keyable=True,
        )
        finger_visibility_attr = f"{hand.ctl}.finger_visibility"

        curl_attr = self._add_multiplied_attr(
            hand.ctl,
            "curl",
            90,
            proxy_to=self.option("Expose Attributes To Nodes").get(),
        )

        spread_attr = self._add_multiplied_attr(
            hand.ctl,
            "spread",
            90,
            proxy_to=self.option("Expose Attributes To Nodes").get(),
        )

        cup_attr = self._add_multiplied_attr(
            hand.ctl,
            "cup",
            90,
            proxy_to=self.option("Expose Attributes To Nodes").get(),
        )

        finger_index_excluding_thumb = -1

        # -- Whilst we do need to treat the thumb a little differently
        # -- there is also a lot that is the same. Thus we use the same
        # -- iteration to deal with them all
        all_tips_including_thumb = finger_tips[:]
        all_tips_including_thumb.append(self.input("Thumb Tip").get())

        # -- Get a list of all the finger labels as well as the thumb label
        finger_labels = self.option("Finger Labels").get()
        finger_labels.append(self.option("Thumb Label").get())
        finger_depth = self.option("Digit Count").get()

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
            if finger_tip != self.input("Thumb Tip").get():
                finger_index_excluding_thumb += 1

            # -- Get the full finger chain
            finger_joints = aniseed_toolkit.joints.get_between(finger_root, finger_tip)

            # -- Determine the facing direction of the fingers so that we
            # -- can adjust the default controls if required.
            facing_dir = aniseed_toolkit.direction.get_chain_facing_direction(
                finger_joints[-2],
                finger_joints[-1],
            )
            if facing_dir == facing_dir.NegativeX:
                shape_rotation = [0, 0, 90]

            # -- Check whether we need to assume there are metacarpal bones. These
            # -- are bones that are parents of the fingers and give functionality
            # -- like spreading and cupping.
            metacarpal = None
            if assume_metacarpals:
                metacarpal_joint = mref.get(finger_root).parent().full_name()

                metacarpal = aniseed_toolkit.control.create(
                    description=f"metacarpal_{finger_labels[finger_idx]}",
                    location=location,
                    parent=hand.ctl,
                    shape="core_paddle",
                    config=self.config,
                    match_to=self.get_parent(finger_tip, finger_depth),
                    shape_scale=5.0,
                    rotate_shape=shape_rotation,
                )
                # -- Constrain the joint
                cmds.parentConstraint(metacarpal.ctl, metacarpal_joint, maintainOffset=False)
                cmds.scaleConstraint(metacarpal.ctl, metacarpal_joint, maintainOffset=False)

            # -- We're now going to create the fk hierarchy - so start by defining
            # -- the hand as the parent, and we will update this as we go.
            control_parent = metacarpal.ctl or hand.ctl
            finger_controls = []

            # -- The ranged value gives us a float denoting how much influence
            # -- this finger should get from features that spread etc.
            ranged_value = self._get_ranged_value(
                finger_index_excluding_thumb,
                finger_tips,
            )

            # -- Cycle all the digits
            for idx, finger_joint in enumerate(finger_joints):

                finger_control = aniseed_toolkit.control.create(
                    description=finger_labels[finger_idx],
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
                cmds.connectAttr(
                    finger_visibility_attr,
                    f"{finger_control.off}.visibility",
                    force=True
                )

                # -- Constrain the joint
                cmds.parentConstraint(finger_control.ctl, finger_joint, maintainOffset=False)
                cmds.scaleConstraint(finger_control.ctl, finger_joint, maintainOffset=False)

                # -- If this is a thumb, we are done, as we do not apply
                # -- any of the attribute drivers to it
                if finger_tip == self.input("Thumb Tip").get():
                    control_parent = finger_control.ctl
                    continue

                control_parent = finger_control.ctl

            if not is_thumb:
                self.setup_finger(
                    finger_controls,
                    metacarpal,
                    ranged_value,
                    cup_attr,
                    curl_attr,
                    spread_attr,
                )

    def setup_finger(self, finger_controls, metacarpal, ranged_value, cup_attr, curl_attr, spread_attr):

        # -- Setup the cup
        for control in finger_controls:
            self._connect_with_inversion(
                curl_attr,
                f"{control.off}.rotateZ",
                -1,
            )

        # -- Do the cup
        cup_control = metacarpal or finger_controls[0]
        self._connect_with_inversion(
            cup_attr,
            f"{cup_control.off}.rotateX",
            1,
            multiplier=ranged_value * 0.25,
        )

        # -- Setup the spread
        spread_control = metacarpal or finger_controls[0]
        self._connect_with_inversion(
            spread_attr,
            f"{spread_control.off}.rotateY",
            1,
            multiplier=ranged_value * -0.1,
        )

    def get_parent(self, node: str, parent_index: int) -> str:
        """
        This will return the parent with the given index
        """
        while parent_index > 0 and node:
            node = cmds.listRelatives(node, parent=True)[0]
            parent_index -= 1
        return node

    def user_func_create_skeleton(self, parent=None):
        """
        This will generate a skeleton for us.
        """
        # -- Determine the parent for the hand bones
        parent = parent or aniseed_toolkit.mutils.first_selected()

        # -- Get the finger labels
        omit_hand = self.option("Omit Hand Joint").get()
        finger_labels = self.option("Finger Labels").get()
        digit_count = self.option("Digit Count").get()
        use_metacarpals = self.option("Use Metacarpals").get()
        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        thumb_label = self.option("Thumb Label").get()
        all_joints = []

        # -- Create the hand bone if required
        hand = aniseed_toolkit.joints.create(
            description=f"{prefix}_hand",
            location=location,
            parent=parent,
            config=self.config,
        )
        all_joints.append(hand)
        spread = 5.0

        # -- Track all the finger tips we create
        
        for finger_index, label in enumerate([thumb_label] + finger_labels):
            ranged_value = self._get_ranged_value(finger_index, finger_labels)

            # -- By default the parent for our digits will be the
            # -- give parent
            digit_parent = hand
            planar_offset = ranged_value * (spread / 4)
            # -- Before we build the finger digits, build the metacarpal if we
            # -- need to
            if finger_index and use_metacarpals:
                metacarpal = aniseed_toolkit.joints.create(
                    description=f"{prefix}_Metacarpal_{label}",
                    location=location,
                    parent=hand,
                    config=self.config,
                )
                all_joints.append(metacarpal)

                # -- Adjust the transform of the metacarpal
                cmds.setAttr(f"{metacarpal}.translateZ", planar_offset)
                cmds.setAttr(f"{metacarpal}.translateX", 1)
                # cmds.setAttr(f"{metacarpal}.rotateY", ranged_value)

                # -- Ensure the metacarpal is the parent of the subsequent
                # -- digits
                digit_parent = metacarpal

            # -- Now we can start building our digits
            for digit_index in range(digit_count):
                
                digit = aniseed_toolkit.joints.create(
                    description=f"{prefix}_finger_{label}",
                    location=location,
                    parent=digit_parent,
                    config=self.config,
                )
                all_joints.append(digit)

                # -- Match just the translate to the parent
                cmds.xform(
                    digit,
                    translation=cmds.xform(digit_parent, query=True, translation=True, worldSpace=True),
                    worldSpace=True,
                )

                length = spread * 2 if not digit_index else spread
                cmds.setAttr(f"{digit}.translateX", length)

                if finger_index == 0:  # -- Thumb
                    cmds.setAttr(f"{digit}.rotateX", 90)

                if digit_index == 0:
                    if finger_index == 0: # -- First thumb
                        cmds.setAttr(f"{digit}.translateX", length / 2.0)
                        cmds.setAttr(f"{digit}.translateZ", planar_offset * 1.6)
                        cmds.setAttr(f"{digit}.translateY", -length * 0.25)

                    else:  # -- First Finger
                        cmds.setAttr(f"{digit}.translateZ", planar_offset)

                # -- Mark this digit as the parent for the next digit
                digit_parent = digit

            # -- Ensure the last digits are added
            if finger_index:
                tips = self.input("Finger Tips").get()
                tips.append(digit)
                self.input("Finger Tips").set(tips)
            else:
                self.input("Thumb Tip").set(digit)

        # -- If we're not omiting the hand, then snap the hand to the parent
        if omit_hand:
            all_joints.remove(hand)
            cmds.xform(
                hand,
                translation=cmds.xform(parent, query=True, translation=True, worldSpace=True),
                worldSpace=True,
            )

            for child in cmds.listRelatives(hand, children=True):
                cmds.parent(child, parent)
            cmds.delete(hand)
            output_hand = parent
        else:
            cmds.xform(
                hand,
                translation=cmds.xform(parent, query=True, translation=True, worldSpace=True),
                worldSpace=True,
            )
            output_hand = hand

        # -- Now we set our inputs
        self.input("Hand Joint").set(output_hand)

        # -- Finally, we build the guide
        self.user_func_create_guide()

        # -- Add our joints to a deformers set.
        aniseed_toolkit.sets.add_to(all_joints, set_name="deformers")

    @classmethod
    def _add_multiplied_attr(cls, host, name, multiplier, proxy_to=None):

        cmds.addAttr(
            host,
            shortName=name,
            attributeType='float',
            minValue=-1,
            maxValue=1,
            defaultValue=0,
            keyable=True,
        )

        multiply_node = cmds.createNode("floatMath")
        cmds.setAttr(multiply_node + ".operation", 2)  # -- Multiply
        cmds.setAttr(multiply_node + ".floatB", multiplier)
        cmds.connectAttr(
            f"{host}.{name}",
            f"{multiply_node}.floatA",
        )

        for proxy in proxy_to or list():
            cmds.addAttr(
                proxy,
                shortName=name,
                proxy=f"{host}.{name}",
                keyable=True,
            )

        return f"{multiply_node}.outFloat"

    @classmethod
    def _connect_with_inversion(cls, connect_this, to_this, inversion, multiplier=1.0):

        inversion_node = cmds.createNode("floatMath")
        cmds.setAttr(inversion_node + ".operation", 2)  # -- Multiply
        cmds.setAttr(inversion_node + ".floatB", inversion)
        cmds.connectAttr(
            connect_this,
            f"{inversion_node}.floatA",
        )

        multiply_node = cmds.createNode("floatMath")
        cmds.setAttr(multiply_node + ".operation", 2)  # -- Multiply
        cmds.setAttr(multiply_node + ".floatB", multiplier)

        cmds.connectAttr(
            f"{inversion_node}.outFloat",
            f"{multiply_node}.floatA"
        )

        cmds.connectAttr(
            f"{multiply_node}.outFloat",
            to_this
        )

        return multiply_node

    @classmethod
    def _get_ranged_value(cls, idx, items):
        increment = 1.0 / (len(items) - 1)
        v = ((idx + 1) / (len(items) - 1)) - increment
        v = 1.0 - (v * 2.0)
        return v

    def user_func_create_guide(self):

        # -- If the guide already exists, then we do not need to do anything
        # -- more.
        if self.guide():
            return

        # -- Read our option data
        hand_joint = self.input("Hand Joint").get()
        digit_count = self.option("Digit Count").get()
        use_metacarpals = self.option("Use Metacarpals").get()
        finger_tips = self.input("Finger Tips").get()
        thumb_tip = self.input("Thumb Tip").get()
        omit_hand_joint = self.option("Omit Hand Joint").get()

        # -- Create the org node
        org = mref.create("transform", name="hand_guide").full_name()

        # -- Create the hand guide
        hand_guide = aniseed_toolkit.guide.create(
            joint=self.input("Hand Joint").get(),
            parent=org,
            scale=1.25,
            constrain=not self.option("Omit Hand Joint").get(),
        )

        for idx, finger_tip in enumerate([thumb_tip] + finger_tips):
            finger_root = self.get_parent(finger_tip, digit_count - 1)
            metacarpal = self.get_parent(finger_tip, digit_count)
            other_digits = aniseed_toolkit.joints.get_between(finger_root, finger_tip)[1:]

            guide_parent = hand_guide

            if idx and use_metacarpals:
                metacarpal_guide = aniseed_toolkit.guide.create(
                    joint=metacarpal,
                    parent=guide_parent,
                    scale=0.5,
                    link_to=guide_parent,
                )
                guide_parent = metacarpal_guide

            finger_root_guide = aniseed_toolkit.guide.create(
                joint=finger_root,
                parent=guide_parent,
                scale=1,
                link_to=guide_parent,
            )
            guide_parent = finger_root_guide

            for digit in other_digits:
                digit_guide = aniseed_toolkit.guide.create(
                    joint=digit,
                    parent=guide_parent,
                    scale=0.5,
                    link_to=guide_parent,
                )
                guide_parent = digit_guide

        self.option("LinkedGuide").set(org)
        aniseed_toolkit.joints.make_referenced(self.all_joints())

        # -- If there is a parent of the root then we constrain our
        # -- setup to that
        root_joint = mref.get(hand_joint)
        if root_joint.parent():
            cmds.parentConstraint(
                root_joint.parent().full_name(),
                org,
                maintainOffset=True,
            )

    def user_func_remove_guide(self):

        if not self.guide():
            return

        with aniseed_toolkit.joints.HeldTransforms(self.all_joints()):
            cmds.delete(self.guide())

        aniseed_toolkit.joints.unreference(self.all_joints())

    def guide(self):
        guide = self.option("LinkedGuide").get()
        if guide and cmds.objExists(guide):
            return guide
        return None

    def user_func_toggle_joint_selectability(self):
        """
        This will make all the joints either unselectable or selectable
        """
        joints = self.all_joints()
        if aniseed_toolkit.joints.is_referenced(joints[0]):
            aniseed_toolkit.joints.unreference(joints)
        else:
            aniseed_toolkit.joints.make_referenced(joints)

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
            all_joints.extend(aniseed_toolkit.joints.get_between(finger_root, finger_tip))

        if not omit_hand:
            all_joints.append(self.input("Hand Joint").get())

        return all_joints
