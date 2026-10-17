"""
Aligning a joint chain for ik: re-orients every joint in a chain to face down a
given axis with a given pole vector axis, handling pins, child transforms and
twist joints.
"""
import maya.cmds as mc

from ..core import maths as _maths
from ..scene import joints as _joints
from ..scene import transforms as _transforms
from ..rig import pinning as _pinning


AXIS = ["x", "y", "z"]
AXIS_LABELS = [
    "positive x",
    "negative x",
    "positive y",
    "negative y",
    "positive z",
    "negative z",
]


def align_bones_for_ik(
        root: str,
        tip: str,
        primary_axis: str,
        polevector_axis: str,
        retain_child_transforms: bool,
) -> None:
    """
    This will align the bones down the chain based on a specific facing axis and
    a specific up axis. All joints including the end joint will be aligned (the
    end joint taking its vector from the projection of the joint before it).

    Any joints in the chain which are pinned are unpinned during the alignment
    and pinned again afterwards. Children named with "twist" are re-positioned
    to the same relative position along their bone and have their rotations
    zeroed.

    Args:
        root: The joint to start aligning from
        tip: The end joint - only joints between these two will be affected
        primary_axis: The axis to align to ('Positive X', 'Negative Y', etc)
        polevector_axis: The axis to align to (same format as primary_axis)
        retain_child_transforms: Whether to keep (in worldspace) the same transform
            for any children that are not part of the chain

    Returns:
        None
    """
    # -- Now we have all the data we need, remove any pins
    pinned_joints = list()

    all_joints_in_chain = _joints.get_between(start=root, end=tip)

    for joint in all_joints_in_chain:
        if _pinning.is_pinned(joint):
            pinned_joints.append(joint)
            _pinning.remove_pins([joint])

    try:
        joint_parent = mc.listRelatives(root, parent=True)[0]
    except (TypeError, IndexError):
        joint_parent = None

    aim_axis = get_aim_dir(primary_axis)
    upvector_axis = get_aim_dir(polevector_axis)
    inverted_upvector_axis = get_inverted_aim_dir(polevector_axis)

    actual_chain = _joints.get_between(
        root,
        tip,
    )
    _joints.move_orients_to_rotation(
        actual_chain,
    )

    # -- Store any child transforms
    child_transforms = dict()
    twist_factors = dict()

    for idx, joint in enumerate(actual_chain):
        for child in mc.listRelatives(joint, children=True) or list():
            if child in actual_chain:
                continue

            child_transforms[child] = mc.xform(
                child,
                query=True,
                matrix=True,
                worldSpace=True,
            )

            if "Twist" in child and idx < len(actual_chain):
                twist_factors[child] = _maths.factor_between(
                    node=child,
                    from_this=joint,
                    to_this=actual_chain[idx + 1],
                    print_result=True,
                )

    replicated_joints = _joints.replicate_chain(
        from_this=root,
        to_this=tip,
        parent=None,
    )
    _joints.move_orients_to_rotation(
        replicated_joints
    )

    for idx, joint in enumerate(replicated_joints):
        try:
            mc.parent(
                joint,
                world=True,
            )

        except RuntimeError:
            pass

        _joints.move_orients_to_rotation(
            [joint],
        )

    for idx, joint in enumerate(replicated_joints[:-1]):

        # -- special case for the first one
        if idx == 0:
            cns = mc.aimConstraint(
                replicated_joints[idx + 1],
                joint,
                worldUpType="object",
                worldUpObject=replicated_joints[-1],
                aimVector=aim_axis,
                upVector=inverted_upvector_axis,
                maintainOffset=False,
            )
            mc.delete(cns)
            continue

        cns = mc.aimConstraint(
            replicated_joints[idx + 1],
            joint,
            worldUpType="object",
            worldUpObject=replicated_joints[idx - 1],
            aimVector=aim_axis,
            upVector=inverted_upvector_axis,
            maintainOffset=False,
        )
        mc.delete(cns)

    # -- Re parent the joints before copying the data
    for idx, joint in enumerate(replicated_joints):

        if idx == 0:
            if joint_parent:
                mc.parent(
                    joint,
                    joint_parent
                )
            continue

        mc.parent(
            joint,
            replicated_joints[idx - 1],
        )

    _joints.move_orients_to_rotation(
        replicated_joints,
    )

    # -- Zero the last joints rotation
    for axis in AXIS:
        mc.setAttr(
            f"{replicated_joints[-1]}.rotate{axis.upper()}",
            0,
        )

    for idx in range(len(actual_chain)):
        _joints.copy_attributes(
            from_this=replicated_joints[idx],
            to_this=actual_chain[idx],
        )

    if retain_child_transforms:
        for child, matrix in child_transforms.items():
            mc.xform(
                child,
                matrix=child_transforms[child],
                worldSpace=True,
            )

    # -- Deal with twist joints
    for idx, joint in enumerate(actual_chain):

        for child in mc.listRelatives(joint, children=True) or list():

            if child in actual_chain:
                continue

            # -- Skip anything that is not a twist
            if "twist" not in child.lower():
                continue

            # -- If we dont have an additional joint to aim down, skip it
            if idx >= len(actual_chain):
                continue

            # -- Position the node
            _transforms.position_between(
                child,
                actual_chain[idx],
                actual_chain[idx + 1],
                twist_factors[child],
            )

            for axis in AXIS:
                mc.setAttr(f"{child}.r{axis.lower()}", 0)
                mc.setAttr(f"{child}.jointOrient{axis.upper()}", 0)


    mc.delete(replicated_joints)

    # -- Restore the pins which were removed
    if pinned_joints:
        _pinning.pin(pinned_joints)


def get_aim_dir(aim_label: str) -> list[int]:
    """
    Converts an axis label (such as "positive x" or "Negative Z") into a
    direction vector.

    Args:
        aim_label: The axis label, see AXIS_LABELS

    Returns:
        The direction as a list of three values
    """
    aim_label = aim_label.lower()
    aim_dir = [0, 0, 0]

    # for idx in range(values):
    index = AXIS.index(aim_label[-1])
    aim_dir[index] = 1 * -1 if "negative" in aim_label else 1

    return aim_dir


def get_inverted_aim_dir(aim_label: str) -> list[int]:
    """
    Returns the inverse of the direction vector for the given axis label
    (see get_aim_dir).

    Args:
        aim_label: The axis label, see AXIS_LABELS

    Returns:
        The inverted direction as a list of three values
    """
    return [
        v * -1
        for v in get_aim_dir(aim_label)
    ]
