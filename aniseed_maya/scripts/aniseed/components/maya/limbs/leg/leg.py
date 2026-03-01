import os
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

        self.declare_option(
            name="GuideData",
            value=self.default_guide_data(),
            hidden=True,
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
            name="Align Foot To World",
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

    def on_build_started(self) -> None:
        # -- Remove the guide if there is one

        guide_data = self.option("GuideData").get()
        linked_guide = guide_data["LinkedGuide"]

        if linked_guide and cmds.objExists(linked_guide):
            self.user_func_remove_guide()

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we need to remove the
        guide and bones too.
        """
        # -- Remove the guide
        self.user_func_remove_guide()

        # -- Remove the joints (re-parenting any children)
        new_parent = mref.get(self.input("Leg Root").get()).parent()
        aniseed_toolkit.joints.reparent_unknown_children(self.all_joints(), new_parent)

        # -- Now delete our leg chain and joints
        cmds.delete(self.input("Leg Root").get())

    def input_widget(self, requirement_name):
        """
        Return bespoke widgets for certain input types
        """
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

        # -- Determine the options we're building with
        self.prefix = self.option('Descriptive Prefix').get()
        self.location = self.option("Location").get()

        self.leg_joints = aniseed_toolkit.run(
            "Get Joints Between",
            start=self.input("Leg Root").get(),
            end=self.input("Toe").get(),
        )

        self.org = aniseed_toolkit.run(
            "Create Basic Transform",
            classification=self.config.organisational,
            description=self.prefix + "Leg",
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

        # -- Check if we have a guide
        guide_data = self.option("GuideData").get()
        linked_guide = guide_data["LinkedGuide"]

        if linked_guide and cmds.objExists(linked_guide):
            # -- Depending on whether we have a guide or not, change what we show
            # -- in the actions menu
            menu["Remove Guide"] = functools.partial(self.user_func_remove_guide)
            menu["Toggle Joint Selectability"] = functools.partial(self.user_func_toggle_joint_selectability)
            menu["Create Mirrored Component"] = functools.partial(self.user_func_create_mirror)
        else:
            menu["Create Guide"] = functools.partial(self.user_func_create_guide)

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
        facing_dir = aniseed_toolkit.run(
            "Get Chain Facing Direction",
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
        guide_data = self.option("GuideData").get()

        # -- Add the configuration control
        self.config_control = aniseed_toolkit.run(
            "Create Control",
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
        self.upvector_control = aniseed_toolkit.run(
            "Create Control",
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
            translation=aniseed_toolkit.run(
                "Calculate Upvector Position",
                point_a=self.leg_joints[0],
                point_b=self.leg_joints[1],
                point_c=self.leg_joints[2],
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

        # -- Now create the main IK control
        self.ik_foot_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.prefix}Foot",
            location=self.location,
            parent=self.org,
            shape="core_paddle",
            config=self.config,
            shape_scale=40.0,
            rotate_shape=[0, 90, 0] if self.shape_flip else [0, -90, 0],
        )
        self.ik_controls.append(self.ik_foot_control.ctl)

        cmds.xform(
            self.ik_foot_control.org,
            matrix=guide_data["Markers"]["ball"],
            worldSpace=True,
        )

        if self.option("Align Foot To World").get():
            cmds.xform(
                self.ik_foot_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- Create the pivot control setup
        self.ik_pivot_endpoint, self.pivot_controls = self.create_ik_pivots()

        # -- Add the heel control
        self.ik_heel_control = aniseed_toolkit.run(
            "Create Control",
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
        self.ik_toe_control = aniseed_toolkit.run(
            "Create Control",
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

            fk_control = aniseed_toolkit.run(
                "Create Control",
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

    def create_ik(self):
        """
        This creates the IK solving for the leg
        """
        replicated_joints = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.leg_joints[0],
            to_this=self.leg_joints[2],
            parent=self.org,
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
            self.ik_joints.append(joint)

        # -- Ensure all the rotation values are on the joint
        # -- orients to allow for correct assignment of the
        # -- ik vector
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            self.ik_joints,
        )

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

        if self.option("Apply Soft Ik").get():

            root_marker = cmds.createNode("transform")

            cmds.parent(
                root_marker,
                self.org,
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
                self.ik_pivot_endpoint,
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
            aniseed_toolkit.run(
                "Create Soft Ik",
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

        blend_chain_setup = aniseed_toolkit.run(
            "Create Blend Chain",
            parent=self.org,
            transforms_a=self.ik_bindings,
            transforms_b=self.fk_controls,
            attribute_host=self.config_control.ctl,
            attribute_name="ikfk",
            match_transforms=self.leg_joints,
        )
        for idx, blend_joint in enumerate(blend_chain_setup.out_blend_joints):
            self.nk_joints.append(
                cmds.rename(
                    blend_joint,
                    self.config.generate_name(
                        classification="mech",
                        description=f"{self.prefix}LegNK",
                        location=self.location,
                    )
                ),
            )
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

    def create_snap(self):
        """
        Snap is the mechanism for IK/FK snapping
        """
        group = "Leg_%s_%s" % (
            self.prefix,
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

        pivot_attributes = [
            "ball",
            "heel",
            "tip",
            "inner",
            "outer",
        ]
        for attribute_name in pivot_attributes:
            snappy.new_forced_attribute(
                node=self.ik_foot_control.ctl,
                attribute_name=attribute_name.title(),
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
            twist_component.input("Parent").set(self.org)
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

    def set_outputs(self):

        self.output("Upvector").set(self.upvector_control.ctl)
        self.output("Ik Foot").set(self.ik_foot_control.ctl)
        self.output("Blended Upper Leg").set(self.nk_joints[0])
        self.output("Blended Lower Leg").set(self.nk_joints[1])
        self.output("Blended Foot").set(self.nk_joints[2])
        self.output("Blended Toe").set(self.nk_joints[3])


    def user_func_create_guide(self) -> list[str]:

        if self.has_guide():
            return []

        guide_org = mref.create("transform", name="leg_guide", parent=None)

        # -- Create the guides for the joints (replicate chain and apply ik?)
        root_joint = self.input("Leg Root").get()
        toe_joint = self.input("Toe").get()
        leg_joints = aniseed_toolkit.joints.get_between(root_joint, toe_joint)

        # -- Create the guide setup for the ik
        ik_org, guides = aniseed_toolkit.guide.create_ik_guide(
            start=leg_joints[0],
            end=leg_joints[2],
            parent=guide_org.full_name(),
            constrain_end_orientation=True,
        )

        # -- Scale the shape of the first guide (its always easier for the rigger
        # -- if the first guide of a component is larger)
        aniseed_toolkit.shapes.scale(guides[0], scale_by=1.5)

        # -- Now we need to create a guide for the foot
        toe_guide = aniseed_toolkit.guide.create(
            joint=leg_joints[-1],
            parent=guides[-1],
            link_to=guides[-1],
        )

        # -- Ensure the twisters are tweened
        if self.input("Upper Twist Joints").get():
            aniseed_toolkit.guide.create_tweens(
                drive_these=self.input("Upper Twist Joints").get(),
                from_this=guides[0],
                to_this=guides[1],
                parent=guide_org.full_name(),
            )

        if self.input("Lower Twist Joints").get():
            aniseed_toolkit.guide.create_tweens(
                drive_these=self.input("Lower Twist Joints").get(),
                from_this=guides[1],
                to_this=guides[2],
                parent=guide_org.full_name(),
            )

        # -- Now create the guide for the foot roll pivots
        guide_base = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="gde",
            description="LegGuide",
            location=self.option("Location").get(),
            config=self.config,
            match_to=self.input("Toe").get(),
            parent=guide_org.full_name(),
        )

        # -- Constrain the position of the base in Z and X
        cmds.pointConstraint(
            guides[-1],
            guide_base,
            skip=["y"],
        )
        cmds.xform(
            guide_base,
            rotation=(0, 0, 0),
            worldSpace=True,
        )

        guide_data = self.option("GuideData").get()

        for marker_name, marker_matrix in guide_data["Markers"].items():

            marker = aniseed_toolkit.run(
                "Create Basic Transform",
                classification="gde",
                description=marker_name.title(),
                location=self.option("Location").get(),
                config=self.config,
                parent=guide_base,
            )
            aniseed_toolkit.tagging.tag(marker, "guide")

            cmds.xform(
                marker,
                matrix=marker_matrix,
                worldSpace=True,
            )
            aniseed_toolkit.run(
                "Apply Shape",
                node=marker,
                data="core_symbol_rotator",
                color=[0, 255, 0],
            )
            aniseed_toolkit.run(
                "Tag Node",
                node=marker,
                tag=marker_name,
            )
            guides.append(marker)

        # -- Store the linked guide
        guide_data["LinkedGuide"] = guide_org.name()
        self.option("GuideData").set(guide_data)

        # -- Finally make the joints unselectable
        aniseed_toolkit.joints.make_referenced(self.all_joints())

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

        if not self.has_guide():
            return

        aniseed_toolkit.joints.unreference(self.all_joints())

        guide_data = self.option("GuideData").get()
        linked_guide = guide_data["LinkedGuide"]

        for marker_name, _ in guide_data["Markers"].items():
            marker = aniseed_toolkit.run(
                "Find First Child With Tag",
                node=linked_guide,
                tag=marker_name,
            )
            if not marker:
                continue

            guide_data["Markers"][marker_name] = cmds.xform(
                marker,
                query=True,
                matrix=True,
                worldSpace=True,
            )

        guide_data["LinkedGuide"] = None
        self.option("GuideData").set(guide_data)

        with aniseed_toolkit.joints.HeldTransforms(self.all_joints()):
            cmds.delete(linked_guide)

    def create_ik_pivots(self):#, foot_control, foot_bone, toe_bone):

        aniseed_toolkit.run(
            "Add Separator Attribute",
            self.ik_foot_control.ctl,
        )

        # ----------------------------------------------------------------------
        # -- Now create the start pivot
        pivot_order = [
            "ball",
            "heel",
            "tip",
            "inner",
            "outer",
        ]
        guide_data = self.option("GuideData").get()
        controls = list()

        last_parent = self.ik_foot_control.ctl

        for pivot_label in pivot_order:

            description = pivot_label.title()

            pivot_control = aniseed_toolkit.run(
                "Create Control",
                description=description,
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
            )

            cmds.xform(
                pivot_control.org,
                matrix=guide_data["Markers"][pivot_label],
                worldSpace=True,
            )

            parameter_pivot = aniseed_toolkit.run(
                "Create Basic Transform",
                classification="piv",
                description=description,
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

    def user_func_create_skeleton(self, parent=None, upper_twist_count=None, lower_twist_count=None):

        # -- Resovle the parent. The parent variable will change throughout
        # -- the course of the function but the component parent will
        # -- remain the same.
        parent = aniseed_toolkit.mutils.first_selected()
        component_parent = parent

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
        joint_data["LowerLeg"] = {"tx": 42, "jointOrientZ": -11}
        joint_data["Foot"] = {"tx": 42, "jointOrientZ": 55}
        joint_data["Toe"] = {"tx": 10, "jointOrientZ": 42}

        all_joints = aniseed_toolkit.joints.chain_from_ordered_dict(
            joint_data=joint_data,
            location=location,
            config=self.config,
            parent=parent,
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
                description=self.option("Descriptive Prefix").get() + "UpperLegTwist",
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
                description=self.option("Descriptive Prefix").get() + "LowerLegTwist",
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
        aniseed_toolkit.transformation.snap_position(guides[0], component_parent)

        # -- Add our joints to a deformers set. If we're given twists, then we
        # -- use them + the foot. Otherwise we use the arm joints themselves.
        deformers = all_joints
        if upper_twist_count:
            deformers = upper_twists + lower_twists + [all_joints[3]]
        aniseed_toolkit.sets.add_to(deformers, set_name="deformers")

    def user_func_toggle_joint_selectability(self):
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
        # -- we know its mirrored. Note that we clear the root bone as this will
        # -- trigger the duplcated component to generate the skeleton too.
        cmds.select(cmds.listRelatives(self.input("Leg Root").get(), parent=True)[0])
        mirrored_component = self.duplicate(
            input_overrides={"Leg Root": ""},
            option_overrides={"Location": location, "GuideData": self.default_guide_data()},
        )
        mirrored_component.set_label(f"{self.label()} (Mirrored)")

        # -- Get the two guides, as we need to match them
        this_guide = self.option("GuideData").get().get("LinkedGuide")
        mirrored_guide = mirrored_component.option("GuideData").get().get("LinkedGuide")

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

        # -- Get the start and end point
        root_joint = self.input("Leg Root").get()
        toe_joint = self.input("Toe").get()

        if not cmds.objExists(root_joint) or not cmds.objExists(toe_joint):
            return []

        # -- Resolve the whole chain betweenm
        leg_joints = aniseed_toolkit.joints.get_between(root_joint, toe_joint)

        # -- Include the twisters
        upper_twists = self.input("Upper Twist Joints").get()
        lower_twists = self.input("Lower Twist Joints").get()
        all_joints = leg_joints + upper_twists + lower_twists

        return [joint for joint in all_joints if joint]

    @classmethod
    def default_guide_data(cls):
        return dict(
            Markers=dict(
                ball=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                      0.0, 3.297, 1.0],
                heel=[0.0, 1.0, 0.0, 0.0, -1.0, 0.05, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                      0.0, -7, 1.0],
                tip=[0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.06, 0.0, -1.0, 0.0, 0.0,
                     0.0, 7.095, 1.0],
                inner=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, -4.0,
                       0.0, 3.3, 1.0],
                outer=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, -1.0, 0.0, 0.0, 0.0,
                       4.0, 0.0, 3.3, 1.0],
            ),
            LinkedGuide=None,
        )

    def has_guide(self):
        """
        Checks whether this has a valid guide or not
        """
        # -- Check if the guide already exists first
        guide_data = self.option("GuideData").get()
        guide = guide_data.get("LinkedGuide")
        if guide and cmds.objExists(guide):
            return True
        return False
