"""
Building blocks for ik chains. These are used by the two bone ikfk setup
as well as the limb components which build their own ik arrangements.
"""
import typing

import mref

from ..scene import joints as _joints


def create_ik_chain(
        from_joint: str,
        to_joint: str,
        parent: str,
        name: typing.Callable[[str], str] = None,
        root_ignores_parent: bool = False,
        move_rotations_to_orients: bool = True,
) -> list[str]:
    """
    Replicates the joint chain between the two given joints, ready to have
    an ik solver applied to it. All rotation values are moved onto the
    joint orients so that the ik solve starts from a zero rotation.

    Args:
        from_joint: The first joint of the chain to replicate
        to_joint: The last joint of the chain to replicate
        parent: The node to parent the replicated chain under
        name: Optional callable which is given the joint and returns the
            name to rename it to
        root_ignores_parent: If True the root joint will not inherit the
            transform of its parent (whilst retaining its world matrix)
        move_rotations_to_orients: If False the rotations are left in place,
            which is useful if the chain needs altering first

    Returns:
        The list of replicated joints
    """
    chain = _joints.replicate_chain(
        from_this=from_joint,
        to_this=to_joint,
        parent=parent,
    )

    if root_ignores_parent:
        root = mref.get(chain[0])
        matrix = root.get_matrix(space="world")
        root.attr("inheritsTransform").set(0)
        root.set_matrix(matrix, space="world")

    if name:
        renamed = []
        for joint in chain:
            joint = mref.get(joint)
            joint.rename(name(joint.name()))
            renamed.append(joint.name())
        chain = renamed

    if move_rotations_to_orients:
        _joints.move_rotations_to_orients(chain)

    return chain


def create_rp_handle(
        start_joint: str,
        end_joint: str,
        parent: str = None,
        pole_vector: str = None,
        hide: bool = True,
        parent_before_pole_vector: bool = True,
) -> mref.ReferencedItem:
    """
    Creates a rotate plane ik handle between the two joints.

    Args:
        start_joint: The joint the solve starts from
        end_joint: The joint the solve ends at
        parent: Optional node to parent the ik handle under
        pole_vector: Optional node to pole vector constrain the handle to
        hide: Whether to hide the handle
        parent_before_pole_vector: The pole vector constraint stores a rest
            position which is calculated in the space of the handle's parent
            at the time it is applied, so this defines whether the handle
            is parented before or after the constraint is applied.

    Returns:
        The ik handle
    """
    handle = mref.get(
        mref.ikHandle(
            startJoint=start_joint,
            endEffector=end_joint,
            solver="ikRPsolver",
            priority=1,
        )[0]
    )

    if hide:
        handle.attr("visibility").set(False)

    if parent and parent_before_pole_vector:
        handle.set_parent(parent)

    if pole_vector:
        mref.poleVectorConstraint(
            pole_vector,
            handle,
            weight=1,
        )

    if parent and not parent_before_pole_vector:
        handle.set_parent(parent)

    return handle
