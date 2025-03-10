import maya.cmds as mc

from . import math


# --------------------------------------------------------------------------------------
def get_parent(node):
    """
    In maya, when getting the parent you're either given a list
    if there are parents or None if there is not. This means you're
    having to constantly deal with two different data types.

    This function will return the immediate parent if there is one
    and None if there is not. This avoids having to wrap every
    listRelatives call in an IndexException catch
    """
    try:
        return mc.listRelatives(
            node,
            parent=True,
        )[0]

    except IndexError:
        return None


# --------------------------------------------------------------------------------------
def get_between(start, end):

    joints = []
    next_joint = end

    # -- Get all the joints that make up part of the continuous hierarchy
    long_name = mc.ls(end, long=True)[0]
    chain = long_name.split("|")
    joints = chain[chain.index(start):]
    return joints


# --------------------------------------------------------------------------------------
def copy_joint_values(
    from_this,
    to_this,
    link=False,
):

    # -- Attributes to copy
    vector_attrs = [
        'translate',
        'rotate',
        'scale',
        'jointOrient',
        'preferredAngle',
    ]

    # -- Set the specific attributes
    for vector_attr in vector_attrs:
        for axis in ['X', 'Y', 'Z']:

            if link:
                mc.connectAttr(
                    f"{from_this}.{vector_attr + axis}",
                    f"{to_this}.{vector_attr + axis}",
                    force=True,
                )

            else:
                mc.setAttr(
                    f"{to_this}.{vector_attr + axis}",
                    mc.getAttr(
                        f"{from_this}.{vector_attr + axis}",
                    ),
                )


# --------------------------------------------------------------------------------------
def replicate(joint, parent, link=False, copy_local_name=False):
    """
    Replicates an individual joint and makes it a child of the parent

    :param joint: Joint to replicate
    :type joint: pm.nt.Joint

    :param parent: Node to parent the new node under
    :type parent: pm.nt.DagNode

    :return: pm.nt.Joint
    """

    # -- Create the joint
    mc.select(clear=True)
    new_joint = mc.joint()

    if parent:
        mc.parent(
            new_joint,
            parent,
        )

    copy_joint_values(
        from_this=joint,
        to_this=new_joint,
        link=link,
    )

    if copy_local_name:
        new_joint = mc.rename(
            new_joint,
            joint.split(":")[-1],
        )

    return new_joint


# --------------------------------------------------------------------------------------
def reverse_chain(joints):
    """
    Reverses the hierarchy of the joint chain.

    :param joints: List of joints in the chain to reverse

    :return: the same list of joints in reverse order
    """
    # -- Store the base parent so we can reparent the chain
    # -- back under it
    try:
        base_parent = mc.listRelatives(
            joints[0],
            parent=True,
        )[0]

    except (TypeError, IndexError):
        base_parent = None

    # -- Start by clearing all the hierarchy of the chain
    for joint in joints:
        mc.parent(
            joint,
            world=True,
        )

    # -- Now build up the hierarchy in the reverse order
    for idx in range(len(joints)):
        try:
            mc.parent(
                joints[idx],
                joints[idx + 1]
            )

        except IndexError:
            pass

    # -- Finally we need to set the base parent once
    # -- again
    if base_parent:
        mc.parent(
            joints[-1],
            base_parent
        )
    else:
        mc.parent(joints[-1], world=True)

    joints.reverse()

    return joints



def replicate_all_chain(joint_root, parent=None, link=False, copy_local_name=False):

    all_joints = mc.listRelatives(
        joint_root,
        ad=True,
        type="joint",
    )

    all_joints.insert(0, joint_root)

    created_joints = dict()
    new_root_joint = None

    for joint in all_joints:

        replicated = replicate(
            joint,
            parent=None,
            link=link,
            copy_local_name=copy_local_name,
        )

        created_joints[joint] = replicated

        if not new_root_joint:
            new_root_joint = replicated

    # -- Now setup the hierarchy
    for original_joint, new_joint in created_joints.items():

        if original_joint == joint_root:

            if parent:
                mc.parent(
                    new_joint,
                    parent,
                )

            # else:
            #     mc.parent(
            #         new_joint,
            #         world=True,
            #     )

        else:
            mc.parent(
                new_joint,
                created_joints[mc.listRelatives(original_joint, parent=True)[0]],
            )

    return new_root_joint


# ------------------------------------------------------------------------------
def replicate_chain(from_this, to_this, parent, world=True, replacements=None):
    """
    Replicates the joint chain exactly
    """
    # -- Define our output joints
    new_joints = list()

    joints_to_trace = get_between(from_this, to_this)

    # -- We can now cycle through our trace joints and replicate them
    next_parent = parent

    for joint_to_trace in joints_to_trace:
        new_joint = replicate(
            joint_to_trace,
            parent=next_parent,
        )

        if replacements:
            for replace_this, with_this in replacements.items():
                new_name = new_joint.replace(
                    replace_this,
                    with_this,
                )
                new_name = mc.rename(
                    new_joint,
                    new_name,
                )

        # -- The first joint we always have to simply match
        # -- in worldspace if required
        if world and joint_to_trace == joints_to_trace[0]:
            mc.xform(
                new_joint,
                matrix=mc.xform(
                    joint_to_trace,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

        # -- Store the new joint
        new_joints.append(new_joint)

        # -- Mark the new joint as being the parent for
        # -- the next
        next_parent = new_joint

    return new_joints


# ------------------------------------------------------------------------------
def chain_length(start, end):

    all_joints = get_between(start, end)
    distance = 0

    for idx, joint in enumerate(all_joints):

        if not idx:
            continue

        distance += math.distance_between(
            joint,
            all_joints[idx-1],
        )

    return distance
