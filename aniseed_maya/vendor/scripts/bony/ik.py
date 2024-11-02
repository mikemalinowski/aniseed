import qute
import maya.cmds as mc

from . import pins
from . import orients
from . import hierarchy
from . import math
from . import transform
from . import utils
from . import constants as c


# --------------------------------------------------------------------------------------
def clean_ik_plane_with_ui():

    pre_selection = mc.ls(sl=True)
    try:
        root = mc.ls(sl=True)[0]
        tip = mc.ls(sl=True)[1]

    except IndexError:
        print("You must select two objects")
        return

    # -- We allow this tool to operate on joints or pins, so make sure we're
    # -- working with joints
    root = pins.get_joint(root)
    tip = pins.get_joint(tip)

    all_joints_in_chain = hierarchy.get_between(root, tip)
    pinned_joints = list()

    for joint in all_joints_in_chain:
        if pins.is_pinned(joint):
            pinned_joints.append(joint)
            pins.remove([joint])

    forward_axis = qute.utilities.request.item(
        title="Forward Axis",
        label="Please select which axis is running along the bone",
        items=c.AXIS_LABELS,
        editable=False,
    )

    if not forward_axis:
        return

    forward_channel = forward_axis[-1]

    possible_vector_channels = [
        possibility
        for possibility in c.AXIS_LABELS
        if not possibility.endswith(forward_channel)
    ]

    polevector_axis = qute.utilities.request.item(
        title="Polevector Axis",
        label="Select the axis the polevector should face down",
        items=possible_vector_channels,
        editable=False,
    )

    if not polevector_axis:
        return

    retain_child_transforms = qute.utilities.request.confirmation(
        title="Retain child transforms",
        label="Do you want to retain the worldspace transforms of child bones (excluding twists)?"
    )

    align_bones_for_ik(
        root,
        tip,
        primary_axis=forward_axis,
        polevector_axis=polevector_axis,
        retain_child_transforms=retain_child_transforms,
    )

    pins.create(pinned_joints)
    mc.select(pre_selection)


# --------------------------------------------------------------------------------------
def get_aim_dir(aim_label):
    aim_label = aim_label.lower()
    aim_dir = [0, 0, 0]

    # for idx in range(values):
    index = c.AXIS.index(aim_label[-1])
    aim_dir[index] = 1 * -1 if "negative" in aim_label else 1

    return aim_dir


# --------------------------------------------------------------------------------------
def get_inverted_aim_dir(aim_label):
    return [
        v * -1
        for v in get_aim_dir(aim_label)
    ]


# --------------------------------------------------------------------------------------
@utils.undoable
def align_bones_for_ik(
        root,
        tip,
        primary_axis,
        polevector_axis,
        retain_child_transforms=True,
):
    try:
        joint_parent = mc.listRelatives(root, parent=True)[0]
    except (TypeError, IndexError):
        joint_parent = None

    aim_axis = get_aim_dir(primary_axis)
    upvector_axis = get_aim_dir(polevector_axis)
    inverted_upvector_axis = get_inverted_aim_dir(polevector_axis)

    actual_chain = hierarchy.get_between(root, tip)
    orients.move_joint_orients_to_rotations(actual_chain)

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
                twist_factors[child] = math.get_factor_between(
                    child,
                    joint,
                    actual_chain[idx + 1],
                )

    replicated_joints = hierarchy.replicate_chain(root, tip, parent=None)
    orients.move_joint_orients_to_rotations(replicated_joints)

    for idx, joint in enumerate(replicated_joints):
        try:
            mc.parent(
                joint,
                world=True,
            )

        except RuntimeError:
            pass

        orients.move_joint_orients_to_rotations([joint])

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

    orients.move_joint_orients_to_rotations(replicated_joints)

    # -- Zero the last joints rotation
    for axis in c.AXIS:
        mc.setAttr(
            f"{replicated_joints[-1]}.rotate{axis.upper()}",
            0,
        )

    for idx in range(len(actual_chain)):
        hierarchy.copy_joint_values(
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
                print("skipping")
                continue

            # -- Position the node
            transform.position_between(
                child,
                actual_chain[idx],
                actual_chain[idx + 1],
                twist_factors[child],
            )

            for axis in c.AXIS:
                mc.setAttr(f"{child}.r{axis.lower()}", 0)
                mc.setAttr(f"{child}.jointOrient{axis.upper()}", 0)


    mc.delete(replicated_joints)

