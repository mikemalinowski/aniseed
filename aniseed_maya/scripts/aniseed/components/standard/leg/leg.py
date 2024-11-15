import os
import qute
import bony
import functools
import shapeshift
import collections

import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
def _default_marker_data():
    return {
      "Marker : Tip Roll": {
        "node": None,
        "matrix": [
          1.6875389974302405e-14,
          -1.0000000000000016,
          0,
          0,
          -0.9999999999999998,
          -5.799797358230175e-7,
          3.2310891488651727e-15,
          0,
          -0.000007699790929509355,
          -0.000004050106194082862,
          -0.9999999999999989,
          0,
          15.923704629321065,
          1.038765080664596e-13,
          10.358663285232932,
          1
        ]
      },
      "Marker : Heel Roll": {
        "node": None,
        "matrix": [
          1.68753899743024e-14,
          -1.0000000000000013,
          0,
          0,
          0.9999999999999996,
          5.799797358230174e-7,
          0,
          0,
          0.000007699790926278266,
          0.000004050106194082862,
          0.9999999999999989,
          0,
          15.923704629320945,
          -1.87822923678576e-14,
          -7.640707908493841,
          1
        ]
      },
      "Marker : Inner Roll": {
        "node": None,
        "matrix": [
          1.6653345369377354e-14,
          -1.0000000000000004,
          0,
          0,
          -2.3529510997915047e-12,
          -0.000004050106193962671,
          -0.9999999999999984,
          0,
          0.9999999999999994,
          5.799797356181654e-7,
          0.00000769978857315843,
          0,
          12.034377989639726,
          3.171960616813738e-16,
          3.649898632868812,
          1
        ]
      },
      "Marker : Outer Roll": {
        "node": None,
        "matrix": [
          0.000007699790939825735,
          -0.9999999998563203,
          0.0000071416516156724706,
          0,
          3.636271272678563e-15,
          0.000011191757810861018,
          0.9999999999703542,
          0,
          -1.0000000000296425,
          -0.000008279825648476315,
          -0.000007699700606637458,
          0,
          19.81905872289967,
          1.7160536247871776e-13,
          3.6498986328687675,
          1
        ]
      },
      "Marker : Ball Twist": {
        "node": None,
        "matrix": [
          0.9999999999999994,
          0,
          0,
          0,
          5.799797189426905e-7,
          1.0000000000000013,
          0,
          0,
          0.000007699793275257417,
          0.000004050101728348392,
          0.9999999999999989,
          0,
          15.92370462932104,
          7.549515128565887e-14,
          4.057209118708634,
          1
        ]
      },
      "Marker : Foot Control": {
        "node": None,
        "matrix": [
          0.9999999999999994,
          0,
          0,
          0,
          5.799797189426905e-7,
          1.0000000000000013,
          0,
          0,
          0.000007699793275257417,
          0.000004050101728348392,
          0.9999999999999989,
          0,
          15.92370462932104,
          7.549515128565887e-14,
          4.057209118708634,
          1
        ]
      }
    }

# --------------------------------------------------------------------------------------
class LegComponent(aniseed.RigComponent):
    """
    This is some documentation that the user will see. You should adjust the guides...
    """
    identifier = "Standard : Leg"

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

    # ----------------------------------------------------------------------------------
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
            value=_default_marker_data(),
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
        self.declare_output("Ik Foot")
        self.declare_output("Upvector")

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name):

        if requirement_name in ["Parent", "Leg Root", "Toe"]:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "Upper Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

        if requirement_name == "Lower Twist Joints":
            return aniseed.widgets.everywhere.ObjectList()

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(self.config)

    # ----------------------------------------------------------------------------------
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

    # ----------------------------------------------------------------------------------
    def is_valid(self) -> bool:

        if self._get_guide():
            print("You must remove the guide before building")
            return False

        leg_root = self.input("Leg Root").get()
        toe_tip = self.input("Toe").get()

        all_joints = bony.hierarchy.get_between(
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

        facing_dir = bony.direction.get_chain_facing_direction(
            leg_root,
            all_joints[2],
        )

        directions = bony.direction.Facing

        if facing_dir != directions.NegativeX and facing_dir != directions.PositiveX:
            print("The leg must be aligned to the X axis")
            return False

        return True

    # ----------------------------------------------------------------------------------
    # noinspection DuplicatedCode
    def run(self):

        leg_root = self.input("Leg Root").get()
        toe_tip = self.input("Toe").get()
        parent = self.input("Parent").get()
        directions = bony.direction.Facing

        all_joints = bony.hierarchy.get_between(
            leg_root,
            toe_tip,
        )

        # -- We now make an assumption about the number of bones in our chain
        knee_joint = all_joints[1]
        foot_joint = all_joints[2]
        toe_joint = all_joints[3]

        # -- Determine the options we're building with
        prefix = self.option('Description Prefix').get()
        location = self.option("Location").get()

        org = aniseed.control.basic_transform(
            classification=self.config.organisational,
            description=prefix + "Leg",
            location=location,
            config=self.config,
            parent=parent
        )

        # -- This is the default rotation of our shapes based on X down the chain
        fk_shape_rotation = [0, 0, 0]

        shape_y_flip = False

        facing_dir = bony.direction.get_chain_facing_direction(
            leg_root,
            foot_joint,
        )

        if facing_dir == directions.NegativeX:
            shape_y_flip = True
            fk_shape_rotation = [180, 0, 0]

        # -- Add the configuration control
        config_control = aniseed.control.create(
            description=f"{prefix}LegConfig",
            location=location,
            parent=org,
            shape="core_lollipop",
            config=self.config,
            match_to=leg_root,
            shape_scale=20.0,
            rotate_shape=fk_shape_rotation,
        )

        # ----------------------------------------------------------------------
        # -- NK SETUP

        # -- Now create an NK joint hierarchy, which we will use to bind
        # -- between the IK and the FK
        nk_joints = list()
        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=leg_root,
            to_this=toe_joint,
            parent=parent,
        )

        # -- Rename the nk joints
        for nk_joint in replicated_joints:
            nk_joint = mc.rename(
                nk_joint,
                self.config.generate_name(
                    classification="mech",
                    description=f"{prefix}LegNK",
                    location=location,
                )
            )
            nk_joints.append(nk_joint)

        self.output("Blended Upper Leg").set(nk_joints[0])
        self.output("Blended Lower Leg").set(nk_joints[1])
        self.output("Blended Foot").set(nk_joints[2])
        self.output("Blended Toe").set(nk_joints[3])

        # ----------------------------------------------------------------------
        # -- IK SETUP

        # -- Now create the Ik joints
        ik_controls = list()
        ik_joints = list()

        replicated_joints = bony.hierarchy.replicate_chain(
            from_this=leg_root,
            to_this=foot_joint,
            parent=parent,
        )

        # -- Rename the ik joints
        for ik_joint in replicated_joints:

            ik_joint = mc.rename(
                ik_joint,
                self.config.generate_name(
                    classification="mech",
                    description=f"{prefix}LegIK",
                    location=location,
                )
            )
            ik_joints.append(ik_joint)

            # -- Ensure all the rotation values are on the joint
            # -- orients to allow for correct assignment of the
            # -- ik vector
            bony.orients.move_rotations_to_joint_orients(ik_joint)

        # -- Create the Ik setup
        handle, effector = mc.ikHandle(
            startJoint=ik_joints[0],
            endEffector=ik_joints[-1],
            solver='ikRPsolver',
            priority=1,
        )

        # -- Hide the ik handle as we dont want the animator
        # -- to interact with it directly
        mc.setAttr(
            f"{handle}.visibility",
            0,
        )

        # -- Create the upvector control for the arm
        upvector = aniseed.control.create(
            description=f"{prefix}LegUpvector",
            location=location,
            parent=parent,
            shape="core_sphere",
            config=self.config,
            match_to=ik_joints[1],
            shape_scale=5.0,
            rotate_shape=None,
        )
        ik_controls.append(upvector)
        self.output("Upvector").set(upvector)

        upvector_org = aniseed.control.get_classification(
            upvector,
            "org",
        )

        mc.xform(
            upvector_org,
            translation=aniseed.utils.math.calculate_upvector_position(
                length=1,
                *ik_joints
            ),
            worldSpace=True,
        )

        if self.option("Align Upvector To World").get():
            mc.xform(
                upvector_org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Apply the upvector constraint
        mc.poleVectorConstraint(
            upvector,
            handle,
            weight=1,
        )

        # -- Now create the main IK control
        ik_foot_ctl = aniseed.control.create(
            description=f"{prefix}Foot",
            location=location,
            parent=parent,
            shape="core_paddle",
            config=self.config,
            shape_scale=40.0,
            rotate_shape=[0, 90, 0] if shape_y_flip else [0, -90, 0],
        )

        mc.xform(
            aniseed.control.get_classification(
                ik_foot_ctl,
                "org",
            ),
            matrix=self._get_marker_matrix("Marker : Foot Control"),
            worldSpace=True,
        )

        ik_controls.append(ik_foot_ctl)
        self.output("Ik Foot").set(ik_foot_ctl)

        if self.option("Align Foot To World").get():
            foot_org = aniseed.control.get_classification(
                ik_foot_ctl,
                "org",
            )

            mc.xform(
                foot_org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        pivot_tip, pivot_controls = self._setup_ik_pivot_behaviour(
            foot_control=ik_foot_ctl,
            foot_bone=foot_joint,
            toe_bone=toe_joint,
        )
        ik_controls.extend(pivot_controls)

        # -- Add the heel control
        heel_control = aniseed.control.create(
            description=f"{prefix}Heel",
            location=location,
            parent=pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=toe_joint,
            shape_scale=10,
            rotate_shape=[90, 0, 0],
        )
        ik_controls.append(heel_control)

        heel_org = aniseed.control.get_classification(
            heel_control,
            "org",
        )

        mc.xform(
            heel_org,
            rotation=mc.xform(
                ik_foot_ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        # -- Parent the ikhandle under the heel control so it
        # -- moves along with it
        mc.parent(
            handle,
            heel_control,
        )

        # -- Add the toe control
        toe_control = aniseed.control.create(
            description=f"{prefix}Toe",
            location=location,
            parent=pivot_tip,
            shape="core_paddle",
            config=self.config,
            match_to=toe_joint,
            shape_scale=10,
            rotate_shape=[180, 0, 0],
        )
        ik_controls.append(toe_control)

        toe_org = aniseed.control.get_classification(
            toe_control,
            "org",
        )

        mc.xform(
            toe_org,
            rotation=mc.xform(
                ik_foot_ctl,
                query=True,
                rotation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        if self.option("Apply Soft Ik").get():

            root_marker = mc.createNode("transform")

            mc.parent(
                root_marker,
                parent,
            )

            mc.xform(
                root_marker,
                matrix=mc.xform(
                    ik_joints[0],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            tip_marker = mc.createNode("transform")

            mc.parent(
                tip_marker,
                pivot_tip,
            )

            mc.xform(
                tip_marker,
                matrix=mc.xform(
                    ik_joints[-1],
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )
            aniseed.utils.mech.soft_ik.create(
                root_marker,
                tip_marker,
                ik_joints[-2],
                ik_joints[-1],
                host=ik_foot_ctl,
            )


        # -- We need to constrain the end joint in rotation to the
        # -- hand control, because the ik does not do that.
        mc.parentConstraint(
            pivot_tip,
            ik_joints[-1],
            skipTranslate=['x', 'y', 'z'],
        )

        ik_bindings = [
            ik_joints[0],
            ik_joints[1],
            heel_control,
            toe_control,
        ]

        # ----------------------------------------------------------------------
        # -- FK SETUP
        fk_controls = []

        fk_parent = self.input("Parent").get()

        for idx, joint in enumerate(all_joints):

            fk_control = aniseed.control.create(
                description=f"{prefix}{self._LABELS[idx]}FK",
                location=location,
                parent=fk_parent,
                shape="core_paddle",
                config=self.config,
                match_to=joint,
                shape_scale=20.0,
                rotate_shape=fk_shape_rotation,
            )
            fk_controls.append(fk_control)
            fk_parent = fk_control

        # ----------------------------------------------------------------------
        # -- Bink the IK, FK and NK
        proxies = collections.OrderedDict()
        proxies['ik_fk'] = 0
        proxies['show_ik'] = 1
        proxies['show_fk'] = 0

        for label in proxies:
            mc.addAttr(
                config_control,
                shortName=label,
                at='float',
                min=0,
                max=1,
                dv=proxies[label],
                k=True,
            )

        for ik_control in ik_controls:

            ik_off = aniseed.control.get_classification(
                ik_control,
                "off",
            )

            mc.connectAttr(
                f"{config_control}.show_ik",
                f"{ik_off}.visibility",
            )

        for fk_control in fk_controls:

            fk_off = aniseed.control.get_classification(
                fk_control,
                "off",
            )

            mc.connectAttr(
                f"{config_control}.show_fk",
                f"{fk_off}.visibility",
            )

        # -- We need to constrain our nk between the ik and the fk
        for ik_node, fk_node, nk_node, skl_node in zip(ik_bindings, fk_controls, nk_joints, all_joints):

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
                f"{config_control}.ik_fk",
                f"{reverse_node}.inputX",
            )

            mc.connectAttr(
                f"{reverse_node}.outputX",
                f"{cns}.{ik_driven}",
            )

            mc.connectAttr(
                f"{config_control}.ik_fk",
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

        upper_twist_joints = self.input("Upper Twist Joints").get()
        lower_twist_joints = self.input("Lower Twist Joints").get()

        if upper_twist_joints:
            twist_component = self.rig.component_library.get("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(upper_twist_joints)
            twist_component.input("Parent").set(parent)
            twist_component.input("Root").set(nk_joints[0])
            twist_component.input("Tip").set(nk_joints[1])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("UpperTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                shapeshift.rotate_shape(twist, *fk_shape_rotation)

        if lower_twist_joints:

            twist_component = self.rig.component_library.get("Augment : Twister")(
                "",
                stack=self.rig,
            )

            twist_component.input("Joints").set(lower_twist_joints)
            twist_component.input("Parent").set(nk_joints[1])
            twist_component.input("Root").set(nk_joints[1])
            twist_component.input("Tip").set(nk_joints[2])

            twist_component.option("Constrain Root").set(False)
            twist_component.option("Constrain Tip").set(True)
            twist_component.option("Descriptive Prefix").set("LowerTwist")
            twist_component.option("Location").set(self.option("Location").get())

            twist_component.run()

            for twist in twist_component.builder.all_controls():
                shapeshift.rotate_shape(twist, *fk_shape_rotation)

    # ----------------------------------------------------------------------------------
    def user_func_build_guide(self) -> str:

        # -- Get the joint hierarchy
        leg_root = self.input("Leg Root").get()
        toe = self.input("Toe").get()

        all_joints = bony.hierarchy.get_between(
            leg_root,
            toe,
        )

        guide_data = dict()

        # -- Read the current joint axis orientation so we can always
        # -- default to it
        guide_data["facing_direction"] = bony.direction.direction_as_string(
            bony.direction.get_chain_facing_direction(
                all_joints[0],
                all_joints[2],
            ),
        )

        guide_data["upvector_direction"] = bony.direction.direction_as_string(
            bony.direction.get_upvector_direction(
                all_joints[0],
                all_joints[2],
            ),
        )

        guide_data["guide_org"] = aniseed.control.basic_transform(
            classification="gde",
            description=f"LegManipulationGuide",
            location=self.option("Location").get(),
            config=self.config,
            parent=None,
        )

        last_guide = None
        guide_data["guides"] = dict()

        for idx, joint in enumerate(all_joints):

            guide_control = aniseed.utils.guide.create(
                joint,
                parent=guide_data["guide_org"],
                link_to=last_guide,
            )
            guide_data["guides"][joint] = guide_control

            last_guide = guide_control

        default_marker_data = _default_marker_data()
        stored_marker_data = self.option("GuideMarkers").get()
        data_to_store = dict()

        for marker_label in default_marker_data:

            marker_data = stored_marker_data.get(
                marker_label,
                default_marker_data[marker_label]
            )

            if "node" not in marker_data:
                marker_data = default_marker_data[marker_label]

            marker = aniseed.control.basic_transform(
                classification="gde",
                description=marker_label.split(":")[-1].replace(" ", ""),
                location=self.option("Location").get(),
                config=self.config,
                parent=guide_data["guide_org"],
                match_to=marker_data["matrix"],
            )
            marker_data["node"] = marker

            shapeshift.apply(
                node=marker,
                data="core_symbol_rotator",
                color=[0, 255, 0],
            )

            data_to_store[marker_label] = marker_data

        self.option("Guides").set(guide_data)
        self.option("GuideMarkers").set(data_to_store)

        bony.visibility.hide(all_joints)

    # ----------------------------------------------------------------------------------
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

        all_chain = bony.hierarchy.get_between(
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

        for label in _default_marker_data():
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
        bony.ik.align_bones_for_ik(
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

        bony.visibility.show(all_chain)

    # ----------------------------------------------------------------------------------
    def _setup_ik_pivot_behaviour(self, foot_control, foot_bone, toe_bone):

        aniseed.utils.attribute.add_separator_attr(foot_control)

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

        last_parent = foot_control

        for pivot_label in pivot_order:

            marker_transform = self._get_marker_matrix(pivot_label)
            description = pivot_label.split(":")[-1].replace(" ", "")

            pivot_control = aniseed.control.create(
                description=description,
                location=self.option("Location").get(),
                parent=last_parent,
                shape="core_sphere",  # "core_symbol_rotator",
                shape_scale=4,
                config=self.config,
            )

            mc.xform(
                aniseed.control.get_classification(
                    pivot_control,
                    "org",
                ),
                matrix=marker_transform,
                worldSpace=True,
            )

            parameter_pivot = aniseed.control.basic_transform(
                classification="piv",
                description=description,
                location=self.option("Location").get(),
                config=self.config,
                parent=pivot_control,
                match_to=pivot_control,
            )

            # -- Add the parameter to the foot control
            mc.addAttr(
                foot_control,
                shortName=description,
                at="float",
                dv=0,
                k=True,
            )

            mc.connectAttr(
                f"{foot_control}.{description}",
                f"{parameter_pivot}.rotateY",
            )

            controls.append(pivot_control)
            last_parent = parameter_pivot

        return last_parent, controls

    # ----------------------------------------------------------------------------------
    def _get_marker_matrix(self, marker_name):
        marker_data = self.option("GuideMarkers").get()
        return marker_data[marker_name]["matrix"]

    # ----------------------------------------------------------------------------------
    def _get_guide(self):

        connections = mc.listConnections(
            f"{self.input('Leg Root').get()}.message",
            destination=True,
            plugs=True,
        )

        for connection in connections or list():
            if "guideRig" in connection:
                return connection.split(".")[0]

    # ----------------------------------------------------------------------------------
    def user_func_create_skeleton(self, parent=None, upper_twist_count=None, lower_twist_count=None):

        if not parent:
            try:
                parent = mc.ls(sl=True)[0]

            except:
                parent = None

        if upper_twist_count is None:
            upper_twist_count = qute.utilities.request.text(
                title="Upper Twist Count",
                label="How many twist joints do you want on the upper leg?"
            )
            upper_twist_count = int(upper_twist_count)

        if lower_twist_count is None:
            lower_twist_count = qute.utilities.request.text(
                title="Upper Twist Count",
                label="How many twist joints do you want on the lower leg?"
            )
            lower_twist_count = int(lower_twist_count)

        joint_map = bony.writer.load_joints_from_file(
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "leg_joints.json",
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
                twist_joint = aniseed.joint.create(
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
                twist_joint = aniseed.joint.create(
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
            bony.flip.global_mirror(
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

            bony.flip.global_mirror(
                transforms=markers,
                across="YZ",
            )