"""
Provides the MultiChainTwisters class, which drives a set of twist joints
along a chain of bendy, twisting and squashing curves (see bendy_twists for
the single segment version this follows).

The key joints are the start joint, the end joint and every joint between
them in the hierarchy. A curve runs between each pair of neighbouring key
joints (a segment), with the given number of cvs spread evenly along it. Each
cv is a cluster under a control:

    * Each key joint has a key control, which follows the key joint.
    * The cv controls at the ends of a segment sit under the key control at
      that end, so where two segments meet, a single key control is the
      parent of both of their cv controls.
    * The cv controls inside a segment have orgs point constrained between
      the segment's two key controls (keeping their percentage between them)
      and orient constrained to the first, so moving a key control bends
      the segments either side of it.

Each twist joint is given to the segment it lies closest to, and rides along
that segment's curve (spread by length) with its x axis along the tangent. It
takes its roll from the segment's start key joint and adds a twist blended
along the curve, from the roll of the segment's start key control to the roll
of its end key control, both measured relative to the start key joint around
the line between the key joints. These are zero at rest, so rolling the next
key joint (such as the wrist) or any key control twists the segment. If a
root twist node is given, the start of the first segment also holds that
node's roll, so the twist counters the start key joint rolling (such as an
upper leg rolling as its pole vector moves).

As a segment's curve grows longer the twist joints on it shrink in y and z
(and grow as it shortens). How much each joint scales is mapped through the
scaleFalloff ramp attribute on the segment's start key control, sampled at
the joint's percentage along the segment. The squashAndStretchAlpha
attribute on the same control blends the effect from none (0) to full (1).

The y and z scale of the cv controls is added on top of this. Each cv's scale
is spread over the twist joints of its segment, falling off linearly to the
neighbouring cvs, so a joint between two cvs blends their scales. The y and z
scale of the key controls is added too, each spread over both segments either
side of it, falling off linearly to the next key controls:

    scale = 1 + stretch_ratio * scaleFalloff(percentage)
              + sum(weight * (cv scale - 1))
              + (1 - percentage) * (start key scale - 1)
              + percentage * (end key scale - 1)

The structure built is:

    MultiChainTwisters (org)
        MultiChainKey 01 -> ## (controls, parent constrained to the key joints)
            MultiChainCv (the end cv controls of the adjoining segments)
                MultiChainCluster (cluster handle driving the matching cv)
        MultiChainCv (the inner cv controls of every segment)
            MultiChainCluster
        MultiChainNoTransform (does not inherit transforms)
            MultiChainCurve 01 -> ## (one per segment)
            MultiChainTwistDriver 01 -> ## (one per twist joint)

Each twist joint is constrained to its driver keeping its offset, so a build
leaves the joints where they are, and they return to their rest transforms
once the setup is deleted.
"""
import typing

from maya import cmds
from maya.api import OpenMaya as om

import mref
import aniseed_utilities as au

if typing.TYPE_CHECKING:
    import aniseed


class MultiChainTwisters:
    """
    Builds the multi chain twisters setup between two joints.

    Args:
        start_joint: The first key joint
        end_joint: The last key joint, which must be below the start joint
        twist_joints: The existing joints to drive along the curves
        cvs_per_segment: How many cvs each curve between two key joints has,
            including the cvs at the key joints themselves
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name
        location: The location token (config.left, config.middle etc)
        parent: Optional node to parent the setup's org under (the org is
            matched to it). If not given the org is created at the scene root.
        shape_scale: Optional scale for the control shapes. If not given it
            is derived from the length of the chain.
        root_twist_node: Optional node whose roll the start of the first
            segment holds (such as a limb's root control). If not given, the
            start key joint's roll is used, so rolling the start key joint
            rolls the whole first segment.

    Usage:
        setup = MultiChainTwisters(upper, wrist, twists, 4, config, "arm", config.left)
        setup.build()
    """

    # -- The default scaleFalloff ramp as (position, value, interpolation)
    # -- where an interpolation of 2 is smooth. This scales the middle of
    # -- each segment the most and leaves the ends alone.
    DEFAULT_FALLOFF = [(0.0, 0.0, 2), (0.5, 1.0, 2), (1.0, 0.0, 2)]

    def __init__(
            self,
            start_joint: mref.ReferencedItem,
            end_joint: mref.ReferencedItem,
            twist_joints: typing.List[str],
            cvs_per_segment: int = 4,
            config: "aniseed.RigConfiguration" = None,
            prefix: str = "",
            location: str = "",
            parent: str = None,
            shape_scale: float = None,
            root_twist_node: str = None,
    ):
        if cvs_per_segment < 2:
            raise ValueError("MultiChainTwisters needs at least two cvs per segment")

        if not twist_joints:
            raise ValueError("MultiChainTwisters needs at least one twist joint")

        self.key_joints = self._key_joints(mref.get(start_joint), mref.get(end_joint))
        self.twist_joint_names = [mref.get(joint).full_name() for joint in twist_joints]
        self.cvs_per_segment = cvs_per_segment
        self.root_twist_node = mref.get(root_twist_node).full_name() if root_twist_node else None
        self.config = config
        self.location = location
        self.parent = parent

        # -- "arm" becomes "Arm" so it reads as part of a camel cased description
        self.prefix = prefix[:1].upper() + prefix[1:]

        self.rest_lengths = [
            self._distance(self.key_joints[idx], self.key_joints[idx + 1])
            for idx in range(self.segment_count)
        ]

        # -- 1 if a segment's start key joint has its x axis pointing down
        # -- the segment, -1 if it points back up it (a behaviour mirrored chain)
        self.directions = []
        for idx in range(self.segment_count):
            x_axis = om.MVector(self.key_joints[idx].axis_vector("x", space="world"))
            self.directions.append(1 if x_axis * self._segment_vector(idx) >= 0 else -1)

        self.shape_scale = shape_scale or sum(self.rest_lengths) / (15.0 * self.segment_count)

        # -- Populated by build
        self.org: str = ""
        self.no_transform_org: str = ""
        self.curves: list[str] = []
        self.key_controls: list[au.rig.control.Control] = []
        self.cv_controls: list[list[au.rig.control.Control]] = []
        self.clusters: list[list[str]] = []
        self.twist_joints: list[str] = []

    def build(self) -> "MultiChainTwisters":
        """
        Creates the whole setup.

        Returns:
            This instance, so the created nodes can be read from it
        """
        for plugin in ["matrixNodes", "quatNodes", "lookdevKit"]:
            if not cmds.pluginInfo(plugin, query=True, loaded=True):
                cmds.loadPlugin(plugin, quiet=True)

        self._create_orgs()
        self._create_key_controls()

        for segment in range(self.segment_count):
            self._create_curve(segment)
            self._create_cv_controls(segment)
            self._create_squash_attributes(self.key_controls[segment].ctl)

        self._create_twist_joints()
        return self

    @property
    def segment_count(self) -> int:
        return len(self.key_joints) - 1

    @property
    def cv_percentages(self) -> list[float]:
        """
        Where each cv of a segment sits between its two key joints
        """
        return [idx / (self.cvs_per_segment - 1.0) for idx in range(self.cvs_per_segment)]

    @property
    def placements(self) -> list[typing.Tuple[int, float]]:
        """
        The segment and the percentage along it of each twist joint. Each
        joint is given to the segment it lies closest to, and keeps how far
        along that segment it already is. A joint on a key joint is as close
        to the segments either side of it, so it is given to the segment
        whose start key joint it is below (the deepest one, as each key
        joint is also below the ones before it).
        """
        tolerance = sum(self.rest_lengths) * 1e-4

        placements = []
        for joint in self.twist_joint_names:
            position = om.MVector(mref.get(joint).get_position(space="world"))
            long_name = cmds.ls(joint, long=True)[0]

            candidates = []
            for segment in range(self.segment_count):
                start = om.MVector(self.key_joints[segment].get_position(space="world"))
                vector = self._segment_vector(segment)
                percentage = min(max(((position - start) * vector) / (vector * vector), 0.0), 1.0)
                distance = (position - (start + vector * percentage)).length()

                start_name = cmds.ls(self.key_joints[segment].full_name(), long=True)[0]
                below_start = long_name.startswith(f"{start_name}|")
                candidates.append((distance, below_start, segment, percentage))

            # -- Only segments as close as the closest are considered. Of
            # -- those, the last one the joint is below wins, else the first.
            closest = min(candidate[0] for candidate in candidates)
            ties = [candidate for candidate in candidates if candidate[0] - closest <= tolerance]
            below = [candidate for candidate in ties if candidate[1]]
            placements.append(below[-1][2:] if below else ties[0][2:])

        return placements

    @staticmethod
    def _key_joints(start_joint: mref.ReferencedItem, end_joint: mref.ReferencedItem) -> list[mref.ReferencedItem]:
        """
        Returns the joints from the start joint down to the end joint
        """
        key_joints = [end_joint]
        while key_joints[-1].full_name() != start_joint.full_name():
            parent = key_joints[-1].parent()
            if not parent:
                raise ValueError(f"{end_joint.full_name()} is not below {start_joint.full_name()}")
            key_joints.append(parent)

        return list(reversed(key_joints))

    def _segment_vector(self, segment: int) -> om.MVector:
        """
        Returns the world vector from the segment's start key joint to its
        end key joint
        """
        return (
            om.MVector(self.key_joints[segment + 1].get_position(space="world")) -
            om.MVector(self.key_joints[segment].get_position(space="world"))
        )

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

    def _point_position(self, segment: int, percentage: float) -> list[float]:
        """
        Returns the world position the given percentage along the segment
        """
        start = om.MVector(self.key_joints[segment].get_position(space="world"))
        return list(start + self._segment_vector(segment) * percentage)

    def _create_orgs(self):
        """
        Creates the org which every part of the setup lives under, and the
        org which the curves live in. The curves are moved by clusters which
        work in world space, so their org must not inherit any transform.
        """
        self.org = au.scene.transforms.create(
            classification=self.config.organisational,
            description=self._description("MultiChainTwisters"),
            location=self.location,
            config=self.config,
            parent=self.parent,
            match_to=self.parent,
        )

        self.no_transform_org = au.scene.transforms.create(
            classification=self.config.organisational,
            description=self._description("MultiChainNoTransform"),
            location=self.location,
            config=self.config,
            parent=self.org,
        )
        mref.get(self.no_transform_org).attr("inheritsTransform").set(False)

    def _create_key_controls(self):
        """
        Creates a control at each key joint, which follows the key joint
        """
        for idx, joint in enumerate(self.key_joints):
            control = au.rig.control.create(
                description=self._description("MultiChainKey"),
                location=self.location,
                parent=self.org,
                shape="core_cube",
                config=self.config,
                match_to=joint.full_name(),
                shape_scale=self.shape_scale * 1.5,
                counter=idx + 1,
            )

            # -- The org was matched to the joint, so there is no offset
            mref.parentConstraint(joint.full_name(), control.org, maintainOffset=False)
            self.key_controls.append(control)

    def _create_curve(self, segment: int):
        """
        Creates the curve for the segment, with its cvs spread evenly between
        the segment's key joints
        """
        count = self.cvs_per_segment
        degree = min(3, count - 1)
        knots = [0] * degree + list(range(1, count - degree)) + [count - degree] * degree

        curve = cmds.curve(
            degree=degree,
            point=[self._point_position(segment, p) for p in self.cv_percentages],
            knot=knots,
            name=self._name(self.config.mechanical, "MultiChainCurve", segment + 1),
        )
        cmds.parent(curve, self.no_transform_org)

        # -- Show the curve as a reference so it can be seen but not picked
        curve = mref.get(curve)
        curve.attr("overrideEnabled").set(True)
        curve.attr("overrideDisplayType").set(2)
        self.curves.append(curve.full_name())

    def _create_cv_controls(self, segment: int):
        """
        Creates a control for each cv of the segment, with a cluster under it
        driving the cv. The end cv controls sit under the key control at that
        end. The inner cv controls' orgs are point constrained between the
        segment's two key controls, so they keep their percentage between
        them, and orient constrained to the first. Every cv control is
        oriented like the segment's start key joint.
        """
        start_key = self.key_controls[segment]
        end_key = self.key_controls[segment + 1]
        start_joint = self.key_joints[segment].full_name()

        controls = []
        clusters = []
        for idx, percentage in enumerate(self.cv_percentages):
            if idx == 0:
                parent = start_key.ctl
            elif idx == self.cvs_per_segment - 1:
                parent = end_key.ctl
            else:
                parent = self.org

            control = au.rig.control.create(
                description=self._description("MultiChainCv"),
                location=self.location,
                parent=parent,
                shape="core_sphere",
                config=self.config,
                match_to=start_joint,
                shape_scale=self.shape_scale,
                counter=segment * self.cvs_per_segment + idx + 1,
            )
            mref.get(control.org).set_position(self._point_position(segment, percentage), space="world")

            if parent == self.org:
                for target, weight in [(start_key, 1.0 - percentage), (end_key, percentage)]:
                    mref.pointConstraint(target.ctl, control.org, weight=weight, maintainOffset=False)

                # -- The org was matched to the start key joint, which the
                # -- start key control is matched to, so there is no offset
                mref.orientConstraint(start_key.ctl, control.org, maintainOffset=False)

            # -- Clusters are created from the selection, so select the cv
            counter = segment * self.cvs_per_segment + idx + 1
            cmds.select(f"{self.curves[segment]}.cv[{idx}]")
            cluster, handle = cmds.cluster(name=self._name(self.config.mechanical, "MultiChainCluster", counter))
            handle = mref.get(handle)
            handle.rename(self._name(self.config.mechanical, "MultiChainClusterHandle", counter))
            handle.set_parent(control.ctl)
            handle.attr("visibility").set(False)

            controls.append(control)
            clusters.append(handle.full_name())

        cmds.select(clear=True)
        self.cv_controls.append(controls)
        self.clusters.append(clusters)

    def _create_squash_attributes(self, ctl: str):
        """
        Adds the squashAndStretchAlpha attribute and the scaleFalloff ramp
        attribute to the given control
        """
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
        Drives each twist joint along its segment's curve
        """
        # -- The twist and stretch nodes are only made for segments which
        # -- have twist joints on them
        placements = self.placements
        segments = sorted({segment for segment, _ in placements})

        twists = {
            segment: (
                self._create_start_twist(segment),
                self._create_twist_reader(self.key_controls[segment + 1].ctl, segment, "MultiChainTwist"),
            )
            for segment in segments
        }

        # -- The twist joints take their scale from the org, so the whole
        # -- setup can be scaled
        org_scale = self._create_node("decomposeMatrix", "MultiChainOrgScale")
        mref.get(f"{self.org}.worldMatrix[0]").connect(org_scale.attr("inputMatrix"))

        stretch_ratios = {segment: self._create_stretch_ratio(segment, org_scale) for segment in segments}

        for joint, (segment, percentage) in zip(self.twist_joint_names, placements):
            joint = mref.get(joint)

            driver = mref.get(
                au.scene.transforms.create(
                    classification=self.config.mechanical,
                    description=self._description("MultiChainTwistDriver"),
                    location=self.location,
                    config=self.config,
                    parent=self.no_transform_org,
                ),
            )

            # -- The no transform org only has an identity world matrix when
            # -- the setup is at the origin, so the driver does not inherit
            # -- transforms either. Its own transform is cleared (it is created
            # -- keeping its world position, so it holds an offset), leaving its
            # -- world matrix as the curve's matrix it is given.
            driver.attr("inheritsTransform").set(False)
            cmds.xform(driver.full_name(), matrix=list(om.MMatrix()), objectSpace=True)

            self._attach_to_curve(driver, segment, percentage, *twists[segment], org_scale)
            self._apply_scale(driver, segment, percentage, stretch_ratios[segment])

            # -- The offset is kept, so a joint which sits off the curve, or
            # -- is oriented differently to it, is not moved by the build
            joint.attr("segmentScaleCompensate").set(False)
            mref.parentConstraint(driver.full_name(), joint.full_name(), maintainOffset=True)
            mref.scaleConstraint(driver.full_name(), joint.full_name(), maintainOffset=True)

            self.twist_joints.append(joint.full_name())

    def _create_start_twist(self, segment: int) -> str:
        """
        Returns the plug which outputs the twist at the start of the segment:
        the roll of its start key control, plus for the first segment the
        roll of the root twist node (if there is one). Both are measured
        relative to the start key joint, so with a root twist node the start
        of the curve holds the root twist node's roll however the start key
        joint rolls.
        """
        twist = self._create_twist_reader(self.key_controls[segment].ctl, segment, "MultiChainStartTwist")
        if segment or not self.root_twist_node:
            return twist

        root_twist = self._create_twist_reader(self.root_twist_node, segment, "MultiChainRootTwist")

        total = self._create_node("floatMath", "MultiChainStartTwistTotal")
        total.attr("operation").set(0)  # -- Add
        mref.get(twist).connect(total.attr("floatA"))
        mref.get(root_twist).connect(total.attr("floatB"))
        return f"{total.full_name()}.outFloat"

    def _twist_frame(self, segment: int) -> om.MMatrix:
        """
        Returns the rest frame the segment's twist is measured in. Its x axis
        runs from the segment's start key joint to its end key joint and its
        y axis is the start key joint's y axis (or z axis if the y axis runs
        along the segment).
        """
        start_joint = self.key_joints[segment]
        x_axis = self._segment_vector(segment).normal()

        up_axis = om.MVector(start_joint.axis_vector("y", space="world"))
        if abs(up_axis.normal() * x_axis) > 0.99:
            up_axis = om.MVector(start_joint.axis_vector("z", space="world"))

        z_axis = (x_axis ^ up_axis).normal()
        y_axis = (z_axis ^ x_axis).normal()
        position = start_joint.get_position(space="world")

        return om.MMatrix([
            list(x_axis) + [0],
            list(y_axis) + [0],
            list(z_axis) + [0],
            list(position) + [1],
        ])

    def _create_twist_reader(self, node: str, segment: int, label: str) -> str:
        """
        Creates the nodes which read the twist of the given node relative to
        the segment's start key joint, around the line between its key
        joints, and returns the plug which outputs it. It reads zero at rest.

            relative = (frame in node space) * node.worldMatrix
                       * start.worldInverseMatrix * (frame in start space)^-1

        The twist is taken from the relative rotation by swing/twist
        decomposition: zeroing the y and z of its quaternion leaves the
        rotation around x.
        """
        node = mref.get(node)
        start_joint = self.key_joints[segment]

        frame = self._twist_frame(segment)
        frame_in_node = frame * self._world_matrix(node).inverse()
        frame_in_start_inverse = self._world_matrix(start_joint) * frame.inverse()

        relative = self._create_node("multMatrix", f"{label}Relative")
        relative.attr("matrixIn[0]").set(list(frame_in_node), type="matrix")
        mref.get(f"{node.full_name()}.worldMatrix[0]").connect(relative.attr("matrixIn[1]"))
        mref.get(f"{start_joint.full_name()}.worldInverseMatrix[0]").connect(relative.attr("matrixIn[2]"))
        relative.attr("matrixIn[3]").set(list(frame_in_start_inverse), type="matrix")

        decompose = self._create_node("decomposeMatrix", f"{label}Decompose")
        relative.attr("matrixSum").connect(decompose.attr("inputMatrix"))

        normalize = self._create_node("quatNormalize", f"{label}Quat")
        decompose.attr("outputQuatX").connect(normalize.attr("inputQuatX"))
        decompose.attr("outputQuatW").connect(normalize.attr("inputQuatW"))

        to_euler = self._create_node("quatToEuler", f"{label}Euler")
        normalize.attr("outputQuat").connect(to_euler.attr("inputQuat"))

        return f"{to_euler.full_name()}.outputRotateX"

    def _create_stretch_ratio(self, segment: int, org_scale: mref.ReferencedItem) -> str:
        """
        Creates the nodes which output how far the segment's curve has
        stretched beyond its rest length, as
        ((rest length / length) - 1) * squashAndStretchAlpha. It is zero at
        rest (or with an alpha of zero) and positive as the curve shortens.
        The curve's world length is compared to the rest length scaled by the
        org, so scaling the org does not read as a stretch.
        """
        info = self._create_node("curveInfo", "MultiChainCurveInfo")
        mref.get(f"{self.curves[segment]}.worldSpace[0]").connect(info.attr("inputCurve"))

        rest = self._create_node("floatMath", "MultiChainRestLength")
        rest.attr("operation").set(2)  # -- Multiply
        rest.attr("floatA").set(self.rest_lengths[segment] / self._org_scale())
        org_scale.attr("outputScaleX").connect(rest.attr("floatB"))

        ratio = self._create_node("floatMath", "MultiChainStretchRatio")
        ratio.attr("operation").set(3)  # -- Divide
        rest.attr("outFloat").connect(ratio.attr("floatA"))
        info.attr("arcLength").connect(ratio.attr("floatB"))

        offset = self._create_node("floatMath", "MultiChainStretchOffset")
        offset.attr("operation").set(1)  # -- Subtract
        ratio.attr("outFloat").connect(offset.attr("floatA"))
        offset.attr("floatB").set(1)

        alpha = self._create_node("floatMath", "MultiChainStretchAlpha")
        alpha.attr("operation").set(2)  # -- Multiply
        offset.attr("outFloat").connect(alpha.attr("floatA"))
        mref.get(f"{self.key_controls[segment].ctl}.squashAndStretchAlpha").connect(alpha.attr("floatB"))

        return f"{alpha.full_name()}.outFloat"

    def _org_scale(self) -> float:
        """
        Returns the world scale of the org, as the rest lengths are stored in
        its space
        """
        return om.MTransformationMatrix(om.MMatrix(cmds.getAttr(f"{self.org}.worldMatrix[0]"))).scale(om.MSpace.kWorld)[0]

    def _attach_to_curve(
            self,
            driver: mref.ReferencedItem,
            segment: int,
            percentage: float,
            start_twist: str,
            end_twist: str,
            org_scale: mref.ReferencedItem,
    ):
        """
        Places the driver along the segment's curve (by length) through its
        offsetParentMatrix, with its x axis along the tangent, its roll taken
        from the segment's start key joint plus the twists blended by its
        percentage:

            twist = start_twist * (1 - percentage) + end_twist * percentage

        On a mirrored chain the front axis is inverted, so x points back up
        the curve, and as the motion path's front twist is around that
        inverted axis the twist is negated.
        """
        start_joint = self.key_joints[segment]
        direction = self.directions[segment]

        motion_path = self._create_node("motionPath", "MultiChainTwistPath")
        mref.get(f"{self.curves[segment]}.worldSpace[0]").connect(motion_path.attr("geometryPath"))
        motion_path.attr("fractionMode").set(True)
        motion_path.attr("follow").set(True)
        motion_path.attr("frontAxis").set(0)  # -- X
        motion_path.attr("inverseFront").set(direction < 0)
        motion_path.attr("upAxis").set(1)  # -- Y
        motion_path.attr("worldUpType").set(2)  # -- Object rotation up

        # -- uValue is a doubleLinear attribute, so setAttr would read the
        # -- fraction in the scene's linear unit. The plug takes the internal
        # -- value, which is the fraction itself.
        om.MSelectionList().add(f"{motion_path.full_name()}.uValue").getPlug(0).setDouble(percentage)

        # -- The up vector is the twist frame's y axis, held by the start key joint
        up_vector = om.MVector(list(self._twist_frame(segment))[4:7]) * self._world_matrix(start_joint).inverse()
        motion_path.attr("worldUpVector").set(*up_vector)
        mref.get(f"{start_joint.full_name()}.worldMatrix[0]").connect(motion_path.attr("worldUpMatrix"))

        start_share = self._create_node("floatMath", "MultiChainStartTwistShare")
        start_share.attr("operation").set(2)  # -- Multiply
        mref.get(start_twist).connect(start_share.attr("floatA"))
        start_share.attr("floatB").set((1.0 - percentage) * direction)

        end_share = self._create_node("floatMath", "MultiChainTwistShare")
        end_share.attr("operation").set(2)  # -- Multiply
        mref.get(end_twist).connect(end_share.attr("floatA"))
        end_share.attr("floatB").set(percentage * direction)

        total = self._create_node("floatMath", "MultiChainTwistTotal")
        total.attr("operation").set(0)  # -- Add
        start_share.attr("outFloat").connect(total.attr("floatA"))
        end_share.attr("outFloat").connect(total.attr("floatB"))
        total.attr("outFloat").connect(motion_path.attr("frontTwist"))

        compose = self._create_node("composeMatrix", "MultiChainTwistMatrix")
        motion_path.attr("allCoordinates").connect(compose.attr("inputTranslate"))
        motion_path.attr("rotate").connect(compose.attr("inputRotate"))
        motion_path.attr("rotateOrder").connect(compose.attr("inputRotateOrder"))
        org_scale.attr("outputScale").connect(compose.attr("inputScale"))
        compose.attr("outputMatrix").connect(driver.attr("offsetParentMatrix"))

    def _apply_scale(self, driver: mref.ReferencedItem, segment: int, percentage: float, stretch_ratio: str):
        """
        Drives the driver's y and z scale by the stretch ratio (which already
        carries the squashAndStretchAlpha) mapped by the segment's
        scaleFalloff ramp, plus the y and z scale of the segment's cv
        controls weighted by how close the driver is to each, plus the y and
        z scale of the segment's two key controls blended by its percentage:

            scale = 1 + stretch_ratio * scaleFalloff(percentage)
                      + sum(weight * (cv scale - 1))
                      + (1 - percentage) * (start key scale - 1)
                      + percentage * (end key scale - 1)

        The cv weights fall off linearly to the neighbouring cvs, so they sum
        to one, as do the key weights, and this is
        stretch_ratio * scaleFalloff(percentage) + sum(weight * cv scale)
        + (1 - percentage) * start key scale + percentage * end key scale - 1.
        """
        # -- The whole ramp array is connected, so points the animator adds
        # -- to the ramp reach the remap too. This is done with cmds as
        # -- wrapping the multi compound ramp plug with mref crashes maya.
        falloff = self._create_node("remapValue", "MultiChainScaleFalloff")
        falloff.attr("inputValue").set(percentage)
        cmds.connectAttr(f"{self.key_controls[segment].ctl}.scaleFalloff", f"{falloff.full_name()}.value")

        weighted = self._create_node("floatMath", "MultiChainScaleWeighted")
        weighted.attr("operation").set(2)  # -- Multiply
        mref.get(stretch_ratio).connect(weighted.attr("floatA"))
        falloff.attr("outValue").connect(weighted.attr("floatB"))

        # -- input3D[0] carries the stretch term, input3D[1] the minus one of
        # -- the key control term, and the weighted scales follow
        total = self._create_node("plusMinusAverage", "MultiChainScale")
        total.attr("operation").set(1)  # -- Sum
        for axis in ["y", "z"]:
            weighted.attr("outFloat").connect(total.attr(f"input3D[0].input3D{axis}"))
        total.attr("input3D[1]").set(-1, -1, -1)

        spacing = self.cvs_per_segment - 1.0
        weights = [
            (control.ctl, max(0.0, 1.0 - abs(percentage - cv_percentage) * spacing), "MultiChainCvScale")
            for control, cv_percentage in zip(self.cv_controls[segment], self.cv_percentages)
        ]
        weights += [
            (self.key_controls[segment].ctl, 1.0 - percentage, "MultiChainKeyScale"),
            (self.key_controls[segment + 1].ctl, percentage, "MultiChainKeyScale"),
        ]

        index = 2
        for ctl, weight, label in weights:
            if weight <= 0:
                continue

            scale = self._create_node("multiplyDivide", label)
            mref.get(f"{ctl}.scale").connect(scale.attr("input1"))
            scale.attr("input2").set(weight, weight, weight)
            scale.attr("output").connect(total.attr(f"input3D[{index}]"))
            index += 1

        for axis in ["Y", "Z"]:
            total.attr(f"output3D.output3D{axis.lower()}").connect(driver.attr(f"scale{axis}"))


def create_twist_joints(
        start_joint: str,
        end_joint: str,
        count: int,
        config: "aniseed.RigConfiguration",
        prefix: str,
        location: str,
) -> typing.List[str]:
    """
    Creates twist joints along every segment between the start and end
    joint, under each segment's start key joint and oriented to it. These can
    be given to MultiChainTwisters as its twist_joints, so the joints live in
    the skeleton (and can be skinned) rather than being created by each build.

    The joints are spread evenly along each segment from its start to its
    end key joint (a single joint sits in the middle), as typically only the
    twist joints are skinned to. Where two segments meet there is a joint
    from each, and each is driven by its own segment as it is below that
    segment's start key joint.

    Args:
        start_joint: The first key joint
        end_joint: The last key joint, which must be below the start joint
        count: How many twist joints to create in each segment
        config: The aniseed rig configuration used to name the joints
        prefix: Placed in front of the description of the joint names
        location: The location token (config.left, config.middle etc)

    Returns:
        The created joints, ordered from the start joint to the end joint
    """
    key_joints = MultiChainTwisters._key_joints(mref.get(start_joint), mref.get(end_joint))
    percentages = [0.5] if count == 1 else [idx / (count - 1.0) for idx in range(count)]

    joints = []
    for start_key, end_key in zip(key_joints, key_joints[1:]):
        start = om.MVector(start_key.get_position(space="world"))
        end = om.MVector(end_key.get_position(space="world"))

        for percentage in percentages:
            joint = au.scene.joints.create(
                description=f"{prefix[:1].upper()}{prefix[1:]}MultiChainTwist",
                location=location,
                parent=start_key.full_name(),
                config=config,
                match_to=start_key.full_name(),
            )
            mref.get(joint).set_position(list(start + (end - start) * percentage), space="world")
            joints.append(joint)

    au.scene.joints.move_rotations_to_orients(joints)
    cmds.select(clear=True)
    return joints
