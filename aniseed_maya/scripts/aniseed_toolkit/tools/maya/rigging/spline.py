import maya.cmds as mc
import aniseed_toolkit


class CreateSoftIkSetup(aniseed_toolkit.Tool):

    identifier = "Create Spline Setup"
    classification = "Rigging"
    categories = [
        "Rigging",
    ]

    def run(
        self,
            parent,
            joints,
            control_transforms,
            upvector_transforms,
            constrain=True,
            lock_end_orientations=True,
    ):
        spline_solve = SimpleSplineSetup(
            parent,
            joints,
            control_transforms,
            upvector_transforms,
            constrain=constrain,
            lock_end_orientations_to_control=lock_end_orientations,
        )
        spline_solve.create()
        return spline_solve


class SimpleSplineSetup:
    degree = 3
    knots = [
        0,
        0,
        0,
        1,
        1,
        1,
    ]

    ord_a = 97
    ord_b = 98
    ord_c = 99
    ord_d = 100

    def __init__(
            self,
            parent,
            joints,
            control_transforms,
            upvector_transforms,
            constrain=True,
            hide_mechanicals=True,
            lock_end_orientations_to_control=True,
    ):
        # -- These are our input variables
        self.in_parent = parent
        self.in_joints = joints
        self.in_control_transforms = control_transforms
        self.in_upvector_transforms = upvector_transforms
        self.in_constrain = constrain

        # -- Parameters
        self.option_hide_mechanicals = hide_mechanicals
        self.option_lock_end_orientations_to_control = lock_end_orientations_to_control

        # -- These are our output properties
        self._m_out_curve = None
        self._m_out_controls = []
        self._m_out_clusters = []
        self._m_out_upvectors = [None, None]
        self._m_out_trace_joints = []
        self._m_out_org = None
        self._m_out_no_xform_org = None
        self._m_out_anchor_points = []

    @property
    def out_org(self):
        return aniseed_toolkit.run("MObject Name",self._m_out_org)

    @out_org.setter
    def out_org(self, value):
        self._m_out_org = aniseed_toolkit.run("Get MObject", value)

    @property
    def out_curve(self):
        return aniseed_toolkit.run("MObject Name",self._m_out_curve)

    @out_curve.setter
    def out_curve(self, value):
        self._m_out_curve = aniseed_toolkit.run("Get MObject", value)

    @property
    def out_controls(self):
        return [
            aniseed_toolkit.run("MObject Name",control)
            for control in self._m_out_controls
        ]

    @out_controls.setter
    def out_controls(self, controls):
        self._m_out_controls = [
            aniseed_toolkit.run("Get MObject",control)
            for control in controls
        ]

    @property
    def out_clusters(self):
        return [
            aniseed_toolkit.run("MObject Name", cluster)
            for cluster in self._m_out_clusters
        ]

    @out_clusters.setter
    def out_clusters(self, clusters):
        self._m_out_clusters = [
            aniseed_toolkit.run("Get MObject",cluster)
            for cluster in clusters
        ]

    @property
    def out_upvectors(self):
        return [
            aniseed_toolkit.run("MObject Name", upvector)
            for upvector in self._m_out_upvectors
        ]

    @out_upvectors.setter
    def out_upvectors(self, upvectors):
        self._m_out_upvectors = [
            aniseed_toolkit.run("Get MObject",upvector)
            for upvector in upvectors
        ]

    @property
    def out_trace_joints(self):
        return [
            aniseed_toolkit.run("MObject Name", joint)
            for joint in self._m_out_trace_joints
        ]


    @out_trace_joints.setter
    def out_trace_joints(self, joints):
        self._m_out_trace_joints = [
            aniseed_toolkit.run("Get MObject",joint)
            for joint in joints
        ]
    @property
    def out_anchor_points(self):

        return [
            aniseed_toolkit.run("MObject Name", joint)
            for joint in self._m_out_anchor_points
        ]

    @out_anchor_points.setter
    def out_anchor_points(self, joints):
        self._m_out_anchor_points = [
            aniseed_toolkit.run("Get MObject",joint)
            for joint in joints
        ]

    @property
    def out_no_xform_org(self):
        return aniseed_toolkit.run("MObject Name", self._m_out_no_xform_org)

    @out_no_xform_org.setter
    def out_no_xform_org(self, value):
        self._m_out_no_xform_org = aniseed_toolkit.run("Get MObject", value)

    def create(self):

        # -- Create the node that will act as the parent of all the component
        # -- parts we will construct
        self.out_org = mc.createNode(
            "transform",
            name="SplineSolver",
        )
        aniseed_toolkit.run("Tag Node", self.out_org, "spline_org")

        # -- Ensure that matches the transform of the first control
        # -- point matrix.
        mc.xform(
            self.out_org,
            matrix=self.in_control_transforms[0],
            worldSpace=True,
        )

        # -- If we're given a parent then we need to parent this under
        # -- the given parent
        if self.in_parent:
            mc.parent(self.out_org, self.in_parent)

        # -- Create the no-transform org
        self.out_no_xform_org = mc.createNode(
            "transform",
            name="SplineSolverNoTransform",
        )
        mc.parent(
            self.out_no_xform_org,
            self.out_org,
        )
        aniseed_toolkit.run(
            "Tag Node",
            self.out_no_xform_org,
            "spline_no_transform_org",
        )
        mc.setAttr(f"{self.out_no_xform_org}.inheritsTransform", False)

        # -- Build up the point position list from the list of matrices
        positions = [
            self.position_from_matrix(matrix)
            for matrix in self.in_control_transforms
        ]

        # -- From the position list we can now build our curve
        self.curve = mc.curve(
            p=positions,
            degree=self.degree,
            knot=self.knots
        )
        aniseed_toolkit.run("Tag Node", self.curve, "spline_curve")

        # -- Parent the curve under our org
        mc.parent(
            self.curve,
            self.out_no_xform_org,
        )

        # -- Create the transform nodes to control the curve
        controls = []
        clusters = []
        for idx in range(4):
            control, cluster = self._create_point_driver(
                point_index=idx,
                parent=self.out_org,
            )
            controls.append(control)
            clusters.append(cluster)
        self.out_clusters = clusters
        self.out_controls = controls

        # -- Cluster the curve to the transform nodes
        upvectors = []
        for idx in range(2):
            upvectors.append(
                self._create_upvector(
                    upvector_index=idx,
                    parent=self.out_org,
                ),
            )
        self.out_upvectors = upvectors

        # -- Trace the joints and apply an ikSplineSolver
        self._create_stable_trace_joints(parent=self.out_org)
        self._apply_solve(parent=self.out_org)
        self.create_anchors()

        # -- Constrain the joints to the trace joints with mo=True
        if self.in_constrain:
            self._constrain_to_tracers()

        if self.option_hide_mechanicals:
            self.hide_mechanicals()

    def create_anchors(self):
        parent = mc.listRelatives(self.out_trace_joints[0], parent=True)

        anchors = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.out_trace_joints[0],
            to_this=self.out_trace_joints[-1],
            parent=parent,
        )
        resolved_anchors = []
        for idx, anchor in enumerate(anchors):

            target = self.out_trace_joints[idx]

            if idx == 0 and self.option_lock_end_orientations_to_control:
                target = self.out_controls[0]

            if idx == len(anchors) - 1 and self.option_lock_end_orientations_to_control:
                target = self.out_controls[-1]

            mc.parentConstraint(
                target,
                anchor,
                maintainOffset=True,
            )
            mc.scaleConstraint(
                target,
                anchor,
                maintainOffset=True,
            )

            resolved_anchors.append(mc.rename(anchor, f"SplineAnchor{idx}"))

        self.out_anchor_points = resolved_anchors


    def _constrain_to_tracers(self):
        for idx in range(len(self.out_trace_joints)):

            target = self.out_trace_joints[idx]

            if idx == 0 and self.option_lock_end_orientations_to_control:
                target = self.out_controls[0]

            if idx == len(self.out_trace_joints) - 1 and self.option_lock_end_orientations_to_control:
                target = self.out_controls[-1]

            mc.parentConstraint(
                target,
                self.in_joints[idx],
                maintainOffset=True,
            )
            mc.scaleConstraint(
                target,
                self.in_joints[idx],
                maintainOffset=True,
            )

    def _create_stable_trace_joints(self, parent):

        # -- Now replicate the chain so we can apply the ik
        replicated_chain = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.in_joints[0],
            to_this=self.in_joints[-1],
            parent=self.in_parent,
            world=True,
        )

        replicated_chain = [
            mc.rename(joint, f"SplineSolveJoint{idx+1}")
            for idx, joint in enumerate(replicated_chain)
        ]

        for joint in replicated_chain:
            aniseed_toolkit.run("Tag Node", joint, f"SplineTraceJoint")

        mc.parent(
            replicated_chain[0],
            parent,
        )

        # -- Move all orients
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            replicated_chain,
        )

        for joint in replicated_chain:
            # joint -e -oj xyz -sao ydown -ch -zso;
            mc.joint(
                joint,
                e=True,
                oj="xyz",
                sao="ydown",
                ch=True,
                zso=True,
            )

        for axis in ["X", "Y", "Z"]:
            mc.setAttr(f"{replicated_chain[-1]}.rotate{axis}", 0)
            mc.setAttr(f"{replicated_chain[-1]}.jointOrient{axis}", 0)

        self.out_trace_joints = replicated_chain

    def _apply_solve(self, parent):

        # scale_tracker = mc.createNode("transform")
        # world_tracker = mc.createNode("transform")
        # mc.parent(world_tracker, parent)
        # mc.parent(scale_tracker, world_tracker)
        # mc.setAttr(f"{world_tracker}.inheritsTransform", False)
        # mc.scaleConstraint(
        #     world_tracker,
        #     scale_tracker,
        # )
        # scale_math = mc.createNode("floatMath")
        # mc.setAttr(f"{scale_math}.floatA", 1.0)
        # # mc.setAttr(f"{scale_math}.floatB", 1.0)
        # mc.connectAttr(f"{world_tracker}.scaleX", f"{scale_math}.floatB")
        # mc.setAttr(f"{scale_math}.operation", 3)  # Divide

        # -- Create the ik handle
        ikh, effector = mc.ikHandle(
            startJoint=self.out_trace_joints[0],
            endEffector=self.out_trace_joints[-1],
            curve=self.curve,
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

        mc.connectAttr(
            f"{self.out_upvectors[0]}.worldMatrix[0]",
            f"{ikh}.dWorldUpMatrix",
        )

        mc.connectAttr(
            f"{self.out_upvectors[1]}.worldMatrix[0]",
            f"{ikh}.dWorldUpMatrixEnd",
        )

        # -- Now make the spine stretchable
        curve_info = mc.createNode("curveInfo")

        mc.connectAttr(
            f"{self.curve}.local",
            f"{curve_info}.inputCurve",
        )

        # -- We need to support scaling, so we read the global scale
        # -- of the parent and negate it
        decompose_matrix = mc.createNode("decomposeMatrix")
        mc.connectAttr(
            f"{parent}.worldMatrix[0]",
            f"{decompose_matrix}.inputMatrix",
        )

        scale_divider = mc.createNode("floatMath")
        mc.setAttr(f"{scale_divider}.operation", 3)  # -- Divide
        mc.setAttr(f"{scale_divider}.floatA", 1)  # -- Divide
        mc.connectAttr(
            f"{decompose_matrix}.outputScaleX",
            f"{scale_divider}.floatB",
        )

        scale_multiplier = mc.createNode("floatMath")
        mc.setAttr(f"{scale_multiplier}.operation", 2) # Multiply
        mc.connectAttr(
            f"{scale_divider}.outFloat",
            f"{scale_multiplier}.floatA",
        )
        mc.connectAttr(
            f"{curve_info}.arcLength",
            f"{scale_multiplier}.floatB",
        )
        math_node = mc.createNode("floatMath")

        mc.setAttr(
            f"{math_node}.operation",
            3,  # -- Divide
        )

        mc.connectAttr(
            f"{scale_multiplier}.outFloat",
            f"{math_node}.floatA",
        )

        mc.setAttr(
            f"{math_node}.floatB",
            len(self.out_trace_joints) - 1,
        )

        for joint in self.out_trace_joints:
            mul_node = mc.createNode("floatMath")

            mc.connectAttr(
                f"{math_node}.outFloat",
                mul_node + ".floatA",
            )

            mc.setAttr(
                f"{mul_node}.floatB",
                1,
            )

            mc.setAttr(
                f"{mul_node}.operation",
                2,  # -- Divide
            )

            mc.connectAttr(
                f"{mul_node}.outFloat",
                f"{joint}.translateX",
            )

    def _create_upvector(self, upvector_index, parent):
        """
        This will create the upvector transforms
        """
        # -- Determine the suffix the name should be given
        suffix = chr(upvector_index + self.ord_a).upper()

        # -- Create the actual transform
        control = mc.createNode(
            "transform",
            name=f"upvectorControl{suffix}",
        )
        aniseed_toolkit.run("Tag Node", control, f"UpvectorControl{suffix}")

        # -- Parent the transform
        mc.parent(
            control,
            parent,
        )

        # -- Set the transform of the control to that of the upvector
        # -- position we were given
        mc.xform(
            control,
            m=self.in_upvector_transforms[upvector_index],
            worldSpace=True,
        )

        # -- Finally store the upvector
        return control


    def _create_point_driver(self, point_index, parent):
        """
        This will create a transform (control) to drive the cv with the
        given point index
        """
        # -- Determine the suffix the name should be given
        suffix = chr(point_index + self.ord_a).upper()

        # -- Create the actual transform
        control = mc.createNode(
            "transform",
            name=f"curveControl{suffix}",
        )
        aniseed_toolkit.run("Tag Node", control, f"CurveControl{suffix}")

        # -- Parent the transform
        mc.parent(
            control,
            parent,
        )

        # -- Match the control to the matrix transform we are given
        # -- as an instance variable
        mc.xform(
            control,
            m=self.in_control_transforms[point_index],
            worldSpace=True,
        )

        # -- Get the address (name) of the cv so that we can create a
        # -- cluster from it. Sadly maya behaves in different ways with the
        # -- cluster command depending on what you have selected, hence
        # -- the selection call.
        mc.select(f"{self.curve}.cv[{point_index}]")
        cluster_xform = mc.cluster()[1]

        aniseed_toolkit.run("Tag Node", cluster_xform, f"CurveCluster{suffix}")

        # -- Finally we parent the cluster xform under the control
        mc.parent(cluster_xform, control)

        return control, cluster_xform

    def position_from_matrix(self, matrix):

        return [
            matrix[-4],
            matrix[-3],
            matrix[-2],
        ]

    def hide_mechanicals(self):
        self.hide(self.curve)
        self.hide(self.out_clusters)
        self.hide(self.out_trace_joints)
        self.hide(self.out_no_xform_org)

    def hide(self, node_or_nodes):
        if not isinstance(node_or_nodes, list):
            node_or_nodes = [node_or_nodes]

        for node in node_or_nodes:
            draw_style = f"{node}.drawStyle"
            visibility = f"{node}.visibility"

            if mc.objExists(draw_style):
                mc.setAttr(draw_style, 2)
                continue

            if mc.objExists(visibility):
                mc.setAttr(visibility, False)
