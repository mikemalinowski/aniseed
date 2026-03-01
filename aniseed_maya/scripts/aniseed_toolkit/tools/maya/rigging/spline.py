"""
This creates a generalised Spline Setup
"""
import mref
import maya.cmds as mc
import aniseed_toolkit


class SplineSetup(aniseed_toolkit.Tool):

    identifier = "Create Spline Setup"
    classification = "Rigging"
    categories = [
        "Rigging",
    ]

    def run(
        self,
        parent,
        joints,
        org_transform,
        control_transforms,
        constrain=True,
        lock_end_orientations=True,
    ):
        spline_solve = SimpleSplineSetup(
            parent,
            joints,
            org_transform,
            control_transforms,
            constrain=constrain,
            lock_end_orientations_to_control=lock_end_orientations,
        )
        spline_solve.create()
        return spline_solve


class SimpleSplineSetup:

    # -- This is the index that starts at letter 'a'
    ord_a = 97

    def __init__(
            self,
            parent,
            joints,
            org_transform,
            control_transforms,
            constrain=True,
            hide_mechanicals=True,
            lock_end_orientations_to_control=True,
    ):
        # -- These are our input variables
        self.org_transform = org_transform
        self.in_parent = parent
        self.in_joints = joints
        self.in_control_transforms = control_transforms
        self.in_constrain = constrain

        # -- Parameters
        self.option_hide_mechanicals = hide_mechanicals
        self.option_lock_end_orientations_to_control = lock_end_orientations_to_control

        # -- These are our output properties
        self.out_curve = None
        self.out_upvector_curve = None
        self.out_controls = []
        self.out_clusters = []
        self.out_upvectors = []
        self.out_trace_joints = []
        self.out_sub_tracers = []
        self.out_org = None
        self.out_no_xform_org = None
        self.out_anchor_points = []

    def create(self):
        """
        This is our main creation entrypoint method
        """
        # -- Create our org nodes which everything will reside under
        self._create_orgs()

        # -- Create the curve
        self._create_curve()

        # -- Create the transform nodes to control the curve
        for idx in range(len(self.in_control_transforms)):
            control, cluster = self._create_point_driver(
                point_index=idx,
                parent=self.out_org.full_name(),
            )
            self.out_controls.append(mref.get(control))
            self.out_clusters.append(mref.get(cluster))

        # -- Create the upvectoring curve, which allows for a more stable
        # -- twist
        self._create_upvectoring_curve()

        # -- Trace the joints and apply an ikSplineSolver
        self._create_stable_trace_joints(parent=self.out_org)
        self._apply_solve(parent=self.out_org)
        self.create_anchors()

        # -- Constrain the joints to the trace joints with mo=True
        if self.in_constrain:
            self._constrain_to_anchors()

        if self.option_hide_mechanicals:
            self.hide_mechanicals()

    def _create_orgs(self):
        """
        This will build the main organisational nodes for the setup
        """
        # -- Create the node that will act as the parent of all the component
        # -- parts we will construct
        self.out_org = mref.create("transform", name="SplineSolver")
        aniseed_toolkit.run("Tag Node", self.out_org.full_name(), "spline_org")

        # -- Ensure that matches the transform of the first control
        # -- point matrix.
        self.out_org.set_matrix(self.org_transform, space="world")

        # -- If we're given a parent then we need to parent this under
        # -- the given parent
        self.out_org.set_parent(self.in_parent)

        # -- Create the no-transform org
        self.out_no_xform_org = mref.create(
            "transform",
            name="SplineSolverNoTransform",
            parent=self.out_org.full_name(),
        )
        aniseed_toolkit.run(
            "Tag Node",
            self.out_no_xform_org.full_name(),
            "spline_no_transform_org",
        )
        self.out_no_xform_org.attr("inheritsTransform").set(False)

    def _create_upvectoring_curve(self):
        """
        This needs to be hte same as the main curve but offset/placed at the location
        of the first upvector transform.
        """
        # -- For each control we need to create an upvectoring node, and
        # -- offsetting the position by the upvector distance
        positions = []
        upvector_distance = mc.arclen(self.out_curve.full_name()) * 0.1
        for control in self.out_controls:
            # -- Create our temporary buffer object
            buffer = mref.create("transform", name="buffer", parent=control.full_name())

            # -- Match its transform and then offset it in X
            buffer.match_to(control)
            buffer.attr("translateX").set(upvector_distance)

            # -- Read out the worldspace position
            positions.append(
                mc.xform(
                    buffer.full_name(),
                    query=True,
                    translation=True,
                    worldSpace=True,
                ),
            )

            # -- Finally we can delete our temp buffer node
            mc.delete(buffer.full_name()) # UNDO

        # -- From the position list we can now build our curve
        self.out_upvector_curve = mref.get(
            mc.curve(
                point=positions,
                degree=3,
            ),
        )
        self.out_upvector_curve.attr("visibility").set(0)

        # -- Ensure the curve is a child of the no transform group so that
        # -- it does not get a double transform
        self.out_upvector_curve.set_parent(self.out_no_xform_org)

        # -- Now we need to create the cluster points
        for idx in range(len(positions)):

            # -- Clusters are funny in maya, so we need to use the selection
            mc.select(f"{self.out_upvector_curve.full_name()}.cv[{idx}]")
            cluster_xform = mref.get(mc.cluster()[1])

            # -- Hide the cluster and tag it
            cluster_xform.attr("visibility").set(False)
            aniseed_toolkit.run("Tag Node", cluster_xform.full_name(), f"CurveCluster")

            # -- Make the cluster a child of the control
            cluster_xform.set_parent(self.out_controls[idx])

        # -- we need to determine the 0-1 increment along the curve
        increment = 1.0 / float(len(self.in_joints) - 1)
        for idx in range(len(self.in_joints)):

            # -- Create the upvector transform
            upvector_transform = mref.create("transform", name="SplineUpvector", parent=self.out_no_xform_org.full_name())

            # -- Now we use the motion path command to stick the transform
            # -- to the curve. Note that for the upvector node we do not actually
            # -- care about its orientation.
            motion_path = mc.pathAnimation(
                upvector_transform.full_name(),
                curve=self.out_upvector_curve.full_name(),
                fractionMode=True,
                follow=True,
                followAxis='x',
                upAxis='y',
                worldUpType="vector",
                worldUpVector=(0, 1, 0)
            )

            # - Set the u value based on the calculated increment
            mc.cutKey(motion_path + ".uValue")
            mc.setAttr(motion_path + ".uValue", increment * idx)

            # -- The pathAnimaiton command is a pain - it adds a bunch
            # -- of keyframes. So we clear those off
            mc.cutKey(upvector_transform.full_name(), attribute="translate")
            mc.cutKey(upvector_transform.full_name(), attribute="rotate")

            # -- Finally we store the upvector so that it is accessible.
            self.out_upvectors.append(upvector_transform)

    def _create_curve(self):
        """
        This will construct the spline curve based on the given input
        transforms.
        """
        # -- Build up the point position list from the list of matrices
        positions = [
            self.position_from_matrix(matrix)
            for matrix in self.in_control_transforms
        ]

        # -- From the position list we can now build our curve
        self.out_curve = mref.get(
            mc.curve(
                point=positions,
                degree=3,
            ),
        )

        # -- Set the curve properties and parenting
        self.out_curve.attr("visibility").set(0)
        self.out_curve.match_to(self.out_org)
        self.out_curve.set_parent(self.out_no_xform_org)

        # -- Take the curve so that it is easy to find
        aniseed_toolkit.run("Tag Node", self.out_curve.full_name(), "spline_curve")

    def create_anchors(self):
        """
        Anchors are the end points that anything should be constrained to
        """
        # -- Read out the parent of the joint
        parent = self.out_trace_joints[0].parent()

        # -- Replicate the trace joints - as these will become the anchors
        anchors = mref.get(
            aniseed_toolkit.run(
                "Replicate Chain",
                from_this=self.out_trace_joints[0].name(),
                to_this=self.out_trace_joints[-1].name(),
                parent=parent.full_name(),
            ),
        )

        # -- Cycle each replicated joint
        for idx, anchor in enumerate(anchors):

            # -- Name it as an anchor
            anchor.rename(f"SplineAnchor{idx}")

            # -- The target (i.e, what it should follow) varies depending
            # -- on whether we're at the start/end of the curve and whether
            # -- we have the locking option enabled. So we resolve the constraint
            # -- target now.
            target = self.out_sub_tracers[idx]
            if idx == 0 and self.option_lock_end_orientations_to_control:
                target = self.out_controls[0]
            if idx == len(anchors) - 1 and self.option_lock_end_orientations_to_control:
                target = self.out_controls[-1]

            # -- Constrain the target to the anchor
            mc.parentConstraint(
                target.full_name(),
                anchor.full_name(),
                maintainOffset=True,
            )
            mc.scaleConstraint(
                target.full_name(),
                anchor.full_name(),
                maintainOffset=True,
            )

            self.out_anchor_points.append(anchor)


    def _constrain_to_anchors(self):
        """
        This will constrain any given "items to be constrained" to the anchors
        """
        # -- Cycle our anchor points
        for idx in range(len(self.out_anchor_points)):
            target = self.out_anchor_points[idx]
            mc.parentConstraint(
                target.full_name(),
                self.in_joints[idx],
                maintainOffset=True,
            )
            mc.scaleConstraint(
                target.full_name(),
                self.in_joints[idx],
                maintainOffset=True,
            )

    def _create_stable_trace_joints(self, parent):
        """
        We create a hierarchy of joints and transforms which
        correctly point forward and align to the upvector.
        """
        # -- Replicate the chain so we can apply the ik
        replicated_chain = mref.get(
            aniseed_toolkit.run(
                "Replicate Chain",
                from_this=self.in_joints[0],
                to_this=self.in_joints[-1],
                parent=self.in_parent,
                world=True,
            ),
        )

        # -- Name and tag each joint
        for idx, joint in enumerate(replicated_chain):
            joint.rename(f"SplineSolveJoint{idx+1}")
            aniseed_toolkit.run("Tag Node", joint.full_name(), f"SplineTraceJoint")

        # -- Ensure the chain is correctly parented
        replicated_chain[0].set_parent(parent)

        # -- Move all rotations to orients so we can run a joint
        # -- orient.
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            [j.full_name() for j in replicated_chain],
        )

        # -- Orient the joint correctly
        for joint in replicated_chain:
            mc.joint(
                joint.full_name(),
                edit=True,
                orientJoint="xyz",
                secondaryAxisOrient="ydown",
                children=True,
                zeroScaleOrient=True,
            )

        for axis in ["X", "Y", "Z"]:
            replicated_chain[-1].attr(f"rotate{axis}").set(0)
            replicated_chain[-1].attr(f"jointOrient{axis}").set(0)

        # -- We now cycle each joint and create a tracer which is aimed ahead
        for idx, joint in enumerate(replicated_chain):

            # -- Create the transform node and match its transform
            # -- to the joint
            sub_tracer = mref.create("transform", parent=joint.full_name(), name=f"SplineSubAnchor{idx}")
            sub_tracer.match_to(joint)

            # -- So long as we're not the last anchor, we can setup the constraint
            if idx != len(replicated_chain) - 1:
                mc.aimConstraint(
                    replicated_chain[idx+1].full_name(),
                    sub_tracer.full_name(),
                    aimVector=(0, 1, 0),
                    upVector=(0, 0, 1),
                    worldUpType="object",
                    worldUpObject=self.out_upvectors[idx].full_name(),
                    maintainOffset=False,
                )
            else:
                mc.aimConstraint(
                    replicated_chain[idx-1].full_name(),
                    sub_tracer.full_name(),
                    aimVector=(0, -1, 0),
                    upVector=(0, 0, 1),
                    worldUpType="object",
                    worldUpObject=self.out_upvectors[idx].full_name(),
                    maintainOffset=False,
                )

            # -- Store the sub tracers
            self.out_sub_tracers.append(sub_tracer)

        # -- Store the trace joints.
        self.out_trace_joints = replicated_chain

    def _apply_solve(self, parent):
        """
        This will apply the ik spline solve to the joints
        """
        # -- Create the ik handle
        ik_items = mref.get(
            mc.ikHandle(
                startJoint=self.out_trace_joints[0].full_name(),
                endEffector=self.out_trace_joints[-1].full_name(),
                curve=self.out_curve.full_name(),
                solver="ikSplineSolver",
                createCurve=False,
                parentCurve=False,
                priority=1,
            ),
        )
        ikh = ik_items[0]
        handle = ik_items[-1]

        # -- Set the parenting and attributes of the handle
        ikh.set_parent(parent)
        ikh.attr("visibility").set(False)

        # -- Now make the spine stretchable
        curve_info = mref.create("curveInfo")
        self.out_curve.attr("local").connect(curve_info.attr("inputCurve"))

        # -- We need to support scaling, so we read the global scale
        # -- of the parent and negate it
        decompose_matrix = mref.create("decomposeMatrix")
        parent.attr("worldMatrix[0]").connect(decompose_matrix.attr("inputMatrix"))

        scale_divider = mref.create("floatMath")
        scale_divider.attr("operation").set(3)  # Divide
        scale_divider.attr("floatA").set(1)

        decompose_matrix.attr("outputScaleX").connect(scale_divider.attr("floatB"))

        scale_multiplier = mref.create("floatMath")
        scale_multiplier.attr("operation").set(2) # Multiple
        scale_divider.attr("outFloat").connect(scale_multiplier.attr("floatA"))
        curve_info.attr("arcLength").connect(scale_multiplier.attr("floatB"))

        math_node = mref.create("floatMath")
        math_node.attr("operation").set(3) # -- Divide
        scale_multiplier.attr("outFloat").connect(math_node.attr("floatA"))
        math_node.attr("floatB").set(len(self.out_trace_joints) - 1)

        for joint in self.out_trace_joints:
            mul_node = mref.create("floatMath")

            math_node.attr("outFloat").connect(mul_node.attr("floatA"))
            mul_node.attr("floatB").set(1)
            mul_node.attr("operation").set(2)
            mul_node.attr("outFloat").connect(joint.attr("translateX"))

    def _create_point_driver(self, point_index, parent):
        """
        This will create a transform (control) to drive the cv with the
        given point index
        """
        # -- Determine the suffix the name should be given
        suffix = chr(point_index + self.ord_a).upper()

        # -- Create the actual transform
        control = mref.create(
            "transform",
            name=f"curveControl{suffix}",
            parent=parent,
        )
        aniseed_toolkit.run("Tag Node", control.full_name(), f"CurveControl{point_index}")

        control.set_matrix(
            self.in_control_transforms[point_index],
            space="object",
        )

        # -- Get the address (name) of the cv so that we can create a
        # -- cluster from it. Sadly maya behaves in different ways with the
        # -- cluster command depending on what you have selected, hence
        # -- the selection call.
        mc.select(f"{self.out_curve.full_name()}.cv[{point_index}]")
        cluster_xform = mref.get(mc.cluster()[1])

        cluster_xform.attr("visibility").set(False)
        aniseed_toolkit.run("Tag Node", cluster_xform.full_name(), f"CurveCluster")

        cluster_xform.set_parent(control)
        return control, cluster_xform

    def position_from_matrix(self, matrix):
        """
        Read out the position components of the matrix.
        """
        return [
            matrix[-4],
            matrix[-3],
            matrix[-2],
        ]

    def hide_mechanicals(self):
        """
        This will hide the various parts of the setup which are considered
        to be mechanical (i.e, not animator facing).
        """
        self.hide(self.out_curve)
        self.hide(self.out_clusters)
        self.hide(self.out_trace_joints)
        self.hide(self.out_no_xform_org)
        self.hide(self.out_anchor_points)

    def hide(self, node_or_nodes):
        """
        This is a convenience function for hiding based on whether the
        node is a joint or not.
        """
        if not isinstance(node_or_nodes, list):
            node_or_nodes = [node_or_nodes]

        for node in node_or_nodes:
            node = mref.get(node)
            draw_style = f"{node.full_name()}.drawStyle"
            visibility = f"{node.full_name()}.visibility"
            if mc.objExists(draw_style):
                mc.setAttr(draw_style, 2)
                continue

            if mc.objExists(visibility):
                mc.setAttr(visibility, False)
