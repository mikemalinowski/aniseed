import os
import mref
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
        )

        self.declare_option(
            name="Location",
            value="lf",
            group="Naming",
            should_inherit=True,
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
        
        # -- Delcare our options which make it easier and quicker to generate
        # -- a skeleton if needed
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Build Skeleton", value=True, pre_expose=True)
        self.declare_option(name="LinkedGuide", value="", hidden=True)
        
        # -- Declare our outputs so other components can access them
        self.declare_output(
            name="Blended Upper Arm",
        )

        self.declare_output(
            name="Blended Lower Arm",
        )

        self.declare_output(
            name="Blended Hand",
        )
        self.declare_output(
            name="Aligned Hand",
        )

        self.declare_output("Upvector")
        self.declare_output("Ik Hand")

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

    def on_build_started(self) -> None:
        """
        When the build starts, lets ensure we dont have a guide still 
        """
        linked_guide = self.option("LinkedGuide").get()
        if linked_guide and cmds.objExists(linked_guide):
            self.user_func_remove_guide()
    
    def on_enter_stack(self):
        """
        When this enters the stack we can build the skeleton structure
        automatically if requested.
        """
        # -- Read our options
        build_skeleton = self.option("Build Skeleton")
        upper_twist_count = self.option("Upper Twist Count")
        lower_twist_count = self.option("Lower Twist Count")

        # -- To reach here, we have not - so lets mark this as being processed
        # -- regardless of whether or not we need to build the skeleton
        build_skeleton.set_hidden(True)
        upper_twist_count.set_hidden(True)
        lower_twist_count.set_hidden(True)

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

    def on_removed_from_stack(self):
        """
        This is triggered when we remove the item from the stack, so we take
        a moment to clear the joints and reparent any joints from outside
        the component.
        """
        # -- Remove the guide
        self.user_func_remove_guide()

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
            return aniseed.widgets.LocationSelector(self.config)

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

        linked_guide = self.option("LinkedGuide").get()
        if linked_guide and cmds.objExists(linked_guide):
            # -- Depending on whether we have a guide or not, change what we show
            # -- in the actions menu
            menu["Remove Guide"] = functools.partial(self.user_func_remove_guide)
            menu["Toggle Joint Selectability"] = functools.partial(self.user_func_toggle_joint_selectability)
        else:
            menu["Create Guide"] = functools.partial(self.user_func_create_guide)

        menu["Create Mirrored Component"] = functools.partial(self.user_func_create_mirror)
        return menu

    def is_valid(self):
        """
        This gives us the chance to validate the skeleton
        before we commit to building.
        """
        arm_joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Shoulder").get(),
            self.input("Hand").get(),
        )[1:]

        direction = aniseed_toolkit.run(
            "Get Chain Facing Direction",
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

        ikfk_setup = aniseed_toolkit.run(
            "Create Two Bone IKFK",
            parent=self.shoulder_control.ctl,
            root_joint=self.arm_joints[1],
            end_joint=self.arm_joints[-1],
            attribute_host=self.config_control.ctl,
            attribute_name="ikfk",
            constrain=True,
            soft_ik=self.option("Apply Soft Ik").get(),
        )
        for node in ikfk_setup.all_nodes:
            cmds.rename(
                node,
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}Arm{node}",
                    location=self.location,
                ),
            )

        cmds.parentConstraint(
            self.ik_hand_control.ctl,
            ikfk_setup.out_ik_target,
            maintainOffset=True,
        )
        cmds.parentConstraint(
            self.upvector_control.ctl,
            ikfk_setup.out_ik_upvector,
            maintainOffset=False,
        )

        for idx, fk_marker in enumerate(ikfk_setup.out_fk_joints):
            cmds.parentConstraint(
                self.fk_controls[idx],
                fk_marker,
                maintainOffset=True,
            )

        # -- Hook up the visibility attributes
        cmds.addAttr(
            self.config_control.ctl,
            shortName="show_ik",
            attributeType='float',
            minValue=0,
            maxValue=1,
            defaultValue=1,
            keyable=True,
        )
        cmds.addAttr(
            self.config_control.ctl,
            shortName="show_fk",
            attributeType='float',
            minValue=0,
            maxValue=1,
            defaultValue=0,
            keyable=True,
        )
        ik_visibility_attribute = f"{self.config_control.ctl}.show_ik"
        fk_visibility_attribute = f"{self.config_control.ctl}.show_fk"

        for ik_control in self.ik_controls:
            ik_control = aniseed_toolkit.run(
                "Get Control",
                ik_control,
            )
            cmds.connectAttr(
                f"{self.config_control.ctl}.show_ik",
                f"{ik_control.off}.visibility",
                force=True,
            )

        for fk_control in self.fk_controls:
            fk_control = aniseed_toolkit.run(
                "Get Control",
                fk_control,
            )
            cmds.connectAttr(
                f"{self.config_control.ctl}.show_fk",
                f"{fk_control.off}.visibility",
                force=True,
            )

        self.nk_joints = ikfk_setup.out_blend_joints
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
            translation=aniseed_toolkit.run(
                "Calculate Upvector Position",
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
        group = "Arm_%s_%s" % (
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
                aniseed_toolkit.run(
                    "Rotate Shapes",
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
                aniseed_toolkit.run(
                    "Rotate Shapes",
                    twist,
                    *self.shape_rotation,
                )

    def _set_outputs(self):

        self.output("Upvector").set(self.upvector_control.ctl)
        self.output("Ik Hand").set(self.ik_hand_control.ctl)

        self.output("Blended Upper Arm").set(self.nk_joints[0])
        self.output("Blended Lower Arm").set(self.nk_joints[1])
        self.output("Blended Hand").set(self.nk_joints[2])

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
        joint_data["upperarm"] = {"tx": 9, "jointOrientX": 7, "jointOrientY": 50}
        joint_data["lowerarm"] = {"tx": 24, "jointOrientZ": -20,}
        joint_data["hand"] = {"tx": 24}

        joint_data = collections.OrderedDict()
        joint_data["shoulder"] = {}
        joint_data["upperarm"] = {"tx": 9, "jointOrientX": 7, "jointOrientZ": -50}
        joint_data["lowerarm"] = {"tx": 24, "jointOrientY": -20,}
        joint_data["hand"] = {"tx": 24}

        all_joints = aniseed_toolkit.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=self.option("Location").get(),
            config=self.config,
            parent=parent,
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
                description=self.option("Descriptive Prefix").get() + "UpperTwist",
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
                description=self.option("Descriptive Prefix").get() + "LowerTwist",
                location=self.option("Location").get(),
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Lower Twist Joints").set(lower_twists)

        # -- Immediately enter guide mode
        guides = self.user_func_create_guide()

        # -- If we have a parent, then match the translation to it, this
        # -- just makes the riggers life a little easier as the component
        # -- will show in a contextually relevant locaiton.
        aniseed_toolkit.transformation.snap_position(guides[0], parent)

        # -- Add our joints to a deformers set. If we're given twists, then we
        # -- use them + the hand. Otherwise we use the arm joints themselves.
        deformers = all_joints
        if upper_twist_count:
            deformers = upper_twists + lower_twists + [all_joints[3]]
        aniseed_toolkit.sets.add_to(deformers, set_name="deformers")

    def user_func_create_guide(self):
        """
        This will generate a guide, making it easier to manipulate the
        skeleton.
        """
        # -- Check if the guide already exists first
        if self.has_guide():
            return []

        guide_org = mref.create("transform", name="arm_guide", parent=None)

        # -- Create the guides for the joints (replicate chain and apply ik?)
        root_joint = self.input("Shoulder").get()
        hand_joint = self.input("Hand").get()
        arm_joints = aniseed_toolkit.joints.get_between(root_joint, hand_joint)

        # -- Create the shoulder guide
        shoulder_guide = aniseed_toolkit.guide.create(
            root_joint,
            parent=guide_org.full_name()
        )
        # -- Scale the shape of the first guide (its always easier for the rigger
        # -- if the first guide of a component is larger)
        aniseed_toolkit.shapes.scale(shoulder_guide, scale_by=1.5)

        # -- Create the guide setup for the ik
        ik_org, guides = aniseed_toolkit.guide.create_ik_guide(
            start=arm_joints[1],
            end=arm_joints[3],
            parent=shoulder_guide,
            constrain_end_orientation=True,
            link_to=shoulder_guide,
        )

        # -- Insert the shoulder guide
        guides.insert(0, shoulder_guide)

        # -- Ensure the twisters are tweened
        aniseed_toolkit.guide.create_tweens(
            drive_these=self.input("Upper Twist Joints").get(),
            from_this=guides[1],
            to_this=guides[2],
            parent=guide_org.full_name(),
        )
        aniseed_toolkit.guide.create_tweens(
            drive_these=self.input("Lower Twist Joints").get(),
            from_this=guides[2],
            to_this=guides[3],
            parent=guide_org.full_name(),
        )
        # -- Finally make the joints unselectable
        aniseed_toolkit.joints.make_referenced(self.all_joints())

        self.option("LinkedGuide").set(guide_org.name())

        # -- If there is a parent of the root then we constrain our
        # -- setup to that
        root_joint = mref.get(root_joint)
        if root_joint.parent():
            cmds.parentConstraint(
                root_joint.parent().full_name(),
                guide_org.full_name(),
                maintainOffset=True,
            )

        return guides

    def user_func_remove_guide(self):
        """
        This will remove the guide from the scene
        """
        if not self.has_guide():
            return

        # -- Make sure all joints are selectable
        aniseed_toolkit.joints.unreference(self.all_joints())

        linked_guide = self.option("LinkedGuide").get()

        if linked_guide and cmds.objExists(linked_guide):
            with aniseed_toolkit.joints.HeldTransforms(self.all_joints()):
                cmds.delete(linked_guide)
            self.option("LinkedGuide").set(None)

    def user_func_toggle_joint_selectability(self):
        """
        This will make all the joints either unselectable or selectable
        """
        joints = self.all_joints()
        if aniseed_toolkit.joints.is_referenced(joints[0]):
            aniseed_toolkit.joints.unreference(joints)
        else:
            aniseed_toolkit.joints.make_referenced(joints)

    def user_func_create_mirror(self):
        """
        This will create a mirrored version of the component
        """
        location = self.option("Location").get()

        if location not in [self.config.left, self.config.right]:
            print("You can only mirror if the component is left or right")
            return

        # -- Get the opposite location
        location = self.config.left if location == self.config.right else self.config.right

        # -- Select the parent joint and duplicate ourselves (setting hte label so
        # -- we know its mirrored
        cmds.select(cmds.listRelatives(self.input("Shoulder").get(), parent=True)[0])
        mirrored_component = self.duplicate(
            input_overrides={"Shoulder": ""},
            option_overrides={"Location": location, "LinkedGuide": ""},
        )
        mirrored_component.set_label(f"{self.label()} (Mirrored)")

        # -- Get the two guides, as we need to match them
        this_guide = self.option("LinkedGuide").get()
        mirrored_guide = mirrored_component.option("LinkedGuide").get()

        # -- Get all the guide elements
        guides_from_this_component = aniseed_toolkit.tagging.all_children(this_guide, "guide")
        guides_from_mirrored_component = aniseed_toolkit.tagging.all_children(mirrored_guide, "guide")

        # -- Perform the match
        for guide, mirrored_guide in zip(guides_from_this_component, guides_from_mirrored_component):
            mref.get(mirrored_guide).match_to(mref.get(guide))

        # -- Now we do an in-place mirror
        aniseed_toolkit.mirror.global_mirror(
            transforms=guides_from_mirrored_component,
            name_replacement={},
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
        upper_twists = self.input("Upper Twist Joints").get()
        lower_twists = self.input("Lower Twist Joints").get()
        all_joints = arm_joints + upper_twists + lower_twists

        return [joint for joint in all_joints if joint]

    def has_guide(self):
        """
        Checks whether this has a valid guide or not
        """
        # -- Check if the guide already exists first
        guide = self.option("LinkedGuide").get()
        if guide and cmds.objExists(guide):
            return True
        return False
