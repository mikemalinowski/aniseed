import os
import typing
import aniseed
import qtility
import aniseed_toolkit

import maya.cmds as mc


class SplineSpine(aniseed.RigComponent):
    identifier = "Limb : Spline Spine"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(SplineSpine, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Root Joint",
            value="",
            group="Joint Requirements",
        )

        self.declare_input(
            name="Tip Joint",
            value="",
            group="Joint Requirements",
        )

        self.declare_option(
            name="Descriptive Prefix",
            value="Spine",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            value="core_circle",
            group="Visuals",
        )

        self.declare_option(
            name="Orient Controls To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Lock End Orientations To Controls",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="FK Interaction Mode",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="GuideData",
            value=self.default_guide_data(),
            hidden=True,
        )

        self.declare_output(
            name="Root Transform",
        )

        self.declare_output(
            name="Tip Transform",
        )

        self.declare_output(
            name="Master Control",
        )

        self.declare_output(
            name="Root Control"
        )

        self.declare_output(
            name="Tip Control"
        )

        self.declare_output(
            name="Fk Tip",
        )

        self.declare_output(
            name="Fk Root",
        )

    def input_widget(self, requirement_name: str):

        object_requirements = [
            "Parent",
            "Root Joint",
            "Tip Joint",
        ]

        if requirement_name in object_requirements:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                self.option("Shape").get(),
            )

        if option_name == "Upvector Axis":
            return aniseed.widgets.AxisSelector()

    def user_functions(self) -> typing.Dict[str, callable]:

        menu = dict()

        if not self.input("Root Joint").get():
            menu["Create Joints"] = self.user_func_build_skeleton

            return menu

        guide_data = self.option("GuideData").get()
        if guide_data.get("LinkedGuide"):
            menu["Remove Guide"] = self.user_func_remove_guide
        else:
            menu["Create Guide"] = self.user_func_create_guide

        return menu

    def user_func_build_skeleton(self, joint_count=None):

        selection = mc.ls(sl=True)
        final_parent = selection[0] if selection else None
        parent = None
        joint_count = joint_count or int(
            qtility.request.text(
                title="Joint Count",
                message="How many joints do you want?"
            ),
        )
        joints = []
        if not joint_count or joint_count < 2:
            return

        guide_height = self.option("GuideData").get()["control_transforms"][-1][-3]
        increment = guide_height / (joint_count - 1)

        for idx in range(joint_count):
            joint = aniseed_toolkit.run(
                "Create Joint",
                description=self.option("Descriptive Prefix").get(),
                location=self.option("Location").get(),
                parent=parent,
                match_to=parent,
                config=self.config
            )

            if idx != 0:
                mc.setAttr(
                    f"{joint}.translateY",
                    increment
                )

            joints.append(joint)
            parent = joint

        if final_parent:
            mc.parent(
                joints[0],
                final_parent,
            )

        self.input("Root Joint").set(joints[0])
        self.input("Tip Joint").set(joints[-1])

        self.user_func_create_guide()

    def is_valid(self) -> bool:

        root_joint = self.input("Root Joint").get()
        tip_joint = self.input("Tip Joint").get()

        if not root_joint:
            print("No root joint specified")
            return False

        if not tip_joint:
            print("No tip joint specified")
            return False

        guide_data = self.option("GuideData").get()

        if guide_data.get("GuideNode") and mc.objExists(guide_data["GuideNode"]):
            print(f"You must remove the guide for {root_joint} before building")
            return False

        return True

    def run(self):

        joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
        )

        org = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="org",
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            config=self.config,
            parent=self.input("Parent").get(),
            match_to=self.input("Parent").get(),
        )

        spline_setup = self._create_spline_setup(joints, parent=org, constrain=False)
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        orient_to_world = self.option("Orient Controls To World").get()
        control_scale = 10

        master_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{descriptive}Master",
            location=location,
            parent=org,
            shape=self.option("Shape").get(),
            shape_scale=control_scale * 1.25,
            config=self.config,
            match_to=spline_setup.out_controls[0],
        )
        if orient_to_world:
            mc.xform(
                master_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Add the FK and Ik Visibility Attributes
        mc.addAttr(
            master_control.ctl,
            shortName="ik_visibility",
            at="bool",
            dv=True,
            keyable=True,
        )
        mc.addAttr(
            master_control.ctl,
            shortName="fk_visibility",
            at="bool",
            dv=False,
            keyable=True,
        )
        ik_controls = []

        base_control, base_control_tweaker = self.create_doubled_control(
            descriptive=f"{descriptive}Hip",
            location=location,
            parent=master_control.ctl,
            shape_scale=control_scale * 1.1,
            match_to=spline_setup.out_controls[0],
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[0],
        )
        ik_controls.extend([base_control, base_control_tweaker])

        lower_mid_control, lower_mid_control_tweaker = self.create_doubled_control(
            descriptive=descriptive,
            location=location,
            parent=base_control.ctl,
            shape_scale=control_scale,
            match_to=spline_setup.out_controls[1],
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[1],
        )
        ik_controls.extend([lower_mid_control, lower_mid_control_tweaker])

        chest_control, chest_control_tweaker = self.create_doubled_control(
            descriptive=descriptive,
            location=location,
            parent=master_control.ctl,
            shape_scale=control_scale,
            match_to=spline_setup.out_controls[3],
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[3],
        )
        ik_controls.extend([chest_control, chest_control_tweaker])

        upper_mid_control, upper_mid_control_tweaker = self.create_doubled_control(
            descriptive=descriptive,
            location=location,
            parent=chest_control.ctl,
            shape_scale=control_scale,
            match_to=spline_setup.out_controls[2],
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[2],
        )
        ik_controls.extend([upper_mid_control, upper_mid_control_tweaker])

        lower_upvector_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{descriptive}LowerUpvector",
            location=location,
            parent=base_control_tweaker.ctl,
            shape=self.option("Shape").get(),
            shape_scale=control_scale * 0.25,
            config=self.config,
            match_to=spline_setup.out_upvectors[0],
        )
        ik_controls.append(lower_upvector_control)
        if orient_to_world:
            mc.xform(
                lower_upvector_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )
        mc.parentConstraint(
            lower_upvector_control.ctl,
            spline_setup.out_upvectors[0],
            maintainOffset=True,
        )

        upper_upvector_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{descriptive}UpperUpvector",
            location=location,
            parent=chest_control_tweaker.ctl,
            shape=self.option("Shape").get(),
            shape_scale=control_scale * 0.25,
            config=self.config,
            match_to=spline_setup.out_upvectors[1],
        )
        ik_controls.append(upper_upvector_control)
        mc.parentConstraint(
            upper_upvector_control.ctl,
            spline_setup.out_upvectors[1],
            maintainOffset=True,
        )

        # -- Add our upvector visibility attributes
        mc.addAttr(
            base_control.ctl,
            shortName="ShowUpvector",
            dv=False,
            keyable=True,
        )
        mc.connectAttr(
            f"{base_control.ctl}.ShowUpvector",
            f"{lower_upvector_control.off}.visibility",
        )
        mc.addAttr(
            chest_control.ctl,
            shortName="ShowUpvector",
            dv=False,
            keyable=True,
        )
        mc.connectAttr(
            f"{chest_control.ctl}.ShowUpvector",
            f"{upper_upvector_control.off}.visibility",
        )

        if self.option("FK Interaction Mode").get():
            mc.parent(
                upper_mid_control.org,
                lower_mid_control.ctl,
            )
            mc.parent(
                chest_control.zero,
                upper_mid_control.ctl,
            )

        fk_controls = self.create_fk(org, spline_setup)

        # if self.option("Lock End Orientations To Controls").get():
        #     mc.parentConstraint(
        #         chest_control_tweaker.ctl,
        #         spline_setup.out_trace_joints[-1],
        #         skipTranslate=["x", "y", "z"],
        #         maintainOffset=True,
        #     )
        #     mc.parentConstraint(
        #         base_control_tweaker.ctl,
        #         spline_setup.out_trace_joints[0],
        #         skipTranslate=["x", "y", "z"],
        #         maintainOffset=True,
        #     )

        # -- Constrain the joints to the Fk controls
        for idx in range(len(fk_controls)):
            mc.parentConstraint(
                fk_controls[idx].ctl,
                joints[idx],
                maintainOffset=True,
            )
            mc.scaleConstraint(
                fk_controls[idx].ctl,
                joints[idx],
                maintainOffset=True,
            )

            # -- Hook up the visibility
            for nurbs_shape in mc.listRelatives(fk_controls[idx].ctl, children=True, type="nurbsCurve"):
                mc.connectAttr(
                    f"{master_control.ctl}.fk_visibility",
                    f"{nurbs_shape}.visibility",
                )

        for ik_control in ik_controls:
            for nurbs_shape in mc.listRelatives(ik_control.ctl, children=True, type="nurbsCurve"):
                mc.connectAttr(
                    f"{master_control.ctl}.ik_visibility",
                    f"{nurbs_shape}.visibility",
                )

        # -- Finally we set our output variables
        self.output("Root Transform").set(spline_setup.out_trace_joints[0])
        self.output("Tip Transform").set(spline_setup.out_trace_joints[-1])
        self.output("Master Control").set(master_control.ctl)
        self.output("Root Control").set(base_control_tweaker.ctl)
        self.output("Tip Control").set(chest_control_tweaker.ctl)
        self.output("Fk Root").set(fk_controls[0].ctl)
        self.output("Fk Tip").set(fk_controls[-1].ctl)

    def create_fk(self, parent, spline_setup):

        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        orient_to_world = self.option("Orient Controls To World").get()
        control_scale = 10

        next_parent = spline_setup.out_org
        fk_controls = []

        for trace_joint in spline_setup.out_anchor_points:
            fk_control = aniseed_toolkit.run(
                "Create Control",
                description=f"{descriptive}Fk",
                location=location,
                parent=next_parent,
                shape=self.option("Shape").get(),
                shape_scale=control_scale,
                config=self.config,
                match_to=trace_joint,
            )

            decompose_node = mc.createNode("decomposeMatrix")
            mc.connectAttr(f"{trace_joint}.matrix", f"{decompose_node}.inputMatrix")
            mc.connectAttr(f"{decompose_node}.outputTranslate", f"{fk_control.org}.translate")
            mc.connectAttr(f"{decompose_node}.outputRotate", f"{fk_control.org}.rotate")
            mc.connectAttr(f"{decompose_node}.outputScale", f"{fk_control.org}.scale")
            fk_controls.append(fk_control)
            next_parent = fk_control.ctl

        return fk_controls

    def create_doubled_control(self, descriptive, location, parent, shape_scale, match_to, orient_to_world, drive_this):

        main_control = aniseed_toolkit.run(
            "Create Control",
            description=descriptive,
            location=location,
            parent=parent,
            shape=self.option("Shape").get(),
            shape_scale=shape_scale,
            config=self.config,
            match_to=match_to,
        )
        if orient_to_world:
            mc.xform(
                main_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        tweak_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{descriptive}Tweak",
            location=location,
            parent=main_control.ctl,
            shape=self.option("Shape").get(),
            shape_scale=shape_scale * 0.75,
            config=self.config,
            match_to=match_to,
        )

        mc.parentConstraint(
            tweak_control.ctl,
            drive_this,
            maintainOffset=True,
        )

        return [
            main_control,
            tweak_control,
        ]

    def user_func_create_guide(self):

        joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
        )

        spline_setup = self._create_spline_setup(joints=joints)

        guide_org = mc.createNode(
            "transform",
            name="splineGuide",
        )

        mc.parent(
            spline_setup.out_org,
            guide_org,
        )

        guide_a = aniseed_toolkit.run(
            "Create Guide",
            joint=spline_setup.out_controls[0],
            parent=guide_org,
        )

        guide_b = aniseed_toolkit.run(
            "Create Guide",
            joint=spline_setup.out_controls[1],
            parent=guide_a,
            link_to=guide_a,
        )

        guide_c = aniseed_toolkit.run(
            "Create Guide",
            joint=spline_setup.out_controls[2],
            parent=guide_a,
            link_to=guide_b,
        )

        guide_d = aniseed_toolkit.run(
            "Create Guide",
            joint=spline_setup.out_controls[3],
            parent=guide_a,
            link_to=guide_c,
        )

        upvector_a = aniseed_toolkit.run(
            "Create Guide",
            joint=spline_setup.out_upvectors[0],
            parent=guide_a,
            link_to=guide_a,
        )

        upvector_b = aniseed_toolkit.run(
            "Create Guide",
            joint=spline_setup.out_upvectors[1],
            parent=guide_d,
            link_to=guide_d,
        )

        guide_data = self.option("GuideData").get()

        if not "control_transforms" in guide_data:
            guide_data = self.default_guide_data()

        guide_data["LinkedGuide"] = guide_org
        self.option("GuideData").set(guide_data)

    def user_func_remove_guide(self):

        # -- Mark this as not having an active guide
        guide_data = self.option("GuideData").get()

        # -- Validation check for legacy or broken guide data
        if not "control_transforms" in guide_data:
            guide_data = self.default_guide_data()

        # -- Store the guide data
        guide_root = guide_data["LinkedGuide"]
        for idx, suffix in enumerate(["A", "B", "C", "D"]):
            guide_data["control_transforms"][idx] = mc.xform(
                aniseed_toolkit.run(
                    "Find First Child With Tag",
                    guide_root,
                    f"CurveControl{suffix}",
                ),
                q=True,
                ws=True,
                m=True,
            )

        for idx, suffix in enumerate(["A", "B"]):
            guide_data["upvector_transforms"][idx] = mc.xform(
                aniseed_toolkit.run(
                    "Find First Child With Tag",
                    guide_root,
                    f"UpvectorControl{suffix}",
                ),
                q=True,
                ws=True,
                m=True,
            )

        # -- Delete the guide
        transforms = dict()
        joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
        )

        for joint in joints:
            transforms[joint] = mc.xform(joint, q=True, ws=True, m=True)

        mc.delete(guide_data["LinkedGuide"])

        for joint in joints:
            mc.xform(joint, ws=True, m=transforms[joint])

        # -- Update teh data
        guide_data["LinkedGuide"] = None
        self.option("GuideData").set(guide_data)


    def _create_spline_setup(self, joints, parent=None, constrain=True):

        guide_data = self.option("GuideData").get()

        # -- If the data is old or broken, fallback to the default data
        if "control_transforms" not in guide_data:
            guide_data = self.default_guide_data()

        spline_setup = aniseed_toolkit.run(
            "Create Spline Setup",
            parent=parent,
            joints=joints,
            control_transforms=guide_data["control_transforms"],
            upvector_transforms=guide_data["upvector_transforms"],
            constrain=constrain,
            lock_end_orientations=self.option("Lock End Orientations To Controls").get(),
        )

        if parent:
            try:
                mc.parent(
                    spline_setup.out_org,
                    parent,
                )
            except:
                pass
        
        # -- Now we need to name the components based on the configs
        # -- naming convention
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        mc.rename(
            spline_setup.out_org,
            self.config.generate_name(
                classification="org",
                description=f"{descriptive}SplineSolve",
                location=location,
            )
        )

        controls = spline_setup.out_controls + spline_setup.out_upvectors
        for control in controls:
            mc.rename(
                control,
                self.config.generate_name(
                    classification="loc",
                    description=f"{descriptive}PointTransform",
                    location=location,
                )
            )

        for cluster in spline_setup.out_clusters:
            mc.rename(
                cluster,
                self.config.generate_name(
                    classification="cls",
                    description=f"{descriptive}UpvectorTransform",
                    location=location,
                )
            )

        for joint in spline_setup.out_trace_joints:
            mc.rename(
                joint,
                self.config.generate_name(
                    classification="jnt",
                    description=f"{descriptive}Tracer",
                    location=location,
                )
            )

        for joint in spline_setup.out_anchor_points:
            mc.rename(
                joint,
                self.config.generate_name(
                    classification="jnt",
                    description=f"{descriptive}Anchor",
                    location=location,
                )
            )

        mc.rename(
            spline_setup.out_no_xform_org,
            self.config.generate_name(
                classification="org",
                description=f"{descriptive}NoTransform",
                location=location,
            )
        )
        return spline_setup

    @classmethod
    def default_guide_data(cls):
        return dict(
            control_transforms=[
                [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                 0.0, 0.0, 1.0],
                [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                 13.0, 0.0, 1.0],
                [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                 25.0, 0.0, 1.0],
                [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                 38.0, 0.0, 1.0],
            ],
            upvector_transforms=[
                [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 30.0,
                 0.0, 0.0, 1.0],
                [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 30.0,
                 38.0, 0.0, 1.0],
            ],
            LinkedGuide=None,
        )