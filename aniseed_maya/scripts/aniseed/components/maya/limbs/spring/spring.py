import os
import mref
import aniseed
import aniseed_toolkit
from maya import cmds


# noinspection PyUnresolvedReferences
class Spring(aniseed.RigComponent):
    """
    A control rig for a spiral (spring / helix) curve. The artist authors
    a spiraled NURBS curve and a set of guide transforms that mark where
    controls should sit. At build time:

      * One control is built per guide transform.
      * A duplicate of the guide curve becomes the deform curve and is
        skinned to a hidden joint embedded in each control, so moving
        the controls deforms the spiral.
      * Each joint in "Joints to Drive" stays exactly where the artist
        placed it; a buffer joint is created on the deform curve at the
        closest curve parameter and the user joint is parent/scale
        constrained to that buffer joint with maintainOffset. As the
        curve deforms, the buffer joints slide along it and the user
        joints follow.

    Curve normal is used as the up-vector via motionPath's worldUpType=4
    ("Normal"). For a consistent spiral this is rock solid; flat or
    low-curvature regions of the curve can produce normal flips, so this
    component is intentionally bespoke to spring-shaped curves.

    Outputs are declared dynamically: one ``Control N`` output per built
    control, populated inside ``run()``.
    """

    identifier = "Limb : Spring"
    icon = os.path.join(os.path.dirname(__file__), "icon.png")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            validate=True,
            group="Control Rig",
            description="The node under which all rig nodes (deform curve, controls, buffer joints) will be parented.",
        )

        self.declare_input(
            name="Guide Curve",
            value="",
            validate=True,
            description="The spiraled NURBS curve authored by the artist. Its shape is preserved — a duplicate is created internally and used as the deforming curve.",
        )

        self.declare_input(
            name="Control Guides",
            value=[],
            description="Transforms that mark where each control should sit. One control is built per guide.",
        )

        self.declare_input(
            name="Joints to Drive",
            value=[],
            description="The deformation joints the artist wants to follow the curve. They do NOT need to be a chain — each is bound independently to a buffer joint via parentConstraint with maintainOffset, so they stay exactly where the artist placed them at build time.",
        )

        self.declare_option(
            name="Description",
            value="spring",
            group="Naming",
            pre_expose=True,
            description="Descriptive token used when naming all generated rig nodes.",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
            description="Location token (lf/md/rt) used when naming all generated rig nodes.",
        )

        self.declare_option(
            name="Create Joints",
            value=True,
            group="Creation",
            pre_expose=True,
            description="When true, user_func_create_skeleton lays Joint Count joints along the guide curve and writes them into Joints to Drive. When false, the user is expected to supply the joints themselves.",
        )

        self.declare_option(
            name="Joint Count",
            value=5,
            group="Creation",
            pre_expose=True,
            description="Number of deformation joints to lay along the guide curve when user_func_create_skeleton runs.",
        )

        self.declare_option(
            name="Control Shape",
            value="core_cube",
            description="Shape name passed to aniseed_toolkit.control.create for every control.",
        )

        self.declare_option(
            name="Upvector Scale X",
            value=1.0,
            description="Scale factor on the X axis applied to a second copy of the curve used as the up-vector reference. Two of the three axes should be > 1.0 (the axes perpendicular to the spring's main axis) so that the up-vector curve sits radially offset from the deform curve.",
        )

        self.declare_option(
            name="Upvector Scale Y",
            value=1.5,
            description="Scale factor on the Y axis applied to a second copy of the curve used as the up-vector reference. Two of the three axes should be > 1.0 (the axes perpendicular to the spring's main axis) so that the up-vector curve sits radially offset from the deform curve.",
        )

        self.declare_option(
            name="Upvector Scale Z",
            value=1.5,
            description="Scale factor on the Z axis applied to a second copy of the curve used as the up-vector reference. Two of the three axes should be > 1.0 (the axes perpendicular to the spring's main axis) so that the up-vector curve sits radially offset from the deform curve.",
        )

    # ------------------------------------------------------------------
    # Lifecycle

    def on_enter_stack(self):
        """
        Fires once the user confirms the component's options dialog and
        the component is added to the stack. At this point the user has
        chosen whether to create the deformation joints, so we lock the
        option in (hide it) and dispatch user_func_create_skeleton if
        requested.
        """
        self.option("Create Joints").set_hidden(True)

        if not self.option("Create Joints").get():
            return

        self.user_func_create_skeleton(
            joint_count=self.option("Joint Count").get(),
        )

    # ------------------------------------------------------------------
    # Widgets

    def input_widget(self, requirement_name: str):
        if requirement_name in ("Parent", "Guide Curve"):
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name in ("Control Guides", "Joints to Drive"):
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    # ------------------------------------------------------------------
    # Skeleton creation

    def user_func_create_skeleton(self, joint_count=None):
        """
        Lays Joint Count deformation joints evenly along the guide curve
        and writes them into the "Joints to Drive" input. Called by the
        global Build Skeleton utility or invoked directly.

        If the Guide Curve input is empty (or its target no longer
        exists), the first selected object in the scene is used as a
        fallback and written back into the input. This makes it
        convenient to author the spiral, select it, and then add the
        component without having to wire the input by hand.

        The joints created here are the final deformation joints. They
        are parented as a linear chain (each joint a child of the
        previous one) for DAG tidiness — the component's run() binds
        each one independently via constraint, so the chain itself
        carries no rig wiring.
        """
        if not self.option("Create Joints").get():
            return

        guide_curve = self._resolve_guide_curve()
        if not guide_curve:
            return

        count = joint_count or self.option("Joint Count").get()

        if count < 1:
            return

        description = self.option("Description").get()
        location = self.option("Location").get()

        curve_shape = cmds.listRelatives(guide_curve, shapes=True, type="nurbsCurve")[0]
        min_u = cmds.getAttr(f"{curve_shape}.minValue")
        max_u = cmds.getAttr(f"{curve_shape}.maxValue")

        sampler = cmds.createNode("pointOnCurveInfo")
        cmds.connectAttr(f"{curve_shape}.worldSpace[0]", f"{sampler}.inputCurve")

        created_joints = []
        previous_joint = None
        try:
            for idx in range(count):
                if count == 1:
                    u = (min_u + max_u) * 0.5
                else:
                    t = idx / (count - 1)
                    u = min_u + t * (max_u - min_u)

                cmds.setAttr(f"{sampler}.parameter", u)
                position = cmds.getAttr(f"{sampler}.position")[0]

                joint = mref.create("joint", parent=previous_joint) if previous_joint else mref.create("joint")
                joint.rename(
                    self.config.generate_name(
                        classification=self.config.joint,
                        description=description,
                        location=location,
                    ),
                )
                cmds.xform(joint.name(), worldSpace=True, translation=position)
                created_joints.append(joint.name())
                previous_joint = joint
        finally:
            cmds.delete(sampler)

        self.input("Joints to Drive").set(created_joints)

    # ------------------------------------------------------------------
    # Build

    def run(self) -> bool:
        parent = self.input("Parent").get()
        guide_curve = self.input("Guide Curve").get()
        control_guides = self.input("Control Guides").get()
        joints_to_drive = self.input("Joints to Drive").get()
        description = self.option("Description").get()
        location = self.option("Location").get()
        control_shape = self.option("Control Shape").get()
        upvector_scale_x = self.option("Upvector Scale X").get()
        upvector_scale_y = self.option("Upvector Scale Y").get()
        upvector_scale_z = self.option("Upvector Scale Z").get()

        geometry_classification = self.config.geometry if hasattr(self.config, "geometry") else "geo"

        # 1. Duplicate guide curve as the deform curve. Hide it — it's rig internals.
        deform_curve = cmds.duplicate(
            guide_curve,
            name=self.config.generate_name(
                classification=geometry_classification,
                description=f"{description}_deform",
                location=location,
            ),
        )[0]
        cmds.parent(deform_curve, parent)
        cmds.setAttr(f"{deform_curve}.visibility", False)
        deform_shape = cmds.listRelatives(deform_curve, shapes=True, type="nurbsCurve")[0]

        # 1b. Duplicate the guide curve again as the up-vector curve. Scale it by
        #     the user-supplied factors and freeze so the scale is baked into the
        #     CV positions; we'll skin it to the same control-bind joints below so
        #     it deforms in lockstep with the deform curve. Each user joint will
        #     read its up direction from this parallel curve.
        upvector_curve = cmds.duplicate(
            guide_curve,
            name=self.config.generate_name(
                classification=geometry_classification,
                description=f"{description}_upvector",
                location=location,
            ),
        )[0]
        cmds.parent(upvector_curve, parent)
        cmds.setAttr(f"{upvector_curve}.scaleX", upvector_scale_x)
        cmds.setAttr(f"{upvector_curve}.scaleY", upvector_scale_y)
        cmds.setAttr(f"{upvector_curve}.scaleZ", upvector_scale_z)
        cmds.makeIdentity(upvector_curve, apply=True, scale=True)
        cmds.setAttr(f"{upvector_curve}.visibility", False)
        upvector_shape = cmds.listRelatives(upvector_curve, shapes=True, type="nurbsCurve")[0]

        # 2. Wipe any "Control N" outputs left over from a prior build, then build
        #    a control + curve-bind joint per guide and declare an output per control.
        self._clear_dynamic_control_outputs()

        curve_bind_joints = []
        previous_control = None
        for idx, guide in enumerate(control_guides):
            control_parent = previous_control.ctl if previous_control else parent

            control = aniseed_toolkit.control.create(
                description=description,
                location=location,
                parent=control_parent,
                config=self.config,
                shape=control_shape,
                match_to=guide,
            )

            curve_bind_joint = mref.create("joint", parent=control.ctl)
            curve_bind_joint.rename(
                self.config.generate_name(
                    classification=self.config.joint,
                    description=f"{description}_bind",
                    location=location,
                ),
            )
            curve_bind_joints.append(curve_bind_joint.name())

            output_name = f"Control {idx}"
            self.declare_output(name=output_name)
            self.output(output_name).set(control.ctl)

            previous_control = control

        # 3. Skin both the deform curve and the up-vector curve to the same
        #    curve-bind joints so they deform together as the controls move.
        if curve_bind_joints:
            cmds.skinCluster(
                curve_bind_joints,
                deform_curve,
                toSelectedBones=True,
            )
            cmds.skinCluster(
                curve_bind_joints,
                upvector_curve,
                toSelectedBones=True,
            )

        # 4. For each user joint: find the closest u on the deform curve, create a
        #    buffer joint driven by a motionPath there, then offset-constrain the
        #    user joint to it so the user joint never moves on creation.
        for jnt_idx, joint_name in enumerate(joints_to_drive):
            if not cmds.objExists(joint_name):
                continue

            u_value = self._closest_u_on_curve(joint_name, deform_shape)

            buffer_joint = mref.create("joint", parent=parent)
            buffer_joint.rename(
                self.config.generate_name(
                    classification=self.config.joint,
                    description=f"{description}_buffer",
                    location=location,
                ),
            )
            cmds.setAttr(f"{buffer_joint.name()}.visibility", False)

            motion_path = cmds.createNode(
                "motionPath",
                name=self.config.generate_name(
                    classification="mpath",
                    description=f"{description}_buffer",
                    location=location,
                ),
            )
            cmds.connectAttr(f"{deform_shape}.worldSpace[0]", f"{motion_path}.geometryPath")
            cmds.setAttr(f"{motion_path}.uValue", u_value)
            cmds.setAttr(f"{motion_path}.fractionMode", False)
            cmds.setAttr(f"{motion_path}.follow", True)
            cmds.setAttr(f"{motion_path}.frontAxis", 0)    # X follows curve tangent (node-level attr is "frontAxis"; the pathAnimation command exposes it as "followAxis")
            cmds.setAttr(f"{motion_path}.upAxis", 1)       # Y is up
            cmds.setAttr(f"{motion_path}.worldUpType", 1)  # 1 = "Object Up" — up direction points toward the worldUpMatrix's translation

            # Up-vector target — a transform stuck on the parallel scaled curve
            # at the same u parameter as the buffer. Its world position feeds
            # the buffer's motionPath worldUpMatrix so the up axis tracks the
            # parallel curve as the deform curve animates.
            upvector_target = mref.create("transform", parent=parent)
            upvector_target.rename(
                self.config.generate_name(
                    classification="upvector",
                    description=f"{description}_upvector",
                    location=location,
                ),
            )
            cmds.setAttr(f"{upvector_target.name()}.visibility", False)

            upvector_motion_path = cmds.createNode(
                "motionPath",
                name=self.config.generate_name(
                    classification="mpath",
                    description=f"{description}_upvector",
                    location=location,
                ),
            )
            cmds.connectAttr(f"{upvector_shape}.worldSpace[0]", f"{upvector_motion_path}.geometryPath")
            cmds.setAttr(f"{upvector_motion_path}.uValue", u_value)
            cmds.setAttr(f"{upvector_motion_path}.fractionMode", False)
            cmds.setAttr(f"{upvector_motion_path}.follow", False)
            cmds.connectAttr(f"{upvector_motion_path}.allCoordinates", f"{upvector_target.name()}.translate")

            cmds.connectAttr(f"{upvector_target.name()}.worldMatrix[0]", f"{motion_path}.worldUpMatrix")

            cmds.connectAttr(f"{motion_path}.allCoordinates", f"{buffer_joint.name()}.translate")
            cmds.connectAttr(f"{motion_path}.rotate", f"{buffer_joint.name()}.rotate")
            cmds.connectAttr(f"{motion_path}.rotateOrder", f"{buffer_joint.name()}.rotateOrder")

            # The user joint stays where it is and follows the buffer joint
            # via maintainOffset. No snapping.
            cmds.parentConstraint(buffer_joint.name(), joint_name, maintainOffset=True)
            cmds.scaleConstraint(buffer_joint.name(), joint_name, maintainOffset=True)

        return True

    # ------------------------------------------------------------------
    # Helpers

    def _clear_dynamic_control_outputs(self):
        for output in list(self.outputs()):
            if output.name().startswith("Control "):
                self.remove_output(output.name())

    def _resolve_guide_curve(self):
        """
        Returns the Guide Curve input if it points at an existing curve
        in the scene. Otherwise falls back to the first selected NURBS
        curve and writes that selection back into the input, so the
        component is fully configured after this call. Returns None and
        prints an explanation if no valid curve can be resolved.
        """
        guide_curve = self.input("Guide Curve").get()
        if guide_curve and cmds.objExists(guide_curve):
            return guide_curve

        selection = cmds.ls(selection=True, long=False) or []
        if not selection:
            print("Spring: cannot create joints — Guide Curve input is missing and nothing is selected.")
            return None

        candidate = selection[0]
        if not cmds.listRelatives(candidate, shapes=True, type="nurbsCurve"):
            print(f"Spring: cannot create joints — selected object '{candidate}' is not a NURBS curve transform.")
            return None

        self.input("Guide Curve").set(candidate)
        return candidate

    @staticmethod
    def _closest_u_on_curve(joint_name: str, curve_shape: str) -> float:
        joint_world_pos = cmds.xform(joint_name, query=True, worldSpace=True, translation=True)

        npoc = cmds.createNode("nearestPointOnCurve")
        try:
            cmds.connectAttr(f"{curve_shape}.worldSpace[0]", f"{npoc}.inputCurve")
            cmds.setAttr(f"{npoc}.inPosition", *joint_world_pos)
            return cmds.getAttr(f"{npoc}.parameter")
        finally:
            cmds.delete(npoc)
