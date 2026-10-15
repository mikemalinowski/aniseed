"""
Provides the "Limb : Spring" component, a control rig for an artist authored
spiral (spring / helix) NURBS curve. One control is built per control guide,
deforming a duplicate of the guide curve, and the joints to drive follow buffer
joints which slide along that curve (with up-vectors from a second, scaled
curve). Joints can optionally be laid along the curve on entering the stack.
"""
import os
import mref
import aniseed
import aniseed_toolkit


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

    The up-vector of each buffer joint comes from a second, scaled copy of
    the guide curve (skinned in the same way). A transform rides that
    curve at the same parameter as the buffer and is used as the
    motionPath's "Object Up" target, so the up direction tracks the
    spiral as it deforms.

    Outputs are declared dynamically: one ``Control N`` output per built
    control, populated inside ``run()``.
    """

    identifier = "Limb : Spring"
    icon = os.path.join(os.path.dirname(__file__), "icon.png")

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, guide curve, control guide and joints to drive
        inputs, plus the naming, joint creation, control shape and up-vector
        curve scale options. Outputs are declared dynamically in run().
        """
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
        """
        Returns the object selector or object list widgets for our inputs
        """
        if requirement_name in ("Parent", "Guide Curve"):
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name in ("Control Guides", "Joints to Drive"):
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name: str):
        """
        Returns the location selector for the location option
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    # ------------------------------------------------------------------
    # Skeleton creation

    def user_func_create_skeleton(self, joint_count=None):
        """
        Lays Joint Count deformation joints evenly along the guide curve
        and writes them into the "Joints to Drive" input. Called by the
        global Build Skeleton utility or invoked directly (which is why the
        Create Joints option is checked here too).

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

        curve_shape = self._curve_shape_name(guide_curve)
        min_u = mref.getAttr(f"{curve_shape}.minValue")
        max_u = mref.getAttr(f"{curve_shape}.maxValue")

        sampler = mref.create("pointOnCurveInfo")
        mref.connectAttr(f"{curve_shape}.worldSpace[0]", sampler.attr("inputCurve"))

        created_joints = []
        previous_joint = None
        try:
            for idx in range(count):
                if count == 1:
                    u = (min_u + max_u) * 0.5
                else:
                    t = idx / (count - 1)
                    u = min_u + t * (max_u - min_u)

                sampler.attr("parameter").set(u)
                position = sampler.attr("position").get()[0]

                joint = mref.create("joint", parent=previous_joint) if previous_joint else mref.create("joint")
                joint.rename(
                    self.config.generate_name(
                        classification=self.config.joint,
                        description=description,
                        location=location,
                    ),
                )
                joint.set_position(position, space="world")
                created_joints.append(joint.name())
                previous_joint = joint
        finally:
            sampler.delete()

        self.input("Joints to Drive").set(created_joints)

    # ------------------------------------------------------------------
    # Build

    def run(self) -> bool:
        """
        Builds the controls, the deforming curves and the buffer joints
        which the user joints follow.
        """
        parent = self.input("Parent").get()
        guide_curve = mref.get(self.input("Guide Curve").get())
        control_guides = self.input("Control Guides").get()
        joints_to_drive = self.input("Joints to Drive").get()
        description = self.option("Description").get()
        location = self.option("Location").get()
        control_shape = self.option("Control Shape").get()

        geometry_classification = self.config.geometry if hasattr(self.config, "geometry") else "geo"

        # 1. Duplicate guide curve as the deform curve. Hide it — it's rig internals.
        deform_curve = guide_curve.duplicate(
            name=self.config.generate_name(
                classification=geometry_classification,
                description=f"{description}_deform",
                location=location,
            ),
        )
        deform_curve.set_parent(parent)
        deform_curve.hide()

        # -- Note: The duplicated curve shapes keep the same short name as the
        # -- guide curve shape. As the curve shapes are addressed by their short
        # -- names below, maya resolves them to the guide curve shape - so the
        # -- motion paths (and the closest u lookup) read the static guide curve
        # -- rather than the deforming curves. This is existing behaviour which
        # -- rigs depend on, so it is deliberately preserved.
        deform_shape = self._curve_shape_name(deform_curve)

        # 1b. Duplicate the guide curve again as the up-vector curve. Scale it by
        #     the user-supplied factors and freeze so the scale is baked into the
        #     CV positions; we'll skin it to the same control-bind joints below so
        #     it deforms in lockstep with the deform curve. Each user joint will
        #     read its up direction from this parallel curve.
        upvector_curve = guide_curve.duplicate(
            name=self.config.generate_name(
                classification=geometry_classification,
                description=f"{description}_upvector",
                location=location,
            ),
        )
        upvector_curve.set_parent(parent)
        upvector_curve.scaleX.set(self.option("Upvector Scale X").get())
        upvector_curve.scaleY.set(self.option("Upvector Scale Y").get())
        upvector_curve.scaleZ.set(self.option("Upvector Scale Z").get())
        upvector_curve.freeze_transforms(translate=False, rotate=False, scale=True)
        upvector_curve.hide()
        upvector_shape = self._curve_shape_name(upvector_curve)

        # 2. Wipe any "Control N" outputs left over from a prior build, then build
        #    a control + curve-bind joint per guide and declare an output per control.
        aniseed_toolkit.component_outputs.clear_outputs(self, "Control ")

        curve_bind_joints = []
        control_parent = parent
        for idx, guide in enumerate(control_guides):

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

            control_parent = control.ctl

        # 3. Skin both the deform curve and the up-vector curve to the same
        #    curve-bind joints so they deform together as the controls move.
        if curve_bind_joints:
            for curve in [deform_curve, upvector_curve]:
                mref.skinCluster(
                    curve_bind_joints,
                    curve,
                    toSelectedBones=True,
                )

        # 4. For each user joint: find the closest u on the deform curve, create a
        #    buffer joint driven by a motionPath there, then offset-constrain the
        #    user joint to it so the user joint never moves on creation.
        for joint_name in joints_to_drive:
            if not mref.objExists(joint_name):
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
            buffer_joint.hide()

            motion_path = self._create_motion_path(
                curve_shape=deform_shape,
                u_value=u_value,
                follow=True,
                description=f"{description}_buffer",
            )
            motion_path.attr("frontAxis").set(0)    # X follows curve tangent (node-level attr is "frontAxis"; the pathAnimation command exposes it as "followAxis")
            motion_path.attr("upAxis").set(1)       # Y is up
            motion_path.attr("worldUpType").set(1)  # 1 = "Object Up" — up direction points toward the worldUpMatrix's translation

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
            upvector_target.hide()

            upvector_motion_path = self._create_motion_path(
                curve_shape=upvector_shape,
                u_value=u_value,
                follow=False,
                description=f"{description}_upvector",
            )
            upvector_motion_path.attr("allCoordinates").connect(upvector_target.attr("translate"))

            upvector_target.attr("worldMatrix[0]").connect(motion_path.attr("worldUpMatrix"))

            motion_path.attr("allCoordinates").connect(buffer_joint.attr("translate"))
            motion_path.attr("rotate").connect(buffer_joint.attr("rotate"))
            motion_path.attr("rotateOrder").connect(buffer_joint.attr("rotateOrder"))

            # The user joint stays where it is and follows the buffer joint
            # via maintainOffset. No snapping.
            aniseed_toolkit.constraints.parent_and_scale(buffer_joint, joint_name)

        return True

    # ------------------------------------------------------------------
    # Helpers

    def _create_motion_path(self, curve_shape, u_value, follow, description):
        """
        Creates a motionPath node (in parametric mode) reading from the
        given curve shape at the given u value.
        """
        motion_path = mref.create(
            "motionPath",
            name=self.config.generate_name(
                classification="mpath",
                description=description,
                location=self.option("Location").get(),
            ),
        )
        mref.connectAttr(f"{curve_shape}.worldSpace[0]", motion_path.attr("geometryPath"))
        motion_path.attr("uValue").set(u_value)
        motion_path.attr("fractionMode").set(False)
        motion_path.attr("follow").set(follow)
        return motion_path

    def _resolve_guide_curve(self):
        """
        Returns the Guide Curve input if it points at an existing curve
        in the scene. Otherwise falls back to the first selected NURBS
        curve and writes that selection back into the input, so the
        component is fully configured after this call. Returns None and
        prints an explanation if no valid curve can be resolved.
        """
        guide_curve = self.input("Guide Curve").get()
        if guide_curve and mref.objExists(guide_curve):
            return guide_curve

        selection = mref.ls(selection=True).names()
        if not selection:
            print("Spring: cannot create joints — Guide Curve input is missing and nothing is selected.")
            return None

        candidate = selection[0]
        if not mref.listRelatives(candidate, shapes=True, type="nurbsCurve"):
            print(f"Spring: cannot create joints — selected object '{candidate}' is not a NURBS curve transform.")
            return None

        self.input("Guide Curve").set(candidate)
        return candidate

    @staticmethod
    def _curve_shape_name(curve) -> str:
        """
        Returns the short name of the first nurbs curve shape of the given
        curve transform. Note that the short name may be ambiguous (see run).
        """
        return mref.get(curve).children(node_type="nurbsCurve")[0].name()

    @staticmethod
    def _closest_u_on_curve(joint_name: str, curve_shape: str) -> float:
        """
        Returns the curve parameter closest to the world position of the
        given joint. This deliberately uses a nearestPointOnCurve node so
        that the parameter is exactly the one maya resolves.
        """
        npoc = mref.create("nearestPointOnCurve")
        try:
            mref.connectAttr(f"{curve_shape}.worldSpace[0]", npoc.attr("inputCurve"))
            npoc.attr("inPosition").set(*mref.get(joint_name).get_position(space="world"))
            return npoc.attr("parameter").get()
        finally:
            npoc.delete()
