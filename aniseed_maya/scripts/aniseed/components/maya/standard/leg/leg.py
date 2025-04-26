import json
import os
import aniseed
import qtility
import functools
import collections
import aniseed_toolkit
import maya.cmds as mc


class LegComponent(aniseed.RigComponent):
    """
    This is some documentation that the user will see. You should adjust the guides...
    """
    identifier = "Standard : Leg"

    icon = os.path.join(
        os.path.dirname(__file__),
        "leg.png",
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
            name="GuideMarkers",
            value=self._default_marker_data(),
            hidden=True,
        )

        self.declare_option(
            name="Guides",
            value=dict(),
            hidden=True,
        )

        self.declare_option(
            name="Description Prefix",
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
        self.chain_direction: "Direction" = None
        self.org: str = ""
        self.config_control: "Control" = None
        self.upvector_control: "Control" = None
        self.ik_foot_control: "Control" = None
        self.ik_heel_control: "Control" = None
        self.ik_foot_control: "Control" = None
        self.ik_toe_control: "Control" = None
        self.ik_pivot_endpoint: str = ""
        self.pivot_controls: list["Control"] = []

        self.controls: list[str] = []
        self.fk_controls: list["Control"] = []
        self.ik_controls: list["Control"] = []
        self.ik_bindings: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [0, 0, 0]
        self.shape_flip = False


    def input_widget(self, requirement_name):

        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    def user_functions(self):

        menu = super(LegComponent, self).user_functions()

        # -- Only show the skeleton creation tools if we dont have a skeleton
        leg_joint = self.input("Leg Root").get()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        if not leg_joint or not mc.objExists(leg_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)
            return menu

        guide_data = self.option("Guides").get()

        if guide_data.get("guide_org") and mc.objExists(guide_data["guide_org"]):
            # -- Depending on whether we have a guide or not, change what we show
            # -- in the actions menu
            # if self._get_guide():
            menu["Remove Guide"] = functools.partial(self.user_func_remove_guide)

        else:
            menu["Create Guide"] = functools.partial(self.user_func_build_guide)

        return menu

    def is_valid(self) -> bool:

        if self._get_guide():
            print("You must remove the guide before building")
            return False

        leg_root = self.input("Leg Root").get()
        toe_tip = self.input("Toe").get()

        all_joints = aniseed_toolkit.run(
            "Get Joints Between",
            leg_root,
            toe_tip,
        )

        if len(all_joints) < 4:
            print(
                (
                    f"Expected at least 4 joints "
                    "(upper leg, lower leg, foot, toe). "
                    f"But got {len(all_joints)} joints"
                )
            )
            return False

        facing_dir = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            leg_root,
            all_joints[2],
        )

        if facing_dir != facing_dir.NegativeX and facing_dir != facing_dir.PositiveX:
            print("The leg must be aligned to the X axis")
            return False

        return True

    def create_controls(self):

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

        mc.xform(
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
            mc.xform(
                self.upvector_control.org,
                rotation=[0, 0, 0],
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

        mc.xform(
            self.ik_foot_control.org,
            matrix=self._get_marker_matrix("Marker : Foot Control"),
            worldSpace=True,
        )

        if self.option("Align Foot To World").get():
            mc.xform(
                self.ik_foot_control.org,
                rotation=[0, 0, 0],
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
            match_to=self.leg_joints[-2],
            shape_scale=10,
            rotate_shape=[90, 0, 0],
        )
        self.ik_controls.append(self.ik_heel_control.ctl)

        mc.xform(
            self.ik_heel_control.org,
            rotation=mc.xform(
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
            match_to=self.leg_joints[-2],
            shape_scale=10,
            rotate_shape=[180, 0, 0],
        )
        self.ik_controls.append(self.ik_toe_control.ctl)

        mc.xform(
            self.ik_toe_control.org,
            rotation=mc.xform(
                self.ik_foot_control.ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        fk_parent = self.org

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

        replicated_joints = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.leg_joints[0],
            to_this=self.leg_joints[2],
            parent=self.org,
        )

        # -- Rename the ik joints
        for joint in replicated_joints:
            joint = mc.rename(
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
        handle, effector = mc.ikHandle(
            startJoint=self.ik_joints[0],
            endEffector=self.ik_joints[-1],
            solver='ikRPsolver',
            priority=1,
        )

        # -- Hide the ik handle as we dont want the animator
        # -- to interact with it directly
        mc.setAttr(
            f"{handle}.visibility",
            0,
        )

        # -- Apply the upvector constraint
        mc.poleVectorConstraint(
            self.upvector_control.ctl,
            handle,
            weight=1,
        )

        # -- Parent the ikhandle under the heel control so it
        # -- moves along with it
        mc.parent(
            handle,
            self.ik_heel_control.ctl,
        )

        if self.option("Apply Soft Ik").get():

            root_marker = mc.createNode("transform")

            mc.parent(
                root_marker,
                self.org,
            )

            mc.xform(
                root_marker,
                matrix=mc.xform(
                    self.ik_joints[0],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            tip_marker = mc.createNode("transform")

            mc.parent(
                tip_marker,
                self.ik_pivot_endpoint,
            )

            mc.xform(
                tip_marker,
                matrix=mc.xform(
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
        mc.parentConstraint(
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

        # -- Now create an NK joint hierarchy, which we will use to bind
        # -- between the IK and the FK
        replicated_joints = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.leg_joints[0],  # Upper leg
            to_this=self.leg_joints[3],  # Toe
            parent=self.org,
        )

        # -- Rename the nk joints
        for nk_joint in replicated_joints:
            nk_joint = mc.rename(
                nk_joint,
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}LegNK",
                    location=self.location,
                )
            )
            self.nk_joints.append(nk_joint)

        proxies = collections.OrderedDict()
        proxies['ik_fk'] = 0
        proxies['show_ik'] = 1
        proxies['show_fk'] = 0

        for label in proxies:
            mc.addAttr(
                self.config_control.ctl,
                shortName=label,
                at='float',
                min=0,
                max=1,
                dv=proxies[label],
                k=True,
            )

        for ik_control in self.ik_controls:
            ik_control = aniseed_toolkit.run(
                "Get Control",
                ik_control,
            )
            mc.connectAttr(
                f"{self.config_control.ctl}.show_ik",
                f"{ik_control.off}.visibility",
            )

        for fk_control in self.fk_controls:
            fk_control = aniseed_toolkit.run(
                "Get Control",
                fk_control,
            )
            mc.connectAttr(
                f"{self.config_control.ctl}.show_fk",
                f"{fk_control.off}.visibility",
            )

        # -- We need to constrain our nk between the ik and the fk
        for ik_node, fk_node, nk_node, skl_node in zip(self.ik_bindings, self.fk_controls, self.nk_joints, self.leg_joints):

            # -- Create the constraint between the nk and the ik
            mc.parentConstraint(
                ik_node,
                nk_node,
                maintainOffset=True,
            )

            cns = mc.parentConstraint(
                fk_node,
                nk_node,
                maintainOffset=True,
            )[0]

            # -- Hook up the blends to drive the weights
            ik_driven = mc.parentConstraint(cns, query=True, weightAliasList=True)[0]
            fk_driven = mc.parentConstraint(cns, query=True, weightAliasList=True)[1]

            # -- Setting the IK FK blend constraint to shortest
            mc.setAttr(
                f"{cns}.interpType",
                2,  # -- Shortest
            )

            reverse_node = mc.createNode("reverse")

            mc.connectAttr(
                f"{self.config_control.ctl}.ik_fk",
                f"{reverse_node}.inputX",
            )

            mc.connectAttr(
                f"{reverse_node}.outputX",
                f"{cns}.{ik_driven}",
            )

            mc.connectAttr(
                f"{self.config_control.ctl}.ik_fk",
                f"{cns}.{fk_driven}",
            )

            mc.parentConstraint(
                nk_node,
                skl_node,
                maintainOffset=True,
            )

            mc.scaleConstraint(
                nk_node,
                skl_node,
                maintainOffset=True,
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

    # noinspection DuplicatedCode
    def run(self):

        # -- Determine the options we're building with
        self.prefix = self.option('Description Prefix').get()
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

        self.chain_direction = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            start=self.leg_joints[0],
            end=self.leg_joints[-1],
        )

        if self.chain_direction == self.chain_direction.NegativeX:
            self.shape_flip = True
            self.shape_rotation = [180, 0, 0]

        self.create_controls()
        self.create_ik()
        self.create_nk()
        self.create_twists()
        self.set_outputs()

    def user_func_build_guide(self) -> str:

        # -- Get the joint hierarchy
        leg_root = self.input("Leg Root").get()
        toe = self.input("Toe").get()

        all_joints = aniseed_toolkit.run(
            "Get Joints Between",
            leg_root,
            toe,
        )

        guide_data = dict()

        # -- Read the current joint axis orientation so we can always
        # -- default to it
        guide_data["facing_direction"] = aniseed_toolkit.run("Get Chain Facing Direction",
            all_joints[0],
            all_joints[2],
        ).full_string

        guide_data["upvector_direction"] = aniseed_toolkit.run(
        "Get Upvector Direction",
            all_joints[0],
            all_joints[2],
        )

        guide_data["guide_org"] = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="gde",
            description=f"LegManipulationGuide",
            location=self.option("Location").get(),
            config=self.config,
            parent=None,
        )

        last_guide = None
        guide_data["guides"] = dict()

        for idx, joint in enumerate(all_joints):

            guide_control = aniseed_toolkit.run(
                "Create Guide",
                joint,
                parent=guide_data["guide_org"],
                link_to=last_guide,
            )
            guide_data["guides"][joint] = guide_control

            last_guide = guide_control

        default_marker_data = self._default_marker_data()
        stored_marker_data = self.option("GuideMarkers").get()
        data_to_store = dict()

        for marker_label in default_marker_data:

            marker_data = stored_marker_data.get(
                marker_label,
                default_marker_data[marker_label]
            )

            if "node" not in marker_data:
                marker_data = default_marker_data[marker_label]

            marker = aniseed_toolkit.run(
                "Create Basic Transform",
                classification="gde",
                description=marker_label.split(":")[-1].replace(" ", ""),
                location=self.option("Location").get(),
                config=self.config,
                parent=guide_data["guide_org"],
                match_to=marker_data["matrix"],
            )
            marker_data["node"] = marker

            aniseed_toolkit.run(
                "Apply Shape",
                node=marker,
                data="core_symbol_rotator",
                color=[0, 255, 0],
            )

            data_to_store[marker_label] = marker_data

        self.option("Guides").set(guide_data)
        self.option("GuideMarkers").set(data_to_store)

        aniseed_toolkit.run(
            "Hide Nodes",
            all_joints,
        )

    def user_func_remove_guide(self):
        guide_data = self.option("Guides").get()

        if not guide_data:
            print("no guide data")
            return

        try:
            guide_root = guide_data["guide_org"]

        except KeyError:
            self.option("Guides").set(dict())
            return

        all_chain = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Leg Root").get(),
            self.input("Toe").get(),
        )

        transforms = dict()

        for joint, guide in zip(all_chain, guide_data["guides"]):

            transforms[joint] = mc.xform(
                guide,
                query=True,
                matrix=True,
                worldSpace=True,
            )

        # -- Store the marker data before it gets removed
        new_data = dict()

        for label in self._default_marker_data():
            existing_data = self.option("GuideMarkers").get()[label]

            new_data[label] = dict(
                node=None,
                matrix=mc.xform(
                    existing_data["node"],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
            )

        self.option("GuideMarkers").set(new_data)

        mc.delete(guide_data["guide_org"])
        self.option("Guides").set(dict())

        for joint, transform in transforms.items():
            mc.xform(
                joint,
                matrix=transform,
                worldSpace=True,
            )

        mc.select(
            [
                all_chain[0],
                all_chain[-1],
            ]
        )

        # -- Align the foot
        aniseed_toolkit.run(
            "Align Bones For Ik",
            all_chain[0],
            all_chain[2],
            guide_data.get("facing_direction", "positive x"),
            guide_data.get("upvector_direction", "positive y"),
        )

        mc.xform(
            all_chain[-2],
            matrix=transforms[all_chain[-2]],
            worldSpace=True,
        )

        mc.xform(
            all_chain[-1],
            matrix=transforms[all_chain[-1]],
            worldSpace=True,
        )

        aniseed_toolkit.run(
            "Hide Nodes",
            all_chain,
        )

    def create_ik_pivots(self):#, foot_control, foot_bone, toe_bone):

        aniseed_toolkit.run(
            "Add Separator Attribute",
            self.ik_foot_control.ctl,
        )

        # ----------------------------------------------------------------------
        # -- Now create the start pivot
        pivot_order = [
            'Marker : Ball Twist',
            'Marker : Heel Roll',
            'Marker : Tip Roll',
            'Marker : Inner Roll',
            'Marker : Outer Roll',
        ]

        controls = list()

        last_parent = self.ik_foot_control.ctl

        for pivot_label in pivot_order:

            marker_transform = self._get_marker_matrix(pivot_label)
            description = pivot_label.split(":")[-1].replace(" ", "")

            pivot_control = aniseed_toolkit.run(
                "Create Control",
                description=description,
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
            )

            mc.xform(
                pivot_control.org,
                matrix=marker_transform,
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
            mc.addAttr(
                self.ik_foot_control.ctl,
                shortName=description,
                at="float",
                dv=0,
                k=True,
            )

            mc.connectAttr(
                f"{self.ik_foot_control.ctl}.{description}",
                f"{parameter_pivot}.rotateY",
            )

            controls.append(pivot_control.ctl)
            last_parent = parameter_pivot

        return last_parent, controls

    def _get_marker_matrix(self, marker_name):
        marker_data = self.option("GuideMarkers").get()
        return marker_data[marker_name]["matrix"]

    def _get_guide(self):

        connections = mc.listConnections(
            f"{self.input('Leg Root').get()}.message",
            destination=True,
            plugs=True,
        )

        for connection in connections or list():
            if "guideRig" in connection:
                return connection.split(".")[0]

    def user_func_create_skeleton(self, parent=None, upper_twist_count=None, lower_twist_count=None):

        if not parent:
            try:
                parent = mc.ls(sl=True)[0]

            except:
                parent = None

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

        joint_map = aniseed_toolkit.run(
            "Load Joints File",
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "leg.json",
            ),
            apply_names=False,
        )

        location = self.option("Location").get()

        upper_leg = mc.rename(
            joint_map["upperleg"],
            self.config.generate_name(
                classification=self.config.joint,
                description="UpperLeg",
                location=location
            ),
        )

        lower_leg = mc.rename(
            joint_map["lowerleg"],
            self.config.generate_name(
                classification=self.config.joint,
                description="LowerLeg",
                location=location
            ),
        )

        foot = mc.rename(
            joint_map["foot"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Foot",
                location=location
            ),
        )

        toe = mc.rename(
            joint_map["toe"],
            self.config.generate_name(
                classification=self.config.joint,
                description="Toe",
                location=location
            ),
        )

        all_joints = [upper_leg, lower_leg, foot, toe]

        self.input("Leg Root").set(upper_leg)
        self.input("Toe").set(toe)

        if upper_twist_count:
            parent = upper_leg

            upper_increment = mc.getAttr(
                f"{lower_leg}.translateX",
            ) / (upper_twist_count - 1)

            upper_twist_joints = list()

            for idx in range(upper_twist_count):
                twist_joint = aniseed_toolkit.run(
                    "Create Joint",
                    description=self.option("Description Prefix").get() + "UpperLegTwist",
                    location=self.option("Location").get(),
                    parent=parent,
                    match_to=parent,
                    config=self.config
                )
                upper_twist_joints.append(twist_joint)

                mc.setAttr(
                    f"{twist_joint}.translateX",
                    upper_increment * idx
                )
                all_joints.append(twist_joint)
            self.input("Upper Twist Joints").set(upper_twist_joints)

        if lower_twist_count:
            parent = lower_leg

            lower_increment = mc.getAttr(
                f"{foot}.translateX",
            ) / (lower_twist_count - 1)

            lower_twist_joints = list()

            for idx in range(lower_twist_count):
                twist_joint = aniseed_toolkit.run(
                    "Create Joint",
                    description=self.option("Description Prefix").get() + "LowerLegTwist",
                    location=self.option("Location").get(),
                    parent=parent,
                    match_to=parent,
                    config=self.config
                )
                lower_twist_joints.append(twist_joint)

                mc.setAttr(
                    f"{twist_joint}.translateX",
                    lower_increment * idx
                )
                all_joints.append(twist_joint)

            self.input("Lower Twist Joints").set(lower_twist_joints)

        if self.option("Location").get() == self.config.right:
            aniseed_toolkit.run(
                "Global Mirror",
                transforms=all_joints,
                across="YZ"
            )

        # -- Immediately enter guide mode
        self.user_func_build_guide()

        # -- Mirror the guide markers
        if self.option("Location").get() == self.config.right:
            guide_data = self.option("GuideMarkers").get()
            markers = list()

            for _, data in guide_data.items():
                markers.append(data["node"])

            aniseed_toolkit.run(
                "Global Mirror",
                transforms=markers,
                across="YZ",
            )

    @classmethod
    def _default_marker_data(cls):
        pivot_data = os.path.join(
            os.path.dirname(__file__),
            "default_pivot_data.json",
        )
        with open(pivot_data) as f:
            return json.load(f)
