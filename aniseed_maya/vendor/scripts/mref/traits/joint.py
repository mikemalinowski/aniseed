import math

import mref
from maya import cmds
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as oma


# -- Index of each axis name within a matrix row/column
_AXIS_INDICES = {"x": 0, "y": 1, "z": 2}


class Joint(mref.Trait):
    """
    Trait bound to any node with ``MFn.kJoint`` — skeleton joints.
    Exposes the joint-specific channels (joint orient, preferred angle,
    segment scale compensate, radius), joint-only hierarchy traversal
    (:meth:`parent_joint`, :meth:`child_joints`, :meth:`chain_to`) and
    the common rigging orientation operations (:meth:`orient_to_child`,
    :meth:`orient_to_world`, :meth:`freeze_rotation`).

    All angles are in degrees.
    """

    # -- Sits above the generic Transform trait
    priority = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._joint = oma.MFnIkJoint(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kJoint)

    def joint_orient(self) -> list[float]:
        """
        Returns the joint orient as ``[x, y, z]`` Euler angles in degrees.
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.jointOrient")[0])

    def set_joint_orient(self, orient: list[float]) -> None:
        """
        Sets the joint orient from ``[x, y, z]`` Euler angles in degrees.
        Note that this changes the world orientation of the joint (and
        so moves its children) — use :meth:`orient_to_child` or
        :meth:`freeze_rotation` to re-orient without moving anything.
        """
        cmds.setAttr(f"{self.item.full_name()}.jointOrient", *orient)

    def preferred_angle(self) -> list[float]:
        """
        Returns the preferred angle as ``[x, y, z]`` in degrees. This is
        the bend direction hint used by IK solvers.
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.preferredAngle")[0])

    def set_preferred_angle(self, angle: list[float] = None) -> None:
        """
        Sets the preferred angle from ``[x, y, z]`` in degrees. If no angle
        is given, the joint's current rotation is stored as its preferred
        angle (equivalent to "Set Preferred Angle" in the Maya UI).
        """
        if angle is None:
            angle = cmds.getAttr(f"{self.item.full_name()}.rotate")[0]
        cmds.setAttr(f"{self.item.full_name()}.preferredAngle", *angle)

    def segment_scale_compensate(self) -> bool:
        """
        Returns True if segment scale compensate is enabled — i.e. this
        joint does not inherit the scale of its parent joint.
        """
        return bool(cmds.getAttr(f"{self.item.full_name()}.segmentScaleCompensate"))

    def set_segment_scale_compensate(self, state: bool) -> None:
        """
        Enables or disables segment scale compensate on this joint.
        """
        cmds.setAttr(f"{self.item.full_name()}.segmentScaleCompensate", bool(state))

    def radius(self) -> float:
        """
        Returns the display radius of the joint.
        """
        return cmds.getAttr(f"{self.item.full_name()}.radius")

    def set_radius(self, radius: float) -> None:
        """
        Sets the display radius of the joint.
        """
        cmds.setAttr(f"{self.item.full_name()}.radius", radius)

    def parent_joint(self) -> mref.ReferencedItem|None:
        """
        Returns the parent of this joint if (and only if) that parent is
        itself a joint, otherwise None. Use ``parent()`` for the plain
        DAG parent.
        """
        parent = self.item.parent()
        if parent and parent.pointer().hasFn(om.MFn.kJoint):
            return parent
        return None

    def child_joints(self, recursive: bool = False) -> mref.ReferenceList:
        """
        Returns the joints parented directly under this joint. If
        ``recursive`` is True, every descendant joint is returned instead
        (depth-first, parents before children).
        """
        results = mref.ReferenceList()
        for index in range(self._joint.childCount()):
            child = self._joint.child(index)
            if not child.hasFn(om.MFn.kJoint):
                continue
            child_item = mref.get(child)
            results.append(child_item)
            if recursive:
                results.extend(child_item.child_joints(recursive=True))
        return results

    def chain_to(self, end_joint: mref.ReferencedItem|str) -> mref.ReferenceList:
        """
        Returns the joint chain from this joint down to ``end_joint``,
        inclusive of both ends, ordered root to tip. Raises ``ValueError``
        if ``end_joint`` is not this joint or one of its descendant joints
        (connected through joints only).
        """
        end_joint = mref.get(end_joint)
        if not end_joint.pointer().hasFn(om.MFn.kJoint):
            raise ValueError(f"{end_joint.full_name()} is not a joint")

        chain = [end_joint]
        current = end_joint
        while current != self.item:
            current = current.parent_joint()
            if current is None:
                raise ValueError(
                    f"{end_joint.full_name()} is not a descendant joint "
                    f"of {self.item.full_name()}"
                )
            chain.append(current)

        return mref.ReferenceList(reversed(chain))

    def orient_to_child(
        self,
        child: mref.ReferencedItem|str = None,
        aim_axis: str = "x",
        up_axis: str = "y",
        world_up: list[float] = (0.0, 1.0, 0.0),
    ) -> None:
        """
        Orients this joint so that ``aim_axis`` points at ``child`` (the
        first child joint if not given) and ``up_axis`` points as closely
        as possible toward the ``world_up`` vector.

        Axes are given as ``"x"``, ``"y"``, ``"z"``, optionally prefixed
        with ``"-"`` (e.g. ``aim_axis="-x"`` for mirrored chains). The new
        orientation is stored entirely in ``jointOrient`` — ``rotate`` and
        ``rotateAxis`` are zeroed — and all children stay where they are
        in world space.
        """
        if child is None:
            child_joints = self.child_joints()
            if not child_joints:
                raise ValueError(
                    f"{self.item.full_name()} has no child joint to orient towards"
                )
            child = child_joints[0]
        child = mref.get(child)

        aim_sign, aim_index = _parse_axis(aim_axis)
        up_sign, up_index = _parse_axis(up_axis)
        if aim_index == up_index:
            raise ValueError("aim_axis and up_axis must be different axes")

        start = _world_translation(self._pointer)
        end = _world_translation(child.pointer())

        aim = end - start
        if aim.length() < 1e-8:
            raise ValueError(
                f"{child.full_name()} is coincident with {self.item.full_name()}; "
                f"cannot determine an aim direction"
            )
        aim.normalize()

        up = om.MVector(*world_up)
        side = aim ^ up
        if side.length() < 1e-8:
            raise ValueError("world_up is parallel to the aim direction")
        up = (side ^ aim).normal()

        rows = [None, None, None]
        rows[aim_index] = aim * aim_sign
        rows[up_index] = up * up_sign

        # -- The remaining axis is derived so the matrix stays right handed:
        # -- x ^ y = z, y ^ z = x, z ^ x = y.
        third_index = 3 - aim_index - up_index
        if (aim_index + 1) % 3 == up_index:
            rows[third_index] = rows[aim_index] ^ rows[up_index]
        else:
            rows[third_index] = rows[up_index] ^ rows[aim_index]

        self._apply_world_orientation(_rows_to_matrix(rows))

    def orient_to_world(self) -> None:
        """
        Orients this joint so its local axes align with the world axes,
        storing the result in ``jointOrient`` (``rotate`` and ``rotateAxis``
        are zeroed). Children stay where they are in world space. This is
        the typical treatment for end joints.
        """
        self._apply_world_orientation(om.MMatrix())

    def freeze_rotation(self) -> None:
        """
        Bakes the current ``rotate`` and ``rotateAxis`` values into
        ``jointOrient`` and zeroes them, without changing the joint's
        orientation or moving any children. Equivalent to freezing
        rotation on a single joint.
        """
        name = self.item.full_name()

        rotate_order = cmds.getAttr(f"{name}.rotateOrder")
        rotate = om.MEulerRotation(
            [math.radians(v) for v in cmds.getAttr(f"{name}.rotate")[0]],
            rotate_order,
        )
        rotate_axis = om.MEulerRotation(
            [math.radians(v) for v in cmds.getAttr(f"{name}.rotateAxis")[0]],
        )
        orient = om.MEulerRotation(
            [math.radians(v) for v in cmds.getAttr(f"{name}.jointOrient")[0]],
        )

        # -- Joint local rotation is rotateAxis * rotate * jointOrient
        combined = rotate_axis.asMatrix() * rotate.asMatrix() * orient.asMatrix()
        self._set_orientation_matrix(combined)

    def _apply_world_orientation(self, world_rotation: om.MMatrix) -> None:
        """
        Sets this joint's world orientation to the given rotation matrix by
        writing ``jointOrient`` (zeroing rotate / rotateAxis). Children are
        temporarily unparented so they keep their world transforms.
        """
        # -- Gather all non-shape DAG children so we can lift them out
        # -- while the joint rotates.
        children = []
        for index in range(self._joint.childCount()):
            child = self._joint.child(index)
            if child.hasFn(om.MFn.kTransform):
                children.append(mref.get(child))

        for child in children:
            cmds.parent(child.full_name(), world=True)

        parent_matrix = om.MDagPath.getAPathTo(self._pointer).exclusiveMatrix()
        local = world_rotation * _normalised_rotation(parent_matrix).inverse()
        self._set_orientation_matrix(local)

        for child in children:
            cmds.parent(child.full_name(), self.item.full_name())

    def _set_orientation_matrix(self, matrix: om.MMatrix) -> None:
        """
        Writes the rotation part of the given matrix into ``jointOrient``
        and zeroes ``rotate`` and ``rotateAxis``.
        """
        name = self.item.full_name()
        euler = om.MTransformationMatrix(_normalised_rotation(matrix)).rotation()

        cmds.setAttr(f"{name}.rotate", 0, 0, 0)
        cmds.setAttr(f"{name}.rotateAxis", 0, 0, 0)
        cmds.setAttr(
            f"{name}.jointOrient",
            math.degrees(euler.x),
            math.degrees(euler.y),
            math.degrees(euler.z),
        )


def _parse_axis(axis: str) -> tuple[float, int]:
    """
    Parses an axis string such as ``"x"`` or ``"-z"`` into a
    ``(sign, index)`` tuple.
    """
    text = axis.lower().strip()
    sign = 1.0
    if text.startswith("-"):
        sign = -1.0
        text = text[1:]
    elif text.startswith("+"):
        text = text[1:]

    if text not in _AXIS_INDICES:
        raise ValueError(f"Unknown axis {axis!r}; expected x, y or z (optionally signed)")
    return sign, _AXIS_INDICES[text]


def _world_translation(pointer: om.MObject) -> om.MVector:
    """
    Returns the world space translation of the given DAG node.
    """
    matrix = om.MDagPath.getAPathTo(pointer).inclusiveMatrix()
    return om.MVector(matrix[12], matrix[13], matrix[14])


def _rows_to_matrix(rows: list[om.MVector]) -> om.MMatrix:
    """
    Builds a rotation matrix from three axis vectors (Maya row-vector
    convention, so each vector becomes a matrix row).
    """
    return om.MMatrix([
        rows[0].x, rows[0].y, rows[0].z, 0.0,
        rows[1].x, rows[1].y, rows[1].z, 0.0,
        rows[2].x, rows[2].y, rows[2].z, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ])


def _normalised_rotation(matrix: om.MMatrix) -> om.MMatrix:
    """
    Returns the rotation part of the given matrix with scale removed and
    translation zeroed.
    """
    rows = [
        om.MVector(matrix[r * 4], matrix[r * 4 + 1], matrix[r * 4 + 2]).normal()
        for r in range(3)
    ]
    return _rows_to_matrix(rows)
