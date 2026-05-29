import os
import mref
import uuid
import snappy
import typing
import aniseed
import qtility
import functools
import collections
import aniseed_toolkit
from maya import cmds


# noinspection PyInterpreter
class ArmComponent(aniseed.RigComponent):

    identifier = "Limb : Arm"
    icon = os.path.join(
        os.path.dirname(__file__),
        "arm.png",
    )

    # noinspection PyUnresolvedReferences
    def __init__(self, *args, **kwargs):
        super(ArmComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Shoulder",
            description="The root of the spine",
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Hand",
            description="The tip of the spine",
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Upper Twist Joints",
            description="All upper twist joints",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_input(
            name="Lower Twist Joints",
            description="All lower twist joints",
            validate=False,
            group="Twist Configuration",
        )

        self.declare_option(
            name="Descriptive Prefix",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            value=self.config.left,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Align Shoulder To World",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Hand To World",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Upvector To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Apply Soft Ik",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Apply World Fk Switches",
            value=True,
            group="Behaviour",
        )
        self.declare_option(
            name="Apply Space Switches",
            value=True,
            group="Behaviour",
            pre_expose=True,
        )

        # -- Delcare our options which make it easier and quicker to generate
        # -- a skeleton if needed
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Build Skeleton", value=True, pre_expose=True)
        
        # -- Declare our outputs so other components can access them
        self.declare_output(
            name="Blended Upper Arm",
        )

        self.declare_output(
            name="Blended Lower Arm",
        )

        self.declare_output(
            name="Blended Hand",
            is_default=True,
        )

        self.declare_output("Upvector")
        self.declare_output("Ik Hand")
        self.declare_output("Shoulder")

        # -- Declare our build properties - this is only required because i have
        # -- chosen within this component to break up the long build script
        # -- into functions, and therefore we use this to access items created
        # -- from other functions.
        self.prefix: str = ""
        self.location: str = ""
        self.org: str = ""
        self.arm_joints: list[str] = []
        self.chain_direction: "Direction" = None
        self.shoulder_control: "Control" = None
        self.config_control: "Control" = None
        self.upvector_control: "Control" = None
        self.ik_hand_control: "Control" = None
        self.fk_upper_control: "Control" = None
        self.fk_lower_control: "Control" = None
        self.fk_hand_control: "Control" = None

        self.controls: list[str] = []
        self.fk_controls: list[str] = []
        self.ik_controls: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [90, 0, 0]

    def on_enter_stack(self):
        """
        When this enters the stack we can build the skeleton structure
        automatically if requested.
        """
        # -- Read our options
        build_skeleton = self.option("Build Skeleton")
        upper_twist_count = self.option("Upper Twist Count")
        lower_twist_count = self.option("Lower Twist Count")
        apply_spaceswitches = self.option("Apply Space Switches")

        # -- To reach here, we have not - so lets mark this as being processed
        # -- regardless of whether or not we need to build the skeleton
        build_skeleton.set_hidden(True)
        upper_twist_count.set_hidden(True)
        lower_twist_count.set_hidden(True)
        apply_spaceswitches.set_hidden(True)

        # -- If we do not need to build the skeleton, we can exit
        if not build_skeleton.get():
            return

        # -- To reach here we need to build the skeleton
        parent = None
        if cmds.ls(selection=True):
            parent = cmds.ls(selection=True)[0]

        self.user_func_create_skeleton(
            parent=parent,
            upper_twist_count=upper_twist_count.get(),
            lower_twist_count=lower_twist_count.get(),
        )

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent(tags=["fk tip", "chest", "tip"])

        if apply_spaceswitches.get():
            self.setup_spaceswitches()

    def on_removed_from_stack(self):
        """
        This is triggered when we remove the item from the stack, so we take
        a moment to clear the joints and reparent any joints from outside
        the component.
        """
        # -- Remove the joints (re-parenting any children)
        new_parent = mref.get(self.input("Shoulder").get()).parent()
        aniseed_toolkit.joints.reparent_unknown_children(self.all_joints(), new_parent)

        # -- Now delete our leg chain and joints
        cmds.delete(self.input("Shoulder").get())
    
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

        object_list = [
            "Parent",
            "Shoulder",
            "Hand",
        ]

        if requirement_name in object_list:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.ObjectList()

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        These are functions that will be exposed to the user if they
        right click the component
        """
        menu = super(ArmComponent, self).user_functions()
        shoulder_joint = self.input("Shoulder").get()

        # -- If there is no shoulder joint we expose the option
        # -- to allow the user to have one generated
        if not shoulder_joint or not cmds.objExists(shoulder_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)
            return menu

        menu["Create Mirrored Component"] = functools.partial(self.user_func_create_mirror)
        return menu

    def is_valid(self):
        """
        This gives us the chance to validate the skeleton
        before we commit to building.
        """
        arm_joints = aniseed_toolkit.joints.get_between(
            self.input("Shoulder").get(),
            self.input("Hand").get(),
        )[1:]

        direction = aniseed_toolkit.direction.get_chain_facing_direction(
            arm_joints[0],
            arm_joints[-1],
        )

        if direction != direction.PositiveX and direction != direction.NegativeX:
            print("Validation Warning : Chain is not failing Up/Down X")
            print(f"    Tested Chain : {arm_joints}")
            print(direction)
            return False

        return True

    def run(self):
        """
        This is triggered when the stack is executed
        """
        self._clear_values()
        self.prefix = self.option('Descriptive Prefix').get()
        self.location = self.option("Location").get()

        self.org = aniseed_toolkit.transforms.create(
            classification=self.config.organisational,
            description=f"{self.prefix}Arm",
            location=self.location,
            config=self.config,
            parent=self.input("Parent").get(),
            match_to=self.input("Parent").get()
        )
        self.arm_joints = aniseed_toolkit.joints.get_between(
            start=self.input('Shoulder').get(),
            end=self.input("Hand").get(),
        )
        self._create_controls()

        ikfk_setup = aniseed_toolkit.rigging.create_two_bone_ikfk(
            parent=self.shoulder_control.ctl,
            root_joint=self.arm_joints[1],
            end_joint=self.arm_joints[-1],
            attribute_host=self.config_control.ctl,
            attribute_name="ikfk",
            constrain=True,
            soft_ik=self.option("Apply Soft Ik").get(),
            soft_ik_host=self.ik_hand_control.ctl,
        )

        # -- Create the guide line
        aniseed_toolkit.guide.link(
            self.upvector_control.ctl,
            ikfk_setup.ik_chain[1].name(),
        )

        for node in ikfk_setup.all_nodes():
            node.rename(
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}Arm{node.name()}",
                    location=self.location,
                ),
            )


        cmds.parentConstraint(
            self.ik_hand_control.ctl,
            ikfk_setup.ik_target.name(),
            maintainOffset=True,
        )
        cmds.parentConstraint(
            self.upvector_control.ctl,
            ikfk_setup.ik_upvector.name(),
            maintainOffset=False,
        )

        for idx, fk_marker in enumerate(ikfk_setup.fk_chain):
            cmds.parentConstraint(
                self.fk_controls[idx],
                fk_marker.name(),
                maintainOffset=True,
            )

        ikfk_attribute = mref.get(f"{self.config_control.ctl}.ikfk")

        ik_condition = mref.create("lessThan")
        fk_condition = mref.create("greaterThan")

        ikfk_attribute.connect(ik_condition.input1)
        ikfk_attribute.connect(fk_condition.input1)

        ik_condition.input2.set(0.9)
        fk_condition.input2.set(0.1)
        ik_visibility_attribute = ik_condition.output.full_name()
        fk_visibility_attribute = fk_condition.output.full_name()

        for ik_control in self.ik_controls:
            ik_control = aniseed_toolkit.control.get(ik_control)
            cmds.connectAttr(
                ik_visibility_attribute,
                f"{ik_control.off}.visibility",
                force=True,
            )

        for fk_control in self.fk_controls:
            fk_control = aniseed_toolkit.control.get(fk_control)
            cmds.connectAttr(
                fk_visibility_attribute,
                f"{fk_control.off}.visibility",
                force=True,
            )

        # -- Set up the space switches on teh fk controls
        if self.option("Apply World Fk Switches").get():
            aniseed_toolkit.space.setup_fk_worldspace_switches([self.shoulder_control.ctl] + self.fk_controls, rig=self.rig)

        self.nk_joints = ikfk_setup.blend_chain.names()
        self._create_snap()
        self._create_twist_setup()
        self._set_outputs()

    def _create_controls(self):
        """
        Here we create all the controls for the arm
        """
        prefix = self.option('Descriptive Prefix').get()
        location = self.option("Location").get()

        self.shoulder_control = aniseed_toolkit.control.create(
            description=f"{prefix}Shoulder",
            location=location,
            parent=self.org,
            shape="core_cube",
            config=self.config,
            match_to=self.arm_joints[0],
            shape_scale=5.0,
            rotate_shape=None,
        )

        if self.option("Align Shoulder To World").get():
            cmds.xform(
                self.shoulder_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- Add the configuration control
        self.config_control = aniseed_toolkit.control.create(
            description=f"{prefix}ArmConfig",
            location=location,
            parent=self.shoulder_control.ctl,
            shape="core_lollipop",
            config=self.config,
            match_to=self.arm_joints[0],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        cmds.parentConstraint(
            self.shoulder_control.ctl,
            self.arm_joints[0],
            maintainOffset=True,
        )

        cmds.scaleConstraint(
            self.shoulder_control.ctl,
            self.arm_joints[0],
            maintainOffset=True,
        )

        self.fk_upper_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}UpperArmFK",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_paddle",
            config=self.config,
            match_to=self.arm_joints[1],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        self.fk_lower_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}LowerArmFK",
            location=self.location,
            parent=self.fk_upper_control.ctl,
            shape="core_paddle",
            config=self.config,
            match_to=self.arm_joints[2],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        self.fk_hand_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}HandFK",
            location=self.location,
            parent=self.fk_lower_control.ctl,
            shape="core_paddle",
            config=self.config,
            match_to=self.arm_joints[3],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        # -- We'll iterate over our fk joints, so place them all in a list
        self.fk_controls = [
            self.fk_upper_control.ctl,
            self.fk_lower_control.ctl,
            self.fk_hand_control.ctl,
        ]

        # -- Now create the main IK control
        self.ik_hand_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}Hand",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_stumpy_cross",
            config=self.config,
            match_to=self.arm_joints[-1],
            shape_scale=20.0,
            rotate_shape=[-90, 0 ,0],
        )
        self.ik_controls.append(self.ik_hand_control.ctl)
        if self.option("Align Hand To World").get():
            cmds.xform(
                self.ik_hand_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- Create the upvector control for the arm
        self.upvector_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}ArmUpvector",
            location=self.location,
            parent=self.shoulder_control.ctl,
            shape="core_sphere",
            config=self.config,
            match_to=self.arm_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )
        self.ik_controls.append(self.upvector_control.ctl)
        cmds.xform(
            self.upvector_control.org,
            translation=aniseed_toolkit.transformation.calculate_upvector_position(
                point_a=self.arm_joints[1],
                point_b=self.arm_joints[2],
                point_c=self.arm_joints[3],
                length=1,
            ),
            worldSpace=True,
        )
        if self.option("Align Upvector To World").get():
            cmds.xform(
                self.upvector_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

    def _create_snap(self):
        group = "IKFK_Arm_%s_%s" % (
            self.prefix,
            self.location,
        )

        snappy.new(
            node=self.ik_hand_control.ctl,
            target=self.nk_joints[2],
            group=group,
        )

        snappy.new(
            node=self.upvector_control.ctl,
            target=self.nk_joints[1],
            group=group,
        )

        snappy.new(
            node=self.fk_upper_control.ctl,
            target=self.nk_joints[0],
            group=group,
        )

        snappy.new(
            node=self.fk_lower_control.ctl,
            target=self.nk_joints[1],
            group=group,
        )

        snappy.new(
            node=self.fk_hand_control.ctl,
            target=self.nk_joints[2],
            group=group,
        )

    def _create_twist_setup(self):

        upper_twist_joints = self.input("Upper Twist Joints").get()
        lower_twist_joints = self.input("Lower Twist Joints").get()

        if upper_twist_joints:
            twist_component = self.rig.component_library.request("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(upper_twist_joints)
            twist_component.input("Parent").set(self.shoulder_control.ctl)
            twist_component.input("Root").set(self.nk_joints[0])
            twist_component.input("Tip").set(self.nk_joints[1])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("UpperTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                aniseed_toolkit.shapes.rotate(
                    twist,
                    *self.shape_rotation,
                )

        if lower_twist_joints:

            twist_component = self.rig.component_library.request("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(lower_twist_joints)
            twist_component.input("Parent").set(self.nk_joints[1])
            twist_component.input("Root").set(self.nk_joints[1])
            twist_component.input("Tip").set(self.nk_joints[2])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("LowerTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                aniseed_toolkit.shapes.rotate(
                    twist,
                    *self.shape_rotation,
                )

    def _set_outputs(self):

        self.output("Upvector").set(self.upvector_control.ctl)
        self.output("Ik Hand").set(self.ik_hand_control.ctl)

        self.output("Blended Upper Arm").set(self.nk_joints[0])
        self.output("Blended Lower Arm").set(self.nk_joints[1])
        self.output("Blended Hand").set(self.nk_joints[2])
        self.output("Shoulder").set(self.shoulder_control.ctl)

    def user_func_create_skeleton(self, parent=None, upper_twist_count=None, lower_twist_count=None):
        """
        This will create a skeleton structure automatically
        """
        if not parent and cmds.ls(selection=True):
            parent = cmds.ls(selection=True)[0]

        if upper_twist_count is None:
            upper_twist_count = qtility.request.text(
                title="Upper Twist Count",
                message="How many twist joints do you want on the upper arm?"
            )
            upper_twist_count = int(upper_twist_count)

        if lower_twist_count is None:
            lower_twist_count = qtility.request.text(
                title="Upper Twist Count",
                message="How many twist joints do you want on the lower arm?"
            )
            lower_twist_count = int(lower_twist_count)

        # # -- Joint transform attributes
        joint_data = collections.OrderedDict()
        joint_data["shoulder"] = {"jointOrientX": -90}
        joint_data["upperarm"] = {"tx": aniseed_toolkit.units.to_cm(9), "jointOrientX": 7, "jointOrientY": 50}
        joint_data["lowerarm"] = {"tx": aniseed_toolkit.units.to_cm(24), "jointOrientZ": -20,}
        joint_data["hand"] = {"tx": aniseed_toolkit.units.to_cm(24)}

        joint_data = collections.OrderedDict()
        joint_data["shoulder"] = {}
        joint_data["upperarm"] = {"tx": aniseed_toolkit.units.to_cm(9), "jointOrientX": 7, "jointOrientZ": -50}
        joint_data["lowerarm"] = {"tx": aniseed_toolkit.units.to_cm(24), "jointOrientY": -20,}
        joint_data["hand"] = {"tx": aniseed_toolkit.units.to_cm(24)}

        all_joints = aniseed_toolkit.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=self.option("Location").get(),
            config=self.config,
            parent=parent,
            prefix=self.option("Descriptive Prefix").get(),
        )

        self.input("Shoulder").set(all_joints[0])
        self.input("Hand").set(all_joints[-1])
        upper_twists = []
        lower_twists = []

        if upper_twist_count:
            upper_twists = aniseed_toolkit.joints.create_twist_joints(
                all_joints[1],
                all_joints[2],
                upper_twist_count,
                description=self.option("Descriptive Prefix").get() + "ArmUpperTwist",
                location=self.option("Location").get(),
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Upper Twist Joints").set(upper_twists)

        if lower_twist_count:
            lower_twists = aniseed_toolkit.joints.create_twist_joints(
                all_joints[2],
                all_joints[3],
                lower_twist_count,
                description=self.option("Descriptive Prefix").get() + "ArmLowerTwist",
                location=self.option("Location").get(),
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Lower Twist Joints").set(lower_twists)

    def user_func_create_mirror(self):
        """
        This will create a mirrored version of the component
        """
        aniseed_toolkit.component.mirror(
            component_instance=self,
            transforms=self.all_joints(),
            location_label="Location",
            config=self.config,
            joint_parent=mref.get(self.input("Shoulder").get()).parent().name(),
            input_overrides={"Shoulder": ""},
        )

    def all_joints(self):
        """
        This is a convenience function for returning all the joints that this
        component affects
        """
        # -- Get the start and end point
        root_joint = self.input("Shoulder").get()
        end_joint = self.input("Hand").get()

        if not cmds.objExists(root_joint) or not cmds.objExists(end_joint):
            return []

        # -- Resolve the whole chain betweenm
        arm_joints = aniseed_toolkit.joints.get_between(root_joint, end_joint)

        # -- Include the twisters
        upper_twists = self.input("Upper Twist Joints").get() or []
        lower_twists = self.input("Lower Twist Joints").get() or []
        all_joints = arm_joints + upper_twists + lower_twists

        return [joint for joint in all_joints if joint]

    def setup_spaceswitches(self):
        global_srt_component = self.stack.get_component_by_type("Core : Global Control Root")

        if not global_srt_component:
            print("No global srt found, skipping spaceswitch setup")
            return

        hand_spaceswitch = self.stack.add_component(
            component_type="Augment : Space Switch",
            label=self.label() + " Hand Space Switch",
            parent=self,
            inputs={
                "To Be Driven": self.output("Ik Hand").address(),
                "Attribute Host": self.output("Ik Hand").address(),
            },
        )
        hand_spaceswitch.option("_Data").set(
            {
                "default_space": "World",
                "spaces": [
                    {
                        "target": global_srt_component.output("Main Control").address(),
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": "World",
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    },
                    {
                        "target": self.input("Parent").address(),
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": "Component Parent",
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    },
                    {
                        "target": self.input("Shoulder").address(),
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": "Shoulder",
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    },
                ]
            }
        )
        upvector_spaceswitch = self.stack.add_component(
            component_type="Augment : Space Switch",
            label=self.label() + " Upvector Space Switch",
            parent=self,
            inputs={
                "To Be Driven": self.output("Upvector").address(),
                "Attribute Host": self.output("Upvector").address(),
            },
        )
        upvector_spaceswitch.option("_Data").set(
            {
                "default_space": "Hand",
                "spaces": [
                    {
                        "target": global_srt_component.output("Main Control").address(),
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": "World",
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    },
                    {
                        "target": self.input("Parent").address(),
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": "Parent",
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    },
                    {
                        "target": self.input("Shoulder").address(),
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": "Shoulder",
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    },
                    {
                        "target": self.output("Ik Hand").address(),
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": "Hand",
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    },
                ]
            }
        )

    def _clear_values(self):

        self.prefix: str = ""
        self.location: str = ""
        self.org: str = ""
        self.arm_joints: list[str] = []
        self.chain_direction: "Direction" = None
        self.shoulder_control: "Control" = None
        self.config_control: "Control" = None
        self.upvector_control: "Control" = None
        self.ik_hand_control: "Control" = None
        self.fk_upper_control: "Control" = None
        self.fk_lower_control: "Control" = None
        self.fk_hand_control: "Control" = None

        self.controls: list[str] = []
        self.fk_controls: list[str] = []
        self.ik_controls: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [90, 0, 0]