"""
Provides the BendyTwisters class, which builds a bendy, twisting and
squashing chain of joints between two joints.

A four point bezier curve runs from the start joint to the end joint, with
its points at 0%, 33.3%, 66.6% and 100% of the way between them. Each point is
a cluster under a control whose org is point constrained between the two
joints, so the points keep their percentage as the joints move, and orient
constrained to the start joint, so the controls bend the curve relative to
the bone they track.

The twist joints ride along the curve (evenly spread by length), with their
x axis along the curve tangent. They follow the start joint's convention: if
its x axis points down the bone their x axis points down the curve, and if it
points back up the bone (as on a behaviour mirrored chain) their x axis
points back up the curve. They take their roll from the start joint and
add a twist blended along the curve: at the start, the twist of the start
twist node relative to the start joint, and at the end, the twist of the end
twist node relative to the start joint. Both are measured around the line
between the joints and are zero at rest. By default the start twist node is
the start joint itself (so it adds nothing) and the end twist node is the end
joint. Giving a start twist node (such as a shoulder or ik root) anchors the
roll of the start of the curve to that node, so rolling the start joint
spreads a twist along the curve.

As the distance between the joints shrinks the twist joints grow in y and z
(and shrink as it grows). How much each joint scales is mapped through the
scaleFalloff ramp attribute on the first control, sampled at the joint's
percentage along the curve. The squashAndStretchAlpha attribute on the same
control blends the effect from none (0) to full (1).

The structure built is:

    BendyTwisters (org)
        Bendy 01 -> 04 (controls, orgs point constrained between the joints
                        and orient constrained to the start joint)
            BendyCluster (cluster handle driving the matching curve point)
        BendyNoTransform (does not inherit transforms)
            BendyCurve (bezier curve)

    start joint (or the given joint parent)
        BendyTwist 01 -> ## (joints, placed through their offsetParentMatrix)
"""
import typing

from maya import cmds
from maya.api import OpenMaya as om

import mref
import aniseed_utilities as au

if typing.TYPE_CHECKING:
    import aniseed


class BendyTwisters:
    """
    Builds the bendy twisters setup between two joints.

    Args:
        start_joint: The joint the curve starts at
        end_joint: The joint the curve ends at
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name, so
            "upperArm" names the twist joints "UpperArmBendyTwist"
        location: The location token (config.left, config.middle etc)
        count: How many twist joints to create
        parent: Optional node to parent the setup's org under (the org is
            matched to it). If not given the org is created at the scene root.
        joint_parent: Optional node to parent the twist joints under. If not
            given they are parented under the start joint.
        shape_scale: Optional scale for the control shapes. If not given it
            is derived from the distance between the joints.
        start_twist_node: Optional node whose roll the start of the curve
            holds. If not given the start joint's roll is used.
        end_twist_node: Optional node whose roll the end of the curve
            reaches. If not given the end joint is used.

    Usage:
        setup = BendyTwisters(upper, lower, config, "upperArm", config.left, 5)
        setup.build()
    """

    # -- Where each curve point sits between the start and end joint
    POINT_PERCENTAGES = [0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0]

    # -- The default scaleFalloff ramp as (position, value, interpolation)
    # -- where an interpolation of 2 is smooth. This scales the middle of
    # -- the curve the most and leaves the ends alone.
    DEFAULT_FALLOFF = [(0.0, 0.0, 2), (0.5, 1.0, 2), (1.0, 0.0, 2)]

    def __init__(
            self,
            start_joint: mref.ReferencedItem,
            end_joint: mref.ReferencedItem,
            config: "aniseed.RigConfiguration",
            prefix: str,
            location: str,
            count: int,
            parent: str = None,
            joint_parent: str = None,
            shape_scale: float = None,
            start_twist_node: str = None,
            end_twist_node: str = None,
    ):
        if count < 1:
            raise ValueError("BendyTwisters needs at least one twist joint")

        self.start_joint = mref.get(start_joint)
        self.end_joint = mref.get(end_joint)
        self.start_twist_node = mref.get(start_twist_node) if start_twist_node else None
        self.end_twist_node = mref.get(end_twist_node or end_joint)
        self.config = config
        self.location = location
        self.count = count
        self.parent = parent
        self.joint_parent = joint_parent or self.start_joint.full_name()

        # -- "leg" becomes "Leg" so it reads as part of a camel cased description
        self.prefix = prefix[:1].upper() + prefix[1:]

        self.rest_length = self._distance(self.start_joint, self.end_joint)

        # -- 1 if the start joint's x axis points down the bone, -1 if it
        # -- points back up it (a behaviour mirrored chain)
        bone = (
            om.MVector(self.end_joint.get_position(space="world")) -
            om.MVector(self.start_joint.get_position(space="world"))
        )
        x_axis = om.MVector(self.start_joint.axis_vector("x", space="world"))
        self.direction = 1 if x_axis * bone >= 0 else -1
        self.shape_scale = shape_scale or self.rest_length / 15.0

        # -- Populated by build
        self.org: str = ""
        self.no_transform_org: str = ""
        self.curve: str = ""
        self.controls: list[au.rig.control.Control] = []
        self.clusters: list[str] = []
        self.twist_joints: list[str] = []

    def build(self) -> "BendyTwisters":
        """
        Creates the whole setup.

        Returns:
            This instance, so the created nodes can be read from it
        """
        for plugin in ["matrixNodes", "quatNodes", "lookdevKit"]:
            if not cmds.pluginInfo(plugin, query=True, loaded=True):
                cmds.loadPlugin(plugin, quiet=True)

        self._create_orgs()
        self._create_curve()
        self._create_controls()
        self._create_squash_attributes()
        self._create_twist_joints()
        return self

    @property
    def percentages(self) -> list[float]:
        """
        The percentage along the curve of each twist joint. A single joint
        sits in the middle of the curve.
        """
        if self.count == 1:
            return [0.5]
        return [idx / (self.count - 1.0) for idx in range(self.count)]

    def _description(self, label: str) -> str:
        """
        Returns the description for the given label with the prefix applied
        """
        return f"{self.prefix}{label}"

    def _name(self, classification: str, label: str, counter: int = 1) -> str:
        """
        Returns a unique name for the given classification and label
        """
        return self.config.generate_name(
            classification=classification,
            description=self._description(label),
            location=self.location,
            counter=counter,
        )

    def _create_node(self, node_type: str, label: str) -> mref.ReferencedItem:
        """
        Creates a mechanical utility node named for the label
        """
        return mref.create(node_type, name=self._name(self.config.mechanical, label))

    @staticmethod
    def _distance(node_a: mref.ReferencedItem, node_b: mref.ReferencedItem) -> float:
        a = om.MVector(node_a.get_position(space="world"))
        b = om.MVector(node_b.get_position(space="world"))
        return (b - a).length()

    @staticmethod
    def _world_matrix(node: mref.ReferencedItem) -> om.MMatrix:
        return om.MMatrix(cmds.xform(node.full_name(), query=True, matrix=True, worldSpace=True))

    def _point_position(self, percentage: float) -> list[float]:
        """
        Returns the world position the given percentage between the joints
        """
        start = om.MVector(self.start_joint.get_position(space="world"))
        end = om.MVector(self.end_joint.get_position(space="world"))
        return list(start + (end - start) * percentage)

    def _create_orgs(self):
        """
        Creates the org which every part of the setup lives under, and the
        org which the curve lives in. The curve is moved by clusters which
        work in world space, so its org must not inherit any transform.
        """
        self.org = au.scene.transforms.create(
            classification=self.config.organisational,
            description=self._description("BendyTwisters"),
            location=self.location,
            config=self.config,
            parent=self.parent,
            match_to=self.parent,
        )

        self.no_transform_org = au.scene.transforms.create(
            classification=self.config.organisational,
            description=self._description("BendyNoTransform"),
            location=self.location,
            config=self.config,
            parent=self.org,
        )
        mref.get(self.no_transform_org).attr("inheritsTransform").set(False)

    def _create_curve(self):
        """
        Creates the four point bezier curve between the two joints
        """
        curve = cmds.curve(
            bezier=True,
            degree=3,
            point=[self._point_position(p) for p in self.POINT_PERCENTAGES],
            knot=[0, 0, 0, 1, 1, 1],
            name=self._name(self.config.mechanical, "BendyCurve"),
        )
        cmds.parent(curve, self.no_transform_org)

        # -- Show the curve as a reference so it can be seen but not picked
        curve = mref.get(curve)
        curve.attr("overrideEnabled").set(True)
        curve.attr("overrideDisplayType").set(2)
        self.curve = curve.full_name()

    def _create_controls(self):
        """
        Creates a control for each curve point, with a cluster under it
        driving the point. Each control's org is point constrained between
        the two joints so it keeps its percentage between them, and orient
        constrained to the start joint so it follows the bone's orientation.
        """
        for idx, percentage in enumerate(self.POINT_PERCENTAGES):
            control = au.rig.control.create(
                description=self._description("Bendy"),
                location=self.location,
                parent=self.org,
                shape="core_sphere",
                config=self.config,
                match_to=self.start_joint.full_name(),
                shape_scale=self.shape_scale,
                counter=idx + 1,
            )
            mref.get(control.org).set_position(self._point_position(percentage), space="world")

            for target, weight in [(self.start_joint, 1.0 - percentage), (self.end_joint, percentage)]:
                if weight:
                    mref.pointConstraint(
                        target.full_name(),
                        control.org,
                        weight=weight,
                        maintainOffset=False,
                    )

            # -- The org was matched to the start joint, so there is no offset
            mref.orientConstraint(
                self.start_joint.full_name(),
                control.org,
                maintainOffset=False,
            )

            # -- Clusters are created from the selection, so select the cv
            cmds.select(f"{self.curve}.cv[{idx}]")
            cluster, handle = cmds.cluster(name=self._name(self.config.mechanical, "BendyCluster", idx + 1))
            handle = mref.get(handle)
            handle.rename(self._name(self.config.mechanical, "BendyClusterHandle", idx + 1))
            handle.set_parent(control.ctl)
            handle.attr("visibility").set(False)

            self.controls.append(control)
            self.clusters.append(handle.full_name())

        cmds.select(clear=True)

    def _create_squash_attributes(self):
        """
        Adds the squashAndStretchAlpha attribute and the scaleFalloff ramp
        attribute to the first control
        """
        ctl = self.controls[0].ctl

        cmds.addAttr(
            ctl,
            longName="squashAndStretchAlpha",
            attributeType="float",
            minValue=0,
            maxValue=1,
            defaultValue=1,
            keyable=True,
        )

        cmds.addAttr(ctl, longName="scaleFalloff", attributeType="compound", numberOfChildren=3, multi=True)
        cmds.addAttr(ctl, longName="scaleFalloff_Position", attributeType="float", parent="scaleFalloff")
        cmds.addAttr(ctl, longName="scaleFalloff_FloatValue", attributeType="float", parent="scaleFalloff")
        cmds.addAttr(
            ctl,
            longName="scaleFalloff_Interp",
            attributeType="enum",
            enumName="None:Linear:Smooth:Spline",
            parent="scaleFalloff",
        )

        for idx, (position, value, interpolation) in enumerate(self.DEFAULT_FALLOFF):
            cmds.setAttr(f"{ctl}.scaleFalloff[{idx}].scaleFalloff_Position", position)
            cmds.setAttr(f"{ctl}.scaleFalloff[{idx}].scaleFalloff_FloatValue", value)
            cmds.setAttr(f"{ctl}.scaleFalloff[{idx}].scaleFalloff_Interp", interpolation)

    def _create_twist_joints(self):
        """
        Creates the twist joints and drives each one along the curve
        """
        end_twist = self._create_twist_reader(self.end_twist_node, "BendyTwist")
        start_twist = None
        if self.start_twist_node:
            start_twist = self._create_twist_reader(self.start_twist_node, "BendyStartTwist")

        stretch_ratio = self._create_stretch_ratio()

        # -- The twist joints take their scale from the org, so the whole
        # -- setup can be scaled
        org_scale = self._create_node("decomposeMatrix", "BendyOrgScale")
        mref.get(f"{self.org}.worldMatrix[0]").connect(org_scale.attr("inputMatrix"))

        for idx, percentage in enumerate(self.percentages):
            joint = au.scene.joints.create(
                description=self._description("BendyTwist"),
                location=self.location,
                parent=self.joint_parent,
                config=self.config,
            )
            cmds.select(clear=True)

            joint = mref.get(joint)
            joint.attr("segmentScaleCompensate").set(False)
            for attribute in ["translate", "rotate", "jointOrient"]:
                joint.attr(attribute).set(0, 0, 0)

            self._attach_to_curve(joint, percentage, start_twist, end_twist, org_scale)
            self._apply_squash(joint, percentage, stretch_ratio)
            self.twist_joints.append(joint.full_name())

    def _twist_frame(self) -> om.MMatrix:
        """
        Returns the rest frame the twist is measured in. Its x axis runs from
        the start joint to the end joint and its y axis is the start joint's y
        axis (or z axis if the y axis runs along the bone).
        """
        x_axis = (
            om.MVector(self.end_joint.get_position(space="world")) -
            om.MVector(self.start_joint.get_position(space="world"))
        ).normal()

        up_axis = om.MVector(self.start_joint.axis_vector("y", space="world"))
        if abs(up_axis.normal() * x_axis) > 0.99:
            up_axis = om.MVector(self.start_joint.axis_vector("z", space="world"))

        z_axis = (x_axis ^ up_axis).normal()
        y_axis = (z_axis ^ x_axis).normal()
        position = self.start_joint.get_position(space="world")

        return om.MMatrix([
            list(x_axis) + [0],
            list(y_axis) + [0],
            list(z_axis) + [0],
            list(position) + [1],
        ])

    def _create_twist_reader(self, node: mref.ReferencedItem, label: str) -> str:
        """
        Creates the nodes which read the twist of the given node relative to
        the start joint, around the line between the joints, and returns the
        plug which outputs it. It reads zero at rest.

            relative = (frame in node space) * node.worldMatrix
                       * start.worldInverseMatrix * (frame in start space)^-1

        The twist is taken from the relative rotation by swing/twist
        decomposition: zeroing the y and z of its quaternion leaves the
        rotation around x.
        """
        frame = self._twist_frame()
        frame_in_node = frame * self._world_matrix(node).inverse()
        frame_in_start_inverse = self._world_matrix(self.start_joint) * frame.inverse()

        relative = self._create_node("multMatrix", f"{label}Relative")
        relative.attr("matrixIn[0]").set(list(frame_in_node), type="matrix")
        mref.get(f"{node.full_name()}.worldMatrix[0]").connect(relative.attr("matrixIn[1]"))
        mref.get(f"{self.start_joint.full_name()}.worldInverseMatrix[0]").connect(relative.attr("matrixIn[2]"))
        relative.attr("matrixIn[3]").set(list(frame_in_start_inverse), type="matrix")

        decompose = self._create_node("decomposeMatrix", f"{label}Decompose")
        relative.attr("matrixSum").connect(decompose.attr("inputMatrix"))

        normalize = self._create_node("quatNormalize", f"{label}Quat")
        decompose.attr("outputQuatX").connect(normalize.attr("inputQuatX"))
        decompose.attr("outputQuatW").connect(normalize.attr("inputQuatW"))

        to_euler = self._create_node("quatToEuler", f"{label}Euler")
        normalize.attr("outputQuat").connect(to_euler.attr("inputQuat"))

        return f"{to_euler.full_name()}.outputRotateX"

    def _create_stretch_ratio(self) -> str:
        """
        Creates the nodes which output how far the joints have stretched
        beyond their rest distance, as
        ((rest distance / distance) - 1) * squashAndStretchAlpha. It is zero
        at rest (or with an alpha of zero) and positive as the joints move
        closer together. The distance is measured in the org's space so
        scaling the org does not read as a stretch.
        """
        distance = self._create_node("distanceBetween", "BendyDistance")
        for idx, joint in enumerate([self.start_joint, self.end_joint]):
            to_org = self._create_node("multMatrix", "BendyDistanceSpace")
            mref.get(f"{joint.full_name()}.worldMatrix[0]").connect(to_org.attr("matrixIn[0]"))
            mref.get(f"{self.org}.worldInverseMatrix[0]").connect(to_org.attr("matrixIn[1]"))
            to_org.attr("matrixSum").connect(distance.attr(f"inMatrix{idx + 1}"))

        ratio = self._create_node("floatMath", "BendyStretchRatio")
        ratio.attr("operation").set(3)  # -- Divide
        ratio.attr("floatA").set(self.rest_length / self._org_scale())
        distance.attr("distance").connect(ratio.attr("floatB"))

        offset = self._create_node("floatMath", "BendyStretchOffset")
        offset.attr("operation").set(1)  # -- Subtract
        ratio.attr("outFloat").connect(offset.attr("floatA"))
        offset.attr("floatB").set(1)

        alpha = self._create_node("floatMath", "BendyStretchAlpha")
        alpha.attr("operation").set(2)  # -- Multiply
        offset.attr("outFloat").connect(alpha.attr("floatA"))
        mref.get(f"{self.controls[0].ctl}.squashAndStretchAlpha").connect(alpha.attr("floatB"))

        return f"{alpha.full_name()}.outFloat"

    def _org_scale(self) -> float:
        """
        Returns the world scale of the org, as the rest length is stored in
        its space
        """
        return om.MTransformationMatrix(om.MMatrix(cmds.getAttr(f"{self.org}.worldMatrix[0]"))).scale(om.MSpace.kWorld)[0]

    def _attach_to_curve(
            self,
            joint: mref.ReferencedItem,
            percentage: float,
            start_twist: typing.Optional[str],
            end_twist: str,
            org_scale,
    ):
        """
        Places the joint along the curve (by length) through its
        offsetParentMatrix, with its x axis along the tangent, its roll taken
        from the start joint plus the twists blended by its percentage:

            twist = start_twist * (1 - percentage) + end_twist * percentage

        On a mirrored chain the front axis is inverted, so x points back up
        the curve, and as the motion path's front twist is around that
        inverted axis the twist is negated.
        """
        motion_path = self._create_node("motionPath", "BendyTwistPath")
        mref.get(f"{self.curve}.worldSpace[0]").connect(motion_path.attr("geometryPath"))
        motion_path.attr("fractionMode").set(True)
        motion_path.attr("follow").set(True)
        motion_path.attr("frontAxis").set(0)  # -- X
        motion_path.attr("inverseFront").set(self.direction < 0)
        motion_path.attr("upAxis").set(1)  # -- Y
        motion_path.attr("worldUpType").set(2)  # -- Object rotation up

        # -- uValue is a doubleLinear attribute, so setAttr would read the
        # -- fraction in the scene's linear unit. The plug takes the internal
        # -- value, which is the fraction itself.
        om.MSelectionList().add(f"{motion_path.full_name()}.uValue").getPlug(0).setDouble(percentage)

        # -- The up vector is the twist frame's y axis, held by the start joint
        up_vector = om.MVector(list(self._twist_frame())[4:7]) * self._world_matrix(self.start_joint).inverse()
        motion_path.attr("worldUpVector").set(*up_vector)
        mref.get(f"{self.start_joint.full_name()}.worldMatrix[0]").connect(motion_path.attr("worldUpMatrix"))

        twist_share = self._create_node("floatMath", "BendyTwistShare")
        twist_share.attr("operation").set(2)  # -- Multiply
        mref.get(end_twist).connect(twist_share.attr("floatA"))
        twist_share.attr("floatB").set(percentage * self.direction)
        twist = twist_share.attr("outFloat")

        if start_twist:
            start_share = self._create_node("floatMath", "BendyStartTwistShare")
            start_share.attr("operation").set(2)  # -- Multiply
            mref.get(start_twist).connect(start_share.attr("floatA"))
            start_share.attr("floatB").set((1.0 - percentage) * self.direction)

            total = self._create_node("floatMath", "BendyTwistTotal")
            total.attr("operation").set(0)  # -- Add
            start_share.attr("outFloat").connect(total.attr("floatA"))
            twist.connect(total.attr("floatB"))
            twist = total.attr("outFloat")

        twist.connect(motion_path.attr("frontTwist"))

        compose = self._create_node("composeMatrix", "BendyTwistMatrix")
        motion_path.attr("allCoordinates").connect(compose.attr("inputTranslate"))
        motion_path.attr("rotate").connect(compose.attr("inputRotate"))
        motion_path.attr("rotateOrder").connect(compose.attr("inputRotateOrder"))
        org_scale.attr("outputScale").connect(compose.attr("inputScale"))

        # -- The joint's own parentInverseMatrix is not used, as reading it
        # -- back into its offsetParentMatrix does not evaluate reliably
        local = self._create_node("multMatrix", "BendyTwistLocal")
        compose.attr("outputMatrix").connect(local.attr("matrixIn[0]"))
        mref.get(f"{self.joint_parent}.worldInverseMatrix[0]").connect(local.attr("matrixIn[1]"))
        local.attr("matrixSum").connect(joint.attr("offsetParentMatrix"))

    def _apply_squash(self, joint: mref.ReferencedItem, percentage: float, stretch_ratio: str):
        """
        Drives the joint's y and z scale by the stretch ratio (which already
        carries the squashAndStretchAlpha), mapped by the scaleFalloff ramp
        sampled at the joint's percentage:

            scale = 1 + stretch_ratio * scaleFalloff(percentage)
        """
        # -- The whole ramp array is connected, so points the animator adds
        # -- to the ramp reach the remap too. This is done with cmds as
        # -- wrapping the multi compound ramp plug with mref crashes maya.
        falloff = self._create_node("remapValue", "BendyScaleFalloff")
        falloff.attr("inputValue").set(percentage)
        cmds.connectAttr(f"{self.controls[0].ctl}.scaleFalloff", f"{falloff.full_name()}.value")

        weighted = self._create_node("floatMath", "BendyScaleWeighted")
        weighted.attr("operation").set(2)  # -- Multiply
        mref.get(stretch_ratio).connect(weighted.attr("floatA"))
        falloff.attr("outValue").connect(weighted.attr("floatB"))

        scale = self._create_node("floatMath", "BendyScale")
        scale.attr("operation").set(0)  # -- Add
        weighted.attr("outFloat").connect(scale.attr("floatA"))
        scale.attr("floatB").set(1)

        for axis in ["Y", "Z"]:
            scale.attr("outFloat").connect(joint.attr(f"scale{axis}"))
