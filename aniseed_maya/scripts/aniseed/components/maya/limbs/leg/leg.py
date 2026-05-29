import os
import uuid

import mref
import snappy
import aniseed
import collections
import qtility
import functools
import aniseed_toolkit
from maya import cmds


class LegComponent(aniseed.RigComponent):
    """
    This is some documentation that the user will see. You should adjust the guides...
    """
    identifier = "Limb : Leg"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    _LABELS = [
        "Upper",
        "Lower",
        "Foot",
        "Toe",
    ]
    guide_tags = [
        "Ball",
        "Heel",
        "Toe",
        "Inner",
        "Outer",
    ]

    default_guide_transforms = {
        "Ball": {},
        "Heel": {"tz": -2, "rz": 90},
        "Toe": {"tz": 2, "rx": 180, "rz": 90},
        "Inner": {"tx": -2, "rx": 90, "rz": 90},
        "Outer": {"tx": 2, "rx": -90, "rz": 90},
    }

    def __init__(self, *args, **kwargs):
        super(LegComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Leg Root",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Toe",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Upper Twist Joints",
            description="All upper twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_input(
            name="Lower Twist Joints",
            description="All lower twist joints",
            validate=False,
            group="Optional Twist Joints",
        )

        for guide in self.guide_tags:
            self.declare_input(
                name=f"{guide} Guide",
                description=f"Transform for the {guide} Control",
                value="",
                group="Guides",
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
            name="Align Foot To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Paddles To Foot",
            value=True,
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
            name="Upvector Distance Multiplier",
            value=1,
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

        # -- These options are hidden and for intialisation only
        self.declare_option(name="Upper Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Lower Twist Count", value=2, pre_expose=True)
        self.declare_option(name="Build Skeleton", value=True, pre_expose=True)

        self.declare_output(name="Blended Upper Leg")
        self.declare_output(name="Blended Lower Leg")
        self.declare_output(name="Blended Foot")
        self.declare_output(name="Blended Toe")
        self.declare_output(name="Ik Foot")
        self.declare_output(name="Upvector")

        # -- Declare our build properties - this is only required because i have
        # -- chosen within this component to break up the long build script
        # -- into functions, and therefore we use this to access items created
        # -- from other functions.
        self.prefix: str = ""
        self.location: str = ""
        self.leg_joints: list[str] = []
        self.org: str = ""
        self.config_control = None
        self.upvector_control = None
        self.ik_root_control = None
        self.ik_foot_control = None
        self.ik_heel_control = None
        self.ik_foot_control = None
        self.ik_toe_control = None
        self.ik_pivot_endpoint = ""
        self.pivot_controls = []

        self.controls: list[str] = []
        self.fk_controls: list = []
        self.ik_controls: list = []
        self.ik_bindings: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [0, 0, 0]
        self.shape_flip = False

    def on_enter_stack(self):

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

        location = self.option("Location").get()

        # -- Create the guides
        for guide_tag in self.guide_tags:
            guide = cmds.createNode(
                "transform",
                name=self.config.generate_name(
                    classification="gde",
                    description=guide_tag,
                    location=location,
                )
            )
            aniseed_toolkit.shapes.load_shape(guide, "core_rotator")
            self.input(f"{guide_tag} Guide").set(guide)

            # -- Set the guides default transforms
            for attribute, value in self.default_guide_transforms[guide_tag].items():
                cmds.setAttr(f"{guide}.{attribute}", value)

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent(tags=["fk root", "fk hip", "hip"])

        if apply_spaceswitches.get():
            self.setup_spaceswitches()

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we need to remove the
        guide and bones too.
        """
        # -- Remove the joints (re-parenting any children)
        new_parent = mref.get(self.input("Leg Root").get()).parent()
        aniseed_toolkit.joints.reparent_unknown_children(self.all_joints(), new_parent)

        # -- Now delete our leg chain and joints
        cmds.delete(self.input("Leg Root").get())
        cmds.delete(self.all_guides())

    def input_widget(self, requirement_name):
        """
        Return bespoke widgets for certain input types
        """
        if requirement_name.endswith(" Guide"):
            return aniseed.widgets.ObjectSelector()

        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name: str):
        """
        Return bespoke widgets for options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    # noinspection DuplicatedCode
    def run(self):

        # -- Ensure our properties are cleared
        self._clear_values()

        # -- Determine the options we're building with
        self.prefix = self.option('Descriptive Prefix').get()
        self.location = self.option("Location").get()

        self.leg_joints = aniseed_toolkit.joints.get_between(
            start=self.input("Leg Root").get(),
            end=self.input("Toe").get(),
        )

        self.org = aniseed_toolkit.transforms.create(
            classification=self.config.organisational,
            description=f"{self.prefix}Leg",
            location=self.location,
            config=self.config,
            parent=self.input("Parent").get()
        )

        self.create_controls()
        self.create_ik()
        self.create_nk()
        self.create_snap()
        self.create_twists()
        self.set_outputs()

    def user_functions(self):
        """
        This is where we define what functionality we want to actually
        expose to the user
        """
        menu = super(LegComponent, self).user_functions()

        # -- Only show the skeleton creation tools if we dont have a skeleton
        leg_joint = self.input("Leg Root").get()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        if not leg_joint or not cmds.objExists(leg_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)
            return menu

        menu["Create Mirror"] = functools.partial(self.user_func_create_mirror)
        return menu

    def is_valid(self) -> bool:
        """
        Before building, lets check that we have all the information we require
        for building.
        """
        # -- To be valid we expect there to be specifically four joints
        all_joints = self.all_joints()

        if len(all_joints) < 4:
            print("Expected four joints for leg")
            return False

        # -- We also expect that the bones to be facing down X - at least
        # -- between the upper leg and the foot
        facing_dir = aniseed_toolkit.direction.get_chain_facing_direction(
            all_joints[0],
            all_joints[2],
        )
        if facing_dir != facing_dir.NegativeX and facing_dir != facing_dir.PositiveX:
            print("The leg must be aligned to the X axis")
            return False

        return True

    def create_controls(self):
        """
        This function will create all the controls for the leg
        """
        # -- Add the configuration control
        self.config_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}LegConfig",
            location=self.location,
            parent=self.org,
            shape="core_lollipop",
            config=self.config,
            match_to=self.leg_joints[0],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        # -- Create the upvector control for the arm
        self.upvector_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}LegUpvector",
            location=self.location,
            parent=self.org,
            shape="core_sphere",
            config=self.config,
            match_to=self.leg_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )
        self.ik_controls.append(self.upvector_control.ctl)

        cmds.xform(
            self.upvector_control.org,
            translation=aniseed_toolkit.transformation.calculate_upvector_position(
                point_a=self.leg_joints[0],
                point_b=self.leg_joints[1],
                point_c=self.leg_joints[2],
                length=self.option("Upvector Distance Multiplier").get(),
            ),
            worldSpace=True,
        )

        if self.option("Align Upvector To World").get():
            cmds.xform(
                self.upvector_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- Now create the main IK control
        self.ik_foot_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}Foot",
            location=self.location,
            parent=self.org,
            shape="core_paddle",
            config=self.config,
            shape_scale=40.0,
            rotate_shape=[0, 90, 0] if self.shape_flip else [0, -90, 0],
            match_to=self.input("Ball Guide").get()
        )
        self.ik_controls.append(self.ik_foot_control.ctl)

        if self.option("Align Foot To World").get():
            cmds.xform(
                self.ik_foot_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- Create the pivot control setup
        self.ik_pivot_endpoint, self.pivot_controls = self.create_ik_pivots()

        # -- Add the heel control
        self.ik_heel_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}Heel",
            location=self.location,
            parent=self.ik_pivot_endpoint,
            shape="core_paddle",
            config=self.config,
            match_to=self.leg_joints[-1],
            shape_scale=10,
            rotate_shape=[90, 0, 0],
        )
        self.ik_controls.append(self.ik_heel_control.ctl)

        if self.option("Align Paddles To Foot").get():
            cmds.xform(
                self.ik_heel_control.org,
                rotation=cmds.xform(
                    self.ik_foot_control.ctl,
                    query=True,
                    rotation=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

        # -- Add the toe control
        self.ik_toe_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}Toe",
            location=self.location,
            parent=self.ik_pivot_endpoint,
            shape="core_paddle",
            config=self.config,
            match_to=self.leg_joints[-1],
            shape_scale=10,
            rotate_shape=[180, 0, 0],
        )
        self.ik_controls.append(self.ik_toe_control.ctl)

        if self.option("Align Paddles To Foot").get():
            cmds.xform(
                self.ik_toe_control.org,
                rotation=cmds.xform(
                    self.ik_foot_control.ctl,
                    query=True,
                    rotation=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

        fk_parent = self.org
        self.fk_controls = []

        for idx, joint in enumerate(self.leg_joints):

            fk_control = aniseed_toolkit.control.create(
                description=f"{self.prefix}{self._LABELS[idx]}FK",
                location=self.location,
                parent=fk_parent,
                shape="core_paddle",
                config=self.config,
                match_to=joint,
                shape_scale=20.0,
                rotate_shape=self.shape_rotation,
            )
            self.fk_controls.append(fk_control.ctl)
            fk_parent = fk_control.ctl

        # -- Set up the space switches on teh fk controls
        if self.option("Apply World Fk Switches").get():
            aniseed_toolkit.space.setup_fk_worldspace_switches(self.fk_controls, rig=self.rig)

    def create_ik(self):
        """
        This creates the IK solving for the leg
        """

        # -- Create the ik root control
        self.ik_root_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}LegIKRoot",
            location=self.location,
            shape="core_cube",
            parent=self.org,
            match_to=self.leg_joints[0],
            config=self.config,
        )

        replicated_joints = aniseed_toolkit.joints.replicate_chain(
            from_this=self.leg_joints[0],
            to_this=self.leg_joints[2],
            parent=self.ik_root_control.ctl,
        )

        # -- Rename the ik joints
        for joint in replicated_joints:
            joint = cmds.rename(
                joint,
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}LegIK",
                    location=self.location,
                )
            )
            print("makde with location : %s " % self.location)
            self.ik_joints.append(joint)

        # -- Ensure all the rotation values are on the joint
        # -- orients to allow for correct assignment of the
        # -- ik vector
        aniseed_toolkit.joints.move_rotations_to_orients(self.ik_joints)

        # -- Create the Ik setup
        handle, effector = cmds.ikHandle(
            startJoint=self.ik_joints[0],
            endEffector=self.ik_joints[-1],
            solver='ikRPsolver',
            priority=1,
        )

        # -- Hide the ik handle as we dont want the animator
        # -- to interact with it directly
        cmds.setAttr(
            f"{handle}.visibility",
            0,
        )

        # -- Apply the upvector constraint
        cmds.poleVectorConstraint(
            self.upvector_control.ctl,
            handle,
            weight=1,
        )

        # -- Parent the ikhandle under the heel control so it
        # -- moves along with it
        cmds.parent(
            handle,
            self.ik_heel_control.ctl,
        )

        # -- Create the guide line
        aniseed_toolkit.guide.link(
            self.upvector_control.ctl,
            self.ik_joints[1],
        )

        if self.option("Apply Soft Ik").get():

            root_marker = cmds.createNode(
                "transform",
                name=self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}LegIKMarker",
                    location=self.location,
                )
            )

            cmds.parent(
                root_marker,
                self.ik_root_control.ctl,
            )

            cmds.xform(
                root_marker,
                matrix=cmds.xform(
                    self.ik_joints[0],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            tip_marker = cmds.createNode("transform")

            cmds.parent(
                tip_marker,
                self.ik_heel_control.ctl, #self.ik_pivot_endpoint,
            )

            cmds.xform(
                tip_marker,
                matrix=cmds.xform(
                    self.ik_joints[-1],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )
            aniseed_toolkit.rigging.create_two_bone_soft_ik(
                root=root_marker,
                target=tip_marker,
                second_joint=self.ik_joints[-2],
                third_joint=self.ik_joints[-1],
                host=self.ik_foot_control.ctl,
            )

        # -- We need to constrain the end joint in rotation to the
        # -- hand control, because the ik does not do that.
        cmds.parentConstraint(
            self.ik_pivot_endpoint,
            self.ik_joints[-1],
            skipTranslate=['x', 'y', 'z'],
        )

        # -- These are essentially what the nk chain should map to
        self.ik_bindings = [
            self.ik_joints[0],
            self.ik_joints[1],
            self.ik_heel_control.ctl,
            self.ik_toe_control.ctl,
        ]

    def create_nk(self):
        """
        NK is the chain that is constrained between the IK and the FK
        """
        blend_chain_setup = aniseed_toolkit.rigging.create_blend_chain(
            parent=self.org,
            transforms_a=self.ik_bindings,
            transforms_b=self.fk_controls,
            attribute_host=self.config_control.ctl,
            attribute_name="ikfk",
            match_transforms=self.leg_joints,
        )
        for idx, blend_joint in enumerate(blend_chain_setup.blend_joints):
            blend_joint.rename(
                self.config.generate_name(
                        classification="mech",
                        description=f"{self.prefix}LegNK",
                        location=self.location,
                    ),
            )
            self.nk_joints.append(blend_joint.name())

            cmds.parentConstraint(
                self.nk_joints[idx],
                self.leg_joints[idx],
                maintainOffset=True,
            )

            cmds.scaleConstraint(
                self.nk_joints[idx],
                self.leg_joints[idx],
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

    def create_snap(self):
        """
        Snap is the mechanism for IK/FK snapping
        """
        group = "IKFK_%s_%s" % (
            self.prefix + "Leg",
            self.location,
        )

        snappy.new(
            node=self.ik_foot_control.ctl,
            target=self.nk_joints[2],
            group=group,
        )

        snappy.new(
            node=self.upvector_control.ctl,
            target=self.nk_joints[1],
            group=group,
        )

        for pivot_control in self.pivot_controls:
            # -- We leave the target blank for these - which meanas the
            # -- controls will just get zero'd
            snappy.new(
                node=pivot_control,
                target=None,
                group=group,
            )

        for idx, fk_control in enumerate(self.fk_controls):
            snappy.new(
                node=fk_control,
                target=self.nk_joints[idx],
                group=group,
            )

        for attribute_name in self.guide_tags:
            attribute_name = attribute_name.lower().split(" ")[0] + "_roll"

            snappy.new_forced_attribute(
                node=self.ik_foot_control.ctl,
                attribute_name=attribute_name,
                attribute_value=0,
                group=group,
            )

    def create_twists(self):

        upper_twist_joints = self.input("Upper Twist Joints").get()
        lower_twist_joints = self.input("Lower Twist Joints").get()

        if upper_twist_joints:
            twist_component = self.rig.component_library.request("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(upper_twist_joints)
            twist_component.input("Parent").set(self.ik_root_control.ctl)
            twist_component.input("Root").set(self.nk_joints[0])
            twist_component.input("Tip").set(self.nk_joints[1])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set(self.prefix+"LegUpperTwist")
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
            twist_component.option("Descriptive Prefix").set(self.prefix+"LegLowerTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                aniseed_toolkit.shapes.rotate(
                    twist,
                    *self.shape_rotation,
                )

    def set_outputs(self):

        self.output("Upvector").set(self.upvector_control.ctl)
        self.output("Ik Foot").set(self.ik_foot_control.ctl)
        self.output("Blended Upper Leg").set(self.nk_joints[0])
        self.output("Blended Lower Leg").set(self.nk_joints[1])
        self.output("Blended Foot").set(self.nk_joints[2])
        self.output("Blended Toe").set(self.nk_joints[3])

    def create_ik_pivots(self):

        aniseed_toolkit.attributes.add_separator(self.ik_foot_control.ctl)

        controls = list()

        last_parent = self.ik_foot_control.ctl

        for pivot_tag in self.guide_tags:

            description = f"{pivot_tag.lower()}_roll"

            prefix = ""
            if self.prefix:
                prefix = self.prefix + "_"

            pivot_control = aniseed_toolkit.control.create(
                description=f"{prefix}{description}",
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
                match_to=self.input(f"{pivot_tag} Guide").get()
            )

            parameter_pivot = aniseed_toolkit.transforms.create(
                classification="piv",
                description=f"{prefix}{description}",
                location=self.option("Location").get(),
                config=self.config,
                parent=pivot_control.ctl,
                match_to=pivot_control.ctl,
            )

            # -- Add the parameter to the foot control
            cmds.addAttr(
                self.ik_foot_control.ctl,
                shortName=description,
                attributeType="float",
                defaultValue=0,
                keyable=True,
            )

            cmds.connectAttr(
                f"{self.ik_foot_control.ctl}.{description}",
                f"{parameter_pivot}.rotateY",
            )

            controls.append(pivot_control.ctl)
            last_parent = parameter_pivot

        return last_parent, controls

    def user_func_create_mirror(self):
        aniseed_toolkit.component.mirror(
            component_instance=self,
            transforms=self.all_guides() + self.all_joints(),
            location_label="Location",
            config=self.config,
            joint_parent=mref.get(self.input("Leg Root").get()).parent().name(),
            input_overrides={"Leg Root": ""},
        )

    def user_func_create_skeleton(self, parent=None, upper_twist_count=None, lower_twist_count=None):

        # -- Resovle the parent. The parent variable will change throughout
        # -- the course of the function but the component parent will
        # -- remain the same.
        parent = aniseed_toolkit.mutils.first_selected()

        if upper_twist_count is None:
            upper_twist_count = qtility.request.text(
                title="Upper Twist Count",
                message="How many twist joints do you want on the upper leg?"
            )
            upper_twist_count = int(upper_twist_count)

        if lower_twist_count is None:
            lower_twist_count = qtility.request.text(
                title="Upper Twist Count",
                message="How many twist joints do you want on the lower leg?"
            )
            lower_twist_count = int(lower_twist_count)
        #
        location = self.option("Location").get()

        # -- Joint transform attributes
        joint_data = collections.OrderedDict()
        joint_data["UpperLeg"] = {"jointOrientX": 90, "jointOrientY": -4, "jointOrientZ": -90}
        joint_data["LowerLeg"] = {"tx": aniseed_toolkit.units.to_cm(42), "jointOrientZ": -11}
        joint_data["Foot"] = {"tx": aniseed_toolkit.units.to_cm(42), "jointOrientZ": 55}
        joint_data["Toe"] = {"tx": aniseed_toolkit.units.to_cm(10), "jointOrientZ": 42}

        all_joints = aniseed_toolkit.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=location,
            config=self.config,
            parent=None,
            prefix=self.option("Descriptive Prefix").get(),
            # subtract_label="Leg",
        )
        if parent:
            cmds.parent(all_joints[0], parent)
            cmds.xform(
                all_joints[0],
                translation=cmds.xform(
                    parent,
                    query=True,
                    translation=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

        self.input("Leg Root").set(all_joints[0])
        self.input("Toe").set(all_joints[-1])
        upper_twists = []
        lower_twists = []

        if upper_twist_count:
            upper_twists = aniseed_toolkit.joints.create_twist_joints(
                all_joints[0],
                all_joints[1],
                upper_twist_count,
                description=self.option("Descriptive Prefix").get() + "LegUpperTwist",
                location=self.option("Location").get(),
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Upper Twist Joints").set(upper_twists)

        if lower_twist_count:
            lower_twists = aniseed_toolkit.joints.create_twist_joints(
                all_joints[1],
                all_joints[2],
                lower_twist_count,
                description=self.option("Descriptive Prefix").get() + "LegLowerTwist",
                location=self.option("Location").get(),
                config=self.config,
                down_bone_axis="x",
            )
            self.input("Lower Twist Joints").set(lower_twists)

    def all_joints(self):

        # -- Get the start and end point
        root_joint = self.input("Leg Root").get()
        toe_joint = self.input("Toe").get()

        if not cmds.objExists(root_joint) or not cmds.objExists(toe_joint):
            return []

        # -- Resolve the whole chain betweenm
        leg_joints = aniseed_toolkit.joints.get_between(root_joint, toe_joint)

        # -- Include the twisters
        upper_twists = self.input("Upper Twist Joints").get() or []
        lower_twists = self.input("Lower Twist Joints").get() or []
        all_joints = leg_joints + upper_twists + lower_twists

        return [joint for joint in all_joints if joint]

    def all_guides(self):
        results = []
        for guide_tag in self.guide_tags:
            results.append(self.input(f"{guide_tag} Guide").get())
        return results

    def setup_spaceswitches(self):
        global_srt_component = self.stack.get_component_by_type("Core : Global Control Root")

        if not global_srt_component:
            print("No global srt found, skipping spaceswitch setup")
            return

        foot_spaceswitch = self.stack.add_component(
            component_type="Augment : Space Switch",
            label=self.label() + " Foot Space Switch",
            parent=self,
            inputs={
                "To Be Driven": self.output("Ik Foot").address(),
                "Attribute Host": self.output("Ik Foot").address(),
            },
        )
        foot_spaceswitch.option("_Data").set(
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
                        "label": "Parent",
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
                "default_space": "Foot",
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
                        "target": self.output("Ik Foot").address(),
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": "Foot",
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    },
                ]
            }
        )

    def _clear_values(self):
        self.prefix: str = ""
        self.location: str = ""
        self.leg_joints: list[str] = []
        self.org: str = ""
        self.config_control = None
        self.upvector_control = None
        self.ik_root_control = None
        self.ik_foot_control = None
        self.ik_heel_control = None
        self.ik_foot_control = None
        self.ik_toe_control = None
        self.ik_pivot_endpoint = ""
        self.pivot_controls = []

        self.controls: list[str] = []
        self.fk_controls: list = []
        self.ik_controls: list = []
        self.ik_bindings: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [0, 0, 0]
        self.shape_flip = False
