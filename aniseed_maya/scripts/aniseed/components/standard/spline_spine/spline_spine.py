import os
import qute
import bony
import typing
import aniseed
import shapeshift

import maya.cmds as mc
import maya.api.OpenMaya as om


# --------------------------------------------------------------------------------------
class SplineSpine(aniseed.RigComponent):

    identifier = "Standard : Spline Spine"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(SplineSpine, self).__init__(*args, **kwargs)


        self.declare_requirement(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_requirement(
            name="Root Joint",
            value="",
            group="Joint Requirements",
        )

        self.declare_requirement(
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
            name="Tip Should Be Child Of Root",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Lock End Orientations To Controls",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Upvector Axis",
            value="Y",
            group="Behaviour",
        )

        self.declare_option(
            name="Upvector Distance Multiplier",
            value=1.0,
            group="Behaviour",
        )

        self.declare_option(
            name="GuideData",
            value=dict(),
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

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name: str):

        object_requirements = [
            "Parent",
            "Root Joint",
            "Tip Joint",
        ]

        if requirement_name in object_requirements:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                self.option("Shape").get(),
            )

        if option_name == "Upvector Axis":
            return aniseed.widgets.everywhere.AxisSelector()

    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:

        menu = dict()

        if not self.requirement("Root Joint").get():
            menu["Create Joints"] = self.user_func_build_skeleton

            return menu

        if self.option("GuideData").get().get("GuideNode"):
            menu["Remove Guide"] = self.user_func_remove_guide

        else:
            menu["Create Guide"] = self.user_func_create_guide

        return menu

    # ----------------------------------------------------------------------------------
    def is_valid(self) -> bool:

        root_joint = self.requirement("Root Joint").get()
        tip_joint = self.requirement("Tip Joint").get()

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

    # ----------------------------------------------------------------------------------
    def run(self):
        self._create_spline_setup(
            guide_mode=False,
        )

    # ----------------------------------------------------------------------------------
    # noinspection DuplicatedCode
    def _create_spline_setup(self, guide_mode=False):

        if guide_mode:
            parent = mc.rename(
                mc.createNode("transform"),
                "SplineGuideManipulator",
            )

            guide_data = self.option("GuideData").get()
            guide_data["GuideNode"] = parent
            self.option("GuideData").set(guide_data)

        else:
            parent = self.requirement("Parent").get()

        root_joint = self.requirement("Root Joint").get()
        tip_joint = self.requirement("Tip Joint").get()

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        if guide_mode:
            shape = "core_cube"

        else:
            shape = self.option("Shape").get()

        joints_to_drive = bony.hierarchy.get_between(
            root_joint,
            tip_joint,
        )

        chain_direction = bony.direction.get_chain_facing_direction(
            root_joint,
            tip_joint,
        )

        shape_rotation = shapeshift.rotations.rotation_from_up_axis(
            bony.direction.get_axis_from_direction(
                chain_direction,
            ),
        )

        if self.option("Orient Controls To World").get():
            shape_rotation = shapeshift.rotations.rotation_from_up_axis(
                bony.direction.Facing.PositiveY,
            )

        # -- Lets start by creating curve
        curve = self._create_spine_curve(
            joints_to_drive,
            parent=parent
        )
        try:
            mc.parent(
                curve,
                parent,
            )

        except RuntimeError:
            pass

        xfo = mc.xform(
            curve,
            query=True,
            matrix=True,
            worldSpace=True,
        )

        mc.setAttr(
            f"{curve}.inheritsTransform",
            False,
        )

        mc.xform(
            curve,
            matrix=xfo,
            worldSpace=True,
        )

        chain_length = bony.hierarchy.chain_length(
            root_joint,
            tip_joint,
        )

        if guide_mode:
            shape_scale = chain_length * 0.25

        else:
            shape_scale = chain_length

        # -- Create the clusters
        cluster_transforms = self._create_curve_clusters(curve)

        # -- Now create the controls
        master_control = aniseed.control.create(
            description=f"{prefix}Master",
            location=location,
            shape=shape,
            shape_scale=shape_scale * 1.1,
            rotate_shape=shape_rotation,
            match_to=root_joint,
            parent=parent,
            config=self.config,
            classification_override="gde" if guide_mode else None,
        )
        self._align_control_to_world(master_control, guide_mode)

        root_control = aniseed.control.create(
            description=f"{prefix}Root",
            location=location,
            shape=shape,
            shape_scale=shape_scale,
            rotate_shape=shape_rotation,
            match_to=root_joint,
            parent=master_control,
            config=self.config,
            classification_override="gde" if guide_mode else None,
        )
        self._align_control_to_world(root_control, guide_mode)

        secondary_root_control = aniseed.control.create(
            description=f"{prefix}SecondaryRoot",
            location=location,
            shape=shape,
            shape_scale=shape_scale,
            rotate_shape=shape_rotation,
            match_to=root_joint,
            parent=master_control if guide_mode else root_control,
            config=self.config,
            classification_override="gde" if guide_mode else None,
        )
        self._align_control_to_world(secondary_root_control, guide_mode)

        self._add_secondary_vis_attribute(
            root_control,
            secondary_root_control,
            guide_mode,
        )

        mc.xform(
            aniseed.control.get_classification(
                secondary_root_control,
                "org",
            ),
            translation=mc.xform(
                f"{curve}.cv[1]",  # cluster_transforms[1],
                query=True,
                translation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        tip_parent = master_control

        if self.option("Tip Should Be Child Of Root").get():
            tip_parent = root_control

        tip_control = aniseed.control.create(
            description=f"{prefix}Tip",
            location=location,
            shape=shape,
            shape_scale=shape_scale,
            rotate_shape=shape_rotation,
            match_to=tip_joint,
            parent=master_control if guide_mode else tip_parent,
            config=self.config,
            classification_override="gde" if guide_mode else None,
        )
        self._align_control_to_world(tip_control, guide_mode)

        secondary_tip_control = aniseed.control.create(
            description=f"{prefix}SecondaryTip",
            location=location,
            shape=shape,
            shape_scale=shape_scale,
            rotate_shape=shape_rotation,
            match_to=tip_control,
            parent=master_control if guide_mode else tip_control,
            config=self.config,
            classification_override="gde" if guide_mode else None,
        )
        self._align_control_to_world(secondary_tip_control, guide_mode)

        self._add_secondary_vis_attribute(
            tip_control,
            secondary_tip_control,
            guide_mode,
        )

        mc.xform(
            aniseed.control.get_classification(
                secondary_tip_control,
                "org",
            ),
            translation=mc.xform(
                f"{curve}.cv[2]",  # cluster_transforms[2],
                query=True,
                translation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        if guide_mode:

            all_controls = [
                master_control,
                root_control,
                secondary_root_control,
                secondary_tip_control,
                tip_control,
            ]

            for control in all_controls:
                shapeshift.apply_colour(
                    control,
                    r=0,
                    g=1,
                    b=0,
                )
                shapeshift.scale(
                    control,
                    scale_by=0.2,
                )

        cluster_parents = [
            root_control,
            secondary_root_control,
            secondary_tip_control,
            tip_control,
        ]

        for idx in range(len(cluster_parents)):
            mc.parent(
                cluster_transforms[idx],
                cluster_parents[idx],
            )

            mc.setAttr(
                f"{cluster_transforms[idx]}.visibility",
                False,
            )

        # -- Create the upvectors
        root_upvector = aniseed.control.create(
            description=f"{prefix}RootUpvector",
            location=location,
            shape="core_sphere",
            match_to=root_joint,
            parent=root_control,
            config=self.config,
            classification_override="gde" if guide_mode else None,
        )
        self._align_control_to_world(root_upvector, guide_mode)

        tip_upvector = aniseed.control.create(
            description=f"{prefix}TipUpvector",
            location=location,
            shape="core_sphere",
            match_to=tip_joint,
            parent=tip_control,
            config=self.config,
            classification_override="gde" if guide_mode else None,
        )
        self._align_control_to_world(tip_upvector, guide_mode)

        mc.setAttr(
            aniseed.control.get_classification(
                root_upvector,
                "zro",
            ) + ".translate" + self.option("Upvector Axis").get(),
            chain_length * self.option("Upvector Distance Multiplier").get(),
        )
        #
        mc.setAttr(
            aniseed.control.get_classification(
                tip_upvector,
                "zro",
            ) + ".translate" + self.option("Upvector Axis").get(),
            chain_length * self.option("Upvector Distance Multiplier").get(),
        )

        # -- Now replicate the chain so we can apply the ik
        replicated_chain = bony.hierarchy.replicate_chain(
            from_this=root_joint,
            to_this=tip_joint,
            parent=parent,
            world=True,
            replacements={"JNT_": "MEC_"}
        )
        bony.visibility.hide(replicated_chain)

        # -- Create the ik handle
        ikh, effector = mc.ikHandle(
            startJoint=replicated_chain[0],
            endEffector=replicated_chain[-1],
            curve=curve,
            solver="ikSplineSolver",
            createCurve=False,
            parentCurve=False,
            priority=1,
        )

        mc.parent(
            ikh,
            parent,
        )

        mc.setAttr(
            f"{ikh}.visibility",
            False,
        )

        mc.setAttr(
            f"{ikh}.dTwistControlEnable",
            True,
        )

        mc.setAttr(
            f"{ikh}.dWorldUpType",
            2,  # -- Object Up (Start/End)
        )

        mc.setAttr(
            f"{ikh}.dForwardAxis",
            bony.direction.get_ik_solver_attribute_index(direction=chain_direction)
        )

        # -- Get the index of the world up list.
        if self.option("Upvector Axis").get() == "X":
            up_axis = 6  # -- Positive X

        elif self.option("Upvector Axis").get() == "Y":
            up_axis = 0  # -- Positive Y

        else:
            up_axis = 3  # -- Positive Z

        mc.setAttr(
            f"{ikh}.dWorldUpAxis",
            up_axis
        )

        mc.connectAttr(
            f"{root_upvector}.worldMatrix[0]",
            f"{ikh}.dWorldUpMatrix",
        )

        mc.connectAttr(
            f"{tip_upvector}.worldMatrix[0]",
            f"{ikh}.dWorldUpMatrixEnd",
        )

        # -- Now make the spine stretchable
        curve_info = mc.createNode("curveInfo")

        mc.connectAttr(
            f"{curve}.local",
            f"{curve_info}.inputCurve",
        )

        math_node = mc.createNode("floatMath")

        mc.setAttr(
            f"{math_node}.operation",
            3,  # -- Divide
        )

        mc.connectAttr(
            f"{curve_info}.arcLength",
            f"{math_node}.floatA",
        )

        direction = bony.direction.get_chain_facing_direction(
            replicated_chain[1],
            replicated_chain[-2],
            epsilon=mc.getAttr(f"{curve_info}.arcLength") / 100
        )
        print(mc.getAttr(f"{curve_info}.arcLength") / 100)
        mc.setAttr(
            f"{math_node}.floatB",
            len(replicated_chain) - 1,
        )

        forward_axis = bony.direction.get_axis_from_direction(direction)
        multiplier = bony.direction.get_multiplier_from_direction(direction)

        for joint in replicated_chain:
            mul_node = mc.createNode("floatMath")

            mc.connectAttr(
                f"{math_node}.outFloat",
                mul_node + ".floatA",
            )

            mc.setAttr(
                f"{mul_node}.floatB",
                multiplier,
            )

            mc.setAttr(
                f"{mul_node}.operation",
                2,  # -- Divide
            )

            mc.connectAttr(
                f"{mul_node}.outFloat",
                f"{joint}.translate{forward_axis}",
            )

        drivers = [
            b
            for b in replicated_chain
        ]

        if self.option("Lock End Orientations To Controls").get(): #  and not guide_mode:
            drivers[0] = root_control
            drivers[-1] = tip_control

        for idx in range(len(drivers)):
            mc.parentConstraint(
                drivers[idx],
                joints_to_drive[idx],
                maintainOffset=True,
            )

        # -- Set our outputs if we're not in guide mode
        if not guide_mode:
            self.output("Root Transform").set(
                drivers[0],
            )

            self.output("Tip Transform").set(
                drivers[-1],
            )

            self.output("Master Control").set(
                master_control,
            )

            self.output("Root Control").set(
                root_control,
            )

            self.output("Tip Control").set(
                tip_control,
            )

    # ----------------------------------------------------------------------------------
    def _align_control_to_world(self, control, guide_mode=False):

        # -- If we're in guide mode, we want to keep our controls
        # -- orientated to the bones
        if guide_mode:
            return

        # -- If the user has not asked for world oriented controls, 
        # -- we dont do it
        if not self.option("Orient Controls To World").get():
            return 
    
        org = aniseed.control.get_classification(
            control,
            "zro",
        )

        mc.xform(
            org,
            rotation=[0, 0, 0],
            worldSpace=True,
        )

    # ----------------------------------------------------------------------------------
    def _create_curve_clusters(self, curve):
        curve_shape = mc.listRelatives(
            curve,
            shapes=True,
        )[0]

        clusters = []

        for idx in range(4):
            mc.select(f"{curve_shape}.cv[{idx}]")
            cluster_transform = mc.rename(
                mc.cluster()[1],
                self.config.generate_name(
                    classification="cls",
                    description=self.option("Descriptive Prefix").get(),
                    location=self.option("Location").get(),
                ),
            )

            clusters.append(cluster_transform)

        return clusters

    # ----------------------------------------------------------------------------------
    def _create_spine_curve(self, nodes, parent=None):

        guide_data = self.option("GuideData").get()

        position_data = guide_data.get(
            "GuidePoints",
            None,
        )

        if position_data:
            degree = 3

            quad_curve = mc.curve(
                p=position_data["positions"],
                degree=degree,
                knot=position_data["knots"],
            )
            
        else:
            degree = 1

            points = [
                mc.xform(
                    node, 
                    query=True, 
                    translation=True, 
                    worldSpace=True,
                )
                for node in nodes
            ]

            knots = [
                i
                for i in range(len(points) + degree - 1)
            ]

            mc.curve(
                p=points,
                degree=degree,
                knot=knots
            )

            quad_curve = mc.rebuildCurve(
                replaceOriginal=True,
                rebuildType=0,  # Uniform
                endKnots=1,
                keepRange=False,
                keepEndPoints=True,
                keepTangents=False,
                spans=1,
                degree=3,
                tolerance=0.01,
            )

            if parent:
                mc.parent(
                    quad_curve,
                    parent,
                )

        quad_curve = mc.rename(
            quad_curve,
            self.config.generate_name(
                classification="crv",
                description=self.option("Descriptive Prefix").get(),
                location=self.option("Location").get(),
            ),
        )
        mc.setAttr(
            f"{quad_curve}.visibility",
            False,
        )

        # -- Store the guide curve
        guide_data["GuideCurve"] = quad_curve
        self.option("GuideData").set(guide_data)

        return quad_curve

    # ----------------------------------------------------------------------------------
    def _add_secondary_vis_attribute(self, primary, secondary, guide_mode):

        if guide_mode:
            return

        aniseed.utils.attribute.add_separator_attr(primary)

        mc.addAttr(
            primary,
            shortName="SecondaryControlVisibility",
            at="bool",
            dv=False,
            k=True,
        )

        org = aniseed.control.get_classification(
            secondary,
            "org",
        )

        mc.connectAttr(
            f"{primary}.SecondaryControlVisibility",
            f"{org}.visibility",
        )


    # ----------------------------------------------------------------------------------
    def _store_guide_curve_positions(self):

        guide_data = self.option("GuideData").get()

        guide_curve = guide_data.get("GuideCurve", None)

        if not guide_curve:
            print("Could not find the guide curve")
            return

        pointer = aniseed.utils.mutils.get_object(
            mc.listRelatives(
                guide_curve,
                shapes=True,
            )[0],
        )

        nurbs_fn = om.MFnNurbsCurve(pointer)

        data = dict(
            positions=[
                list(p)[:3]
                for p in nurbs_fn.cvPositions(om.MSpace.kObject)
            ],
            knots=[n for n in nurbs_fn.knots()],
        )

        guide_data["GuidePoints"] = data
        self.option("GuideData").set(guide_data)

    # ----------------------------------------------------------------------------------
    def user_func_build_skeleton(self, joint_count=None):

        if not joint_count:
            joint_count = qute.utilities.request.text(
                title="Joint Count",
                label="How many joints do you want?"
            )

            if not joint_count:
                return

            joint_count = int(joint_count)

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        if joint_count < 2:
            return

        increment = 25 / (joint_count - 1)

        root_joint = aniseed.joint.create(
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=parent,
            match_to=parent,
            config=self.config
        )
        self.requirement("Root Joint").set(root_joint)

        mc.xform(
            root_joint,
            rotation=[-90, 0, 90],
            translation=[0, 105, 0],
            worldSpace=True,
        )

        joint = None
        parent = root_joint

        for idx in range(joint_count-1):
            joint = aniseed.joint.create(
                description=self.option("Descriptive Prefix").get(),
                location=self.option("Location").get(),
                parent=parent,
                match_to=parent,
                config=self.config
            )

            mc.setAttr(
                f"{joint}.translateX",
                increment
            )

            parent = joint

        self.requirement("Tip Joint").set(joint)
        mc.select(joint)

        # -- When we build the skeleton, automatically create the guide
        self.user_func_create_guide()

    # ----------------------------------------------------------------------------------
    def user_func_create_guide(self):
        self._create_spline_setup(
            guide_mode=True,
        )

    # ----------------------------------------------------------------------------------
    def user_func_remove_guide(self):

        # -- Store the guide curve positions into the component so we can rebuild
        # -- the exact same curve
        self._store_guide_curve_positions()

        transforms = dict()

        all_chain = bony.hierarchy.get_between(
            self.requirement("Root Joint").get(),
            self.requirement('Tip Joint').get(),
        )

        for joint in all_chain:
            transforms[joint] = mc.xform(
                joint,
                query=True,
                matrix=True,
            )

        guide_data = self.option("GuideData").get()

        if guide_data.get("GuideNode") and mc.objExists(guide_data["GuideNode"]):
            mc.delete(
                guide_data["GuideNode"],
            )

        guide_data["GuideNode"] = None
        self.option("GuideData").set(guide_data)

        for joint, matrix in transforms.items():
            mc.xform(
                joint,
                matrix=matrix,
            )
