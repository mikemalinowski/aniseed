import os
import qute
import bony
import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
class HandComponent(aniseed.RigComponent):

    identifier = "Standard : Hand"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(HandComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value=None,
            validate=False,
            group="Control Rig",
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
            value="Base",
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
            name="Use Parent As Hand",
            value=False,
            group="Behaviour",
            description="If True, the parent will be considered the hand control. If False, a dedicated hand control will be created"
        )

        self.declare_option(
            name="Assume Metacarpals",
            value=False,
            group="Behaviour",
            description="If True, the component will assume that there is an additional bone which acts as the metacarpals."
        )

        self.declare_option(
            name="Finger Depth",
            value=3,
            group="Behaviour",
            description="How many joints (excluding the metacarpal) make up the finger."
        )

        self.declare_option(
            name="Expose Attributes To Nodes",
            value=[],
            group="Behaviour",
        )

        self.declare_output("Hand")

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name):

        if requirement_name in ["Finger Tips"]:
            return aniseed.widgets.everywhere.ObjectList()

        if requirement_name in ["Parent", "Hand", "Thumb Tip"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):

        if option_name == "Expose Attributes To Nodes":
            return aniseed.widgets.everywhere.ObjectList()

        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    # ----------------------------------------------------------------------------------
    def user_functions(self):
        return {
            "Create Joints": self.build_skeleton,
        }

    # ----------------------------------------------------------------------------------
    def is_valid(self):
        finger_tips = self.input("Finger Tips").get() or list()
        thumb_tip = self.input("Thumb Tip").get()

        if not len(finger_tips) > 0:
            print("You must specify at least one finger")
            return False

        if not thumb_tip:
            print("You must specify a thumb")
            return False

        finger_depth = self.option("Finger Depth").get()

        for finger_tip in finger_tips:
            if not self.get_parent(finger_tip, parent_index=finger_depth - 1):
                print(f"{finger_tip} does not have {finger_depth} joints")
                return False

        return True

    # ----------------------------------------------------------------------------------
    def run(self):
    
        # -- Get our hand control if one was given
        parent = self.input("Parent").get()
        finger_tips = self.input("Finger Tips").get() or list()

        finger_roots = [
            self.get_parent(tip, self.option("Finger Depth").get() - 1)
            for tip in finger_tips
        ]

        # -- Determine the options we're building with
        location = self.option("Location").get()

        # -- This is the default rotation of our shapes based on X down the chain
        shape_rotation = [180, 0, 90]

        if self.option("Use Parent As Hand").get():
            hand = parent

        else:
            # -- If we were not given a hand control
            hand_shape_rotation = [0, -90, 0]

            if self.option("Location").get() == self.config.right:
                hand_shape_rotation = [0, 90, 0]

            hand = aniseed.control.create(
            description=f"{self.option('Descriptive Prefix').get()}Hand",
                location=location,
                parent=self.input("Parent").get(),
                shape="core_arrow_handle",
                config=self.config,
                match_to=self.input("Parent").get(),
                shape_scale=45.0,
                rotate_shape=hand_shape_rotation,
            )

        self.output("Hand").set(hand)

        aniseed.utils.attribute.add_separator_attr(hand)

        # -- Add our finger control attributes
        mc.addAttr(
            hand,
            shortName="finger_visibility",
            at='bool',
            dv=1,
            k=True,
        )
        finger_visibility_attr = f"{hand}.finger_visibility"

        curl_attr = self._add_multiplied_attr(
            hand,
            "curl",
            90,
            proxy_to=self.option("Expose Attributes To Nodes").get(),
        )

        spread_attr = self._add_multiplied_attr(
            hand,
            "spread",
            90,
            proxy_to=self.option("Expose Attributes To Nodes").get(),
        )

        cup_attr = self._add_multiplied_attr(
            hand,
            "cup",
            90,
            proxy_to=self.option("Expose Attributes To Nodes").get(),
        )

        finger_index_excluding_thumb = -1

        all_tips_including_thumb = finger_tips[:]
        all_tips_including_thumb.append(self.input("Thumb Tip").get())
        finger_labels = [
            "index",
            "middle",
            "ring",
            "pinky",
            "other",
            "other",
            "other",
        ]

        for finger_idx, finger_tip in enumerate(all_tips_including_thumb):

            finger_root = self.get_parent(finger_tip, self.option("Finger Depth").get() - 1)

            # -- If this is not the thumb, increment this value
            if finger_tip != self.input("Thumb Tip").get():
                finger_index_excluding_thumb += 1

            finger_joints = bony.hierarchy.get_between(
                finger_root,
                finger_tip,
            )

            facing_dir = bony.direction.get_chain_facing_direction(
                finger_joints[-2],
                finger_joints[-1],
            )
            
            facing_struct = bony.direction.Facing
            
            if facing_dir == facing_struct.NegativeX:
                shape_rotation = [0, 0, 90]

            # -- The finger base is a finger joint near the write which is designed
            # -- to allow for more accurate spreading and cupping of the hand.
            metacarpal = None

            if self.option("Assume Metacarpals").get():
                metacarpal = mc.listRelatives(
                    finger_root,
                    parent=True
                )[0]
                finger_joints.insert(
                    0,
                    metacarpal,
                )

            control_parent = hand

            # -- Cycle all the digits
            for idx, finger_joint in enumerate(finger_joints):

                finger_control = aniseed.control.create(
                    description=finger_labels[finger_idx],
                    location=location,
                    parent=control_parent,
                    shape="core_paddle",
                    config=self.config,
                    match_to=finger_joint,
                    shape_scale=5.0,
                    rotate_shape=shape_rotation,
                )

                finger_offset = aniseed.control.get_classification(
                    finger_control,
                    "off",
                )

                # -- Connect the finger visibility
                mc.connectAttr(
                    finger_visibility_attr,
                    f"{finger_offset}.visibility",
                    force=True
                )

                mc.parentConstraint(
                    finger_control,
                    finger_joint,
                    maintainOffset=False,
                )

                mc.scaleConstraint(
                    finger_control,
                    finger_joint,
                    maintainOffset=False,
                )

                # -- If this is a thumb, we are done, as we do not apply
                # -- any of the attribute drivers to it
                if finger_tip == self.input("Thumb Tip").get():
                    control_parent = finger_control
                    continue

                ranged_value = self._get_ranged_value(
                    finger_index_excluding_thumb,
                    finger_tips,
                )

                # -- Set up the attribute links
                if idx == 0 and metacarpal:

                    # -- To reach here, we're working with the base finger, which
                    # -- only has the cup

                    # # -- Do the spread
                    self._connect_with_inversion(
                        spread_attr,
                        f"{finger_offset}.rotateZ",
                        1,
                        multiplier=ranged_value * -0.1,
                    )

                    self._connect_with_inversion(
                        cup_attr,
                        f"{finger_offset}.rotateX",
                        1,
                        multiplier=ranged_value * 0.25,
                    )

                elif (idx == 1 and metacarpal) or (idx == 0 and not metacarpal):

                    # -- To reach here we're operating on the first digit of the finger
                    self._connect_with_inversion(
                        curl_attr,
                        f"{finger_offset}.rotateY",
                        1,
                    )

                    self._connect_with_inversion(
                        spread_attr,
                        f"{finger_offset}.rotateZ",
                        1,
                        multiplier=ranged_value * -0.5,
                    )

                    if not metacarpal:
                        self._connect_with_inversion(
                            cup_attr,
                            f"{finger_offset}.rotateX",
                            1,
                            multiplier=ranged_value * 0.25,
                        )

                else:

                    # -- To reach here we're operating on a normal finger digit
                    self._connect_with_inversion(
                        curl_attr,
                        f"{finger_offset}.rotateY",
                        1,
                    )

                control_parent = finger_control

    # ----------------------------------------------------------------------------------
    def get_parent(self, node, parent_index):

        while parent_index > 0 and node:

            node = mc.listRelatives(node, parent=True)[0]

            parent_index -= 1

        return node

    # ----------------------------------------------------------------------------------
    def build_skeleton(self, omit_hand=None):

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        omit_hand = qute.utilities.request.confirmation(
            title="Omit Hand?",
            label=f"Would you like to skip generating the hand bone and use {parent} as the hand?",
        )

        joint_map = bony.writer.load_joints_from_file(
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "hand_joints.json",
            ),
            apply_names=False,
            invert=self.option("Location").get() == self.config.right,
        )
        hand = None

        if omit_hand:
            hand_to_remove = joint_map["JNT_Hand_01_LF"]

            for child in mc.listRelatives(hand_to_remove, children=True):
                mc.parent(
                    child,
                    parent,
                    relative=True,
                )

            mc.delete(hand_to_remove)
            del joint_map["JNT_Hand_01_LF"]
            hand = parent

        else:
            mc.xform(
                joint_map["JNT_Hand_01_LF"],
                matrix=mc.xform(
                    parent,
                    matrix=True,
                    query=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )
            hand = joint_map["JNT_Hand_01_LF"]

        finger_roots = []
        finger_tips = []

        for key, joint in joint_map.items():

            joint = mc.rename(joint, "temp")

            joint = mc.rename(
                joint,
                self.config.generate_name(
                    classification=self.config.joint,
                    description=key.split("_")[1],
                    location=self.option("Location").get(),
                )
            )

            if "Finger_01_" in key:
                finger_roots.append(joint)

            if "Finger_03_" in key:
                finger_tips.append(joint)

        self.input("Finger Roots").set(sorted(finger_roots))
        self.input("Finger Tips").set(sorted(finger_tips))
        self.option("Assume Base Roots").set(True)

    # ----------------------------------------------------------------------------------
    @classmethod
    def _add_multiplied_attr(cls, host, name, multiplier, proxy_to=None):

        mc.addAttr(
            host,
            shortName=name,
            at='float',
            min=-1,
            max=1,
            dv=0,
            k=True,
        )

        multiply_node = mc.createNode("floatMath")
        mc.setAttr(multiply_node + ".operation", 2)  # -- Multiply
        mc.setAttr(multiply_node + ".floatB", multiplier)
        mc.connectAttr(
            f"{host}.{name}",
            f"{multiply_node}.floatA",
        )

        for proxy in proxy_to or list():
            mc.addAttr(
                proxy,
                shortName=name,
                proxy=f"{host}.{name}",
                k=True,
            )

        return f"{multiply_node}.outFloat"

    # ----------------------------------------------------------------------------------
    @classmethod
    def _connect_with_inversion(cls, connect_this, to_this, inversion, multiplier=1.0):

        inversion_node = mc.createNode("floatMath")
        mc.setAttr(inversion_node + ".operation", 2)  # -- Multiply
        mc.setAttr(inversion_node + ".floatB", inversion)
        mc.connectAttr(
            connect_this,
            f"{inversion_node}.floatA",
        )

        multiply_node = mc.createNode("floatMath")
        mc.setAttr(multiply_node + ".operation", 2)  # -- Multiply
        mc.setAttr(multiply_node + ".floatB", multiplier)

        mc.connectAttr(
            f"{inversion_node}.outFloat",
            f"{multiply_node}.floatA"
        )

        mc.connectAttr(
            f"{multiply_node}.outFloat",
            to_this
        )

        return multiply_node

    # ----------------------------------------------------------------------------------
    @classmethod
    def _get_ranged_value(cls, idx, items):
        increment = 1.0 / (len(items) - 1)
        v = ((idx + 1) / (len(items) - 1)) - increment
        v = 1.0 - (v * 2.0)
        return v