"""
Joint creation and joint chain utilities: replicating, reversing and measuring
chains, moving rotations to and from joint orients, twist joints, and the
facing and upvector directions of a chain.
"""
import typing

from maya import cmds
import mref

from ..registry import tool
from ..core import direction as _direction
from ..core import maths as _maths

if typing.TYPE_CHECKING:
    import aniseed


@tool(
    "Create Joint",
    classification="Rigging",
    user_facing=False,
)
def create(
    description: str,
    location: str,
    parent: str,
    config: "aniseed.RigConfiguration",
    match_to: str = None,
):
    """
    This is a simple tool which creates a joint but sets up the name based on the
    aniseed configuration.

    Args:
        description: The descriptive part of the name to apply
        location: The location to apply the name to
        parent: The parent of the joint
        config: The aniseed configuration
        match_to: If given, the joint will have its transform matched
            to this node
    """
    cmds.select(clear=True)

    joint_ = cmds.joint()

    joint_ = cmds.rename(
        joint_,
        config.generate_name(
            classification=config.joint,
            description=description,
            location=location,
        ),
    )

    if parent:
        cmds.parent(
            joint_,
            parent,
        )

    if match_to:
        cmds.xform(
            joint_,
            matrix=cmds.xform(
                match_to,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

    return joint_


@tool(
    "Create Spread Joints",
    classification="Rigging",
    user_facing=False,
)
def create_spread(
    root_joint: str,
    tip_joint: str,
    joint_count: float,
    axis="X",
    naming_function: callable = None,
):

    created_joints = []

    upper_increment = cmds.getAttr(
        f"{tip_joint}.translate{axis.upper()}",
    ) / (joint_count - 1)

    upper_twist_joints = list()

    for idx in range(joint_count):
        cmds.select(clear=True)
        spread_joint = cmds.rename(cmds.joint(), "SpreadJoint")

        if naming_function:
            spread_joint = cmds.rename(spread_joint, naming_function())

        cmds.parent(
            spread_joint,
            root_joint,
        )

        cmds.xform(
            spread_joint,
            matrix=cmds.xform(
                root_joint,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        cmds.setAttr(
            f"{spread_joint}.translateX",
            upper_increment * idx
        )

        created_joints.append(spread_joint)

    return created_joints


def copy_attributes(
    from_this: str = "",
    to_this: str = "",
    link: bool = False,
) -> None:
    """
    Copies all the transform and joint specific attribute data from the
    first given joint to the second.

    Args:
        from_this: The joint to copy values from
        to_this: The joint to copy values to
        link: If true, instead of setting values, the attributes will be
            connected.

    Returns:
        None
    """
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
                cmds.connectAttr(
                    f"{from_this}.{vector_attr + axis}",
                    f"{to_this}.{vector_attr + axis}",
                    force=True,
                )

            else:
                cmds.setAttr(
                    f"{to_this}.{vector_attr + axis}",
                    cmds.getAttr(
                        f"{from_this}.{vector_attr + axis}",
                    ),
                )


def replicate(
    joint: str = "",
    parent: str or None = "",
    worldspace: bool = False,
    link: bool = False,
    copy_local_name: bool = False,
):
    """
    Replicates an individual joint and makes it a child of the given
    parent.

    Args:
        joint: Joint to replicate
        parent: Node to parent the new node under
        link: If True then the attributes of the initial joint will be
            used as driving connections to this joint.
        copy_local_name: If true, the joint will be renamed to match
            that of the joint being copied (ignoring namespaces)

    Returns:
          The name of the created joint
    """

    # -- Create the joint
    cmds.select(clear=True)
    new_joint = cmds.joint()

    if parent:
        cmds.parent(
            new_joint,
            parent,
        )

    copy_attributes(
        from_this=joint,
        to_this=new_joint,
        link=link,
    )

    if copy_local_name:
        new_joint = cmds.rename(
            new_joint,
            joint.split(":")[-1],
        )

    if worldspace:
        cmds.xform(
            new_joint,
            matrix=cmds.xform(
                joint,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

    return new_joint


def get_between(
        start: str = "",
        end: str = "",
) -> list[str]:
    """
    This will return all the joints in between the start and end joints
    including the start and end joints. Only joints that are directly
    in the relationship chain between these joints will be included.

    Args:
        start: The highest level joint to search from
        end: The lowest level joint to search from.

    Return:
        List of joints
    """
    joints = []
    next_joint = end

    # -- Get all the joints that make up part of the continuous hierarchy
    long_name = cmds.ls(end, long=True)[0]
    chain = long_name.split("|")
    joints = chain[chain.index(start.split("|")[-1]):]
    return joints


def replicate_chain(
    from_this: str = "",
    to_this: str = "",
    parent: str = "",
    world: bool = True,
    replacements: dict = None,
) -> list[str]:
    """
    Given a start and end joint, this will replicate the joint chain
    between them exactly - ensuring that all joint attributes are correctly
    replicated.

    Args:
         from_this: Joint from which to start duplicating
         to_this: Joint to which the duplicating should stop. Only joints
            between this and from_this will be replicated.
        parent: The node the replicated chain should be parented under
        world: Whether to apply the first replicated chains transform
            in worldspace, otherwise it will be given the same local space
            attribute data.
        replacements: A dictionary of replacements to apply to the duplicated
            joint names.

    Returns:
        List of new joints
    """
    # -- Define our output joints
    new_joints = list()

    joints_to_trace = get_between(
        from_this,
        to_this,
    )

    # -- We can now cycle through our trace joints and replicate them
    next_parent = parent

    for joint_to_trace in joints_to_trace:
        new_joint = replicate(
            joint_to_trace,
            parent=next_parent,
        )

        if replacements:
            for replace_this, with_this in replacements.items():
                new_joint = cmds.rename(
                    new_joint,
                    new_joint.replace(
                        replace_this,
                        with_this,
                    ),
                )

        # -- The first joint we always have to simply match
        # -- in worldspace if required
        if world and joint_to_trace == joints_to_trace[0]:
            cmds.xform(
                new_joint,
                matrix=cmds.xform(
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


def reverse_chain(joints: list[str] = None) -> list[str]:
    """
    Reverses the hierarchy of the joint chain.

    Args:
        joints: List of joints in the chain to reverse

    Returns:
        The joint chain in its new order
    """
    # -- Store the base parent so we can reparent the chain
    # -- back under it
    try:
        base_parent = cmds.listRelatives(
            joints[0],
            parent=True,
        )[0]

    except (TypeError, IndexError):
        base_parent = None

    # -- Start by clearing all the hierarchy of the chain
    for joint in joints:
        cmds.parent(
            joint,
            world=True,
        )

    # -- Now build up the hierarchy in the reverse order
    for idx in range(len(joints)):
        try:
            cmds.parent(
                joints[idx],
                joints[idx + 1]
            )

        except IndexError:
            pass

    # -- Finally we need to set the base parent once
    # -- again
    if base_parent:
        cmds.parent(
            joints[-1],
            base_parent
        )
    else:
        cmds.parent(joints[-1], world=True)

    joints.reverse()

    return joints


def replicate_entire_chain(
        joint_root: str = "",
        parent: str = "",
        link: bool = False,
        copy_local_name: bool = False,
) -> str:
    """
    Given a starting point, this will replicate (duplicate) the entire
    joint chain. It allows for you to specify the parent for the duplicated
    chain, as well as optionally attribute-link it.

    Args:
        joint_root: The joint from which to duplicate from
        parent: The parent node for the duplicated chain
        link: If true, then the attributes will be linked together
        copy_local_name: If true, then the name of the joint being duplicated
            will be used as the name of the joint being created (minus namespace)

    Returns:
        The newly duplicated root joint
    """
    all_joints = cmds.listRelatives(
        joint_root,
        allDescendents=True,
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
                cmds.parent(
                    new_joint,
                    parent,
                )

        else:
            cmds.parent(
                new_joint,
                created_joints[cmds.listRelatives(original_joint, parent=True)[0]],
            )

    return new_root_joint


def chain_length(start: str = "", end: str = "", log_result: bool = True) -> float:
    """
    This will calculate the length of the chain in total.

    Args:
        start: The joint from which to start measuring
        end: The joint to which measuring should end
        log_result: If true, the result should be printed

    Returns:
        The total length of all the bones in the chain
    """
    all_joints = get_between(
        start,
        end,
    )
    distance = 0

    for idx, joint in enumerate(all_joints):

        if not idx:
            continue

        distance += _maths.distance_between(
            joint,
            all_joints[idx - 1],
        )

    # if log_result:
    #     print(f"Distance between {start} and {end}: {distance}")

    return distance


@tool(
    "Move Joint Rotations To Orients",
    classification="Rigging",
    categories=["Joints"],
)
def move_rotations_to_orients(joints: list[str] = None) -> None:
    """
    Moves the rotations on the given joints to the joint orients
    attributes (zeroing the rotations).

    Args:
        joints: List of joints to move the rotation attributes for

    Returns:
        None
    """
    if isinstance(joints, str):
        joints = [joints]

    if not joints:
        joints = cmds.ls(selection=True)

    if not joints:
        return

    for joint in joints:
        # -- Store the world space matrix
        ws_mat4 = cmds.xform(
            joint,
            query=True,
            matrix=True,
            worldSpace=True,
        )

        # -- Zero the joint orients
        for attr in ['jointOrientX', 'jointOrientY', 'jointOrientZ']:
            cmds.setAttr(
                f"{joint}.{attr}",
                0,
            )

        # -- Now we can restore the matrix
        cmds.xform(
            joint,
            matrix=ws_mat4,
            worldSpace=True,
        )

        # -- Now we can shift the values from the rotation to the orient
        # -- knowing that the world transform will be retained
        for axis in ['X', 'Y', 'Z']:

            cmds.setAttr(
                f"{joint}.jointOrient{axis}",
                cmds.getAttr(f"{joint}.rotate{axis}"),
            )

            cmds.setAttr(
                f"{joint}.rotate{axis}",
                0,
            )

    return None


@tool(
    "Move Joint Orients to Rotation",
    classification="Rigging",
    categories=["Joints"],
)
def move_orients_to_rotation(joints: list[str] = None) -> None:
    """
    Moves the values from the joint orient of the node to the rotation
    whilst retaining the transform of the node.

    Args:
        joints: The joint to alter

    Returns:
        None
    """

    if isinstance(joints, str):
        joints = [joints]

    if not joints:
        joints = cmds.ls(selection=True)

    if not joints:
        return

    for joint in joints:
        # -- Store the world space matrix
        ws_mat4 = cmds.xform(
            joint,
            query=True,
            matrix=True,
            worldSpace=True,
        )

        # -- Zero the joint orients
        for attr in ['jointOrientX', 'jointOrientY', 'jointOrientZ']:
            cmds.setAttr(
                f"{joint}.{attr}",
                0,
            )

        # -- Now we can restore the matrix
        cmds.xform(
            joint,
            matrix=ws_mat4,
            worldSpace=True,
        )


def roll(joints: list[str] = None, axis="x", value=90) -> None:
    """
    Moves the rotations on the given joints to the joint orients
    attributes (zeroing the rotations).

    Args:
        joints: List of joints to move the rotation attributes for

    Returns:
        None
    """
    if isinstance(joints, str):
        joints = [joints]

    mapped_joints = dict()

    # -- Create our mapping joints
    for joint in joints:

        cmds.select(clear=True)
        transient_joint = cmds.joint()
        cmds.xform(
            transient_joint,
            worldSpace=True,
            matrix=cmds.xform(
                joint,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
        )
        move_rotations_to_orients(joints=[transient_joint])
        cmds.setAttr(f"{transient_joint}.rotate{axis.upper()}", value)

        # -- Now we need to get the matrix of all children whilst
        # -- we perform the match
        child_matrices = dict()
        for child in cmds.listRelatives(joint, children=True) or list():
            child_matrices[child] = cmds.xform(
                child,
                query=True,
                worldSpace=True,
                matrix=True,
            )

        # -- Perform the roll match
        cmds.xform(
            joint,
            worldSpace=True,
            matrix=cmds.xform(
                transient_joint,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
        )

        for child, matrix in child_matrices.items():
            cmds.xform(
                child,
                worldSpace=True,
                matrix=matrix,
            )

        # -- Finally delete the transient
        cmds.delete(transient_joint)

    cmds.select(joints)
    return None


def chain_from_ordered_dict(joint_data, location, config, parent, prefix="", subtract_label=""):
    identity_data = {"tx": 0, "ty": 0, "tz": 0, "rx": 0, "ry": 0, "rz": 0, "sx": 1, "sy": 1, "sz": 1, "jointOrientX": 0, "jointOrientY": 0, "jointOrientZ": 0}

    joints = []
    next_parent = parent
    for name, attributes in joint_data.items():
        joint = create(
            description=prefix+name.replace(subtract_label, ""),
            location=location,
            parent=next_parent,
            config=config,
        )
        all_attribute_data = identity_data.copy()
        all_attribute_data.update(attributes)

        for attribute, value in all_attribute_data.items():
            cmds.setAttr(f"{joint}.{attribute}", value)

        joints.append(joint)
        next_parent = joint

    return joints


def make_referenced(joints):

    if isinstance(joints, str):
        joints = [joints]

    for joint in joints:
        try:
            cmds.setAttr(joint + ".overrideEnabled", 1)
            cmds.setAttr(joint + ".overrideDisplayType", 2)  # 2 = Reference
        except:
            pass


def unreference(joints):
    if isinstance(joints, str):
        joints = [joints]

    try:
        for joint in joints:
            cmds.setAttr(joint + ".overrideDisplayType", 0)  # 0 = Normal
    except:
        pass


def is_referenced(joint):
    if not cmds.getAttr(joint + ".overrideEnabled"):
        return False

    if cmds.getAttr(joint + ".overrideDisplayType")  != 2: # 2 = Reference
        return False

    return True


def reparent_unknown_children(known_joints, new_parent):

    # -- Get a reference to all the known joints
    known_joints = [mref.get(j) for j in known_joints]

    # -- We will return a list of reparented joints, so declare
    # -- that here
    reparented_joints = []

    for joint in known_joints:

        # -- Cycle the children. If the child is a known
        # -- joint then we can ignore it, but if it is not
        # -- a known joint then we need to reparent it.
        for child in joint.children():
            if child not in known_joints:
                child.set_parent(new_parent)
                reparented_joints.append(child.name())

    return reparented_joints


def create_twist_joints(start, end, twist_count, description, location, config, down_bone_axis="x"):
    """
    This will create an even spread of twist joints which are a child
    of the start joint and spread between the start and end
    """
    parent = start

    if twist_count > 1:
        upper_increment = cmds.getAttr(
            f"{end}.translate{down_bone_axis.title()}",
        ) / (twist_count - 1)
    else:
        upper_increment = cmds.getAttr(f"{end}.translate{down_bone_axis.title()}")

    twist_joints = list()

    for idx in range(twist_count):
        twist_joint = create(
            description=description,
            location=location,
            parent=parent,
            match_to=parent,
            config=config
        )
        twist_joints.append(twist_joint)

        pre_distance = _maths.distance_between(
            twist_joint,
            end,
        )

        cmds.setAttr(
            f"{twist_joint}.translate{down_bone_axis.title()}",
            upper_increment * idx
        )

        post_distance = _maths.distance_between(
            twist_joint,
            end,
        )

        if post_distance > pre_distance:
            cmds.setAttr(
                f"{twist_joint}.translate{down_bone_axis.title()}",
                upper_increment * -idx
            )

    return twist_joints


class HeldTransforms:

    def __init__(self, joints):
        self.joints = joints
        self.matrices = dict()

    def __enter__(self):
        for joint in self.joints:
            self.matrices[joint] = cmds.xform(joint, query=True, matrix=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for joint, matrix in self.matrices.items():
            if cmds.objExists(joint):
                cmds.xform(joint, matrix=matrix)


@tool(
    "Get Chain Facing Direction",
    categories=["Transforms"],
    user_facing=False,
)
def get_chain_facing_direction(start: str = "", end: str = "", epsilon: float = 0.01) -> _direction.Direction:
    """
    This will return a Direction class which represents the facing direction
    of a chain. The facing direction is the direction ALL bones are using
    down-the-bone.

    The Direction instance is a class which provides easy access to directional
    data in different formats such as:
        axis: x, y, z
        full_string: Positive X, Negative X
        axis_vector: [1, 0, 0]
        direction_vector: [-1, 0, 0]
        cross_axis: x, y, z (the axis that crosses this one)

    Args:
        start: The first bone in the chain
        end: The last bone in the chain
        epsilon: How much variance in axis change we will tolerate

    Returns:
        Direction instance
    """
    axis = dict(
        x=0,
        y=0,
        z=0,
    )

    for joint in get_between(start, end)[1:]:
        for channel in axis:
            axis[channel] += cmds.getAttr(
                f"{joint}.translate{channel.upper()}",
            )

    has_x = abs(axis["x"]) > epsilon
    has_y = abs(axis["y"]) > epsilon
    has_z = abs(axis["z"]) > epsilon

    if sum([int(has_x), int(has_y), int(has_z)]) > 1:
        return _direction.Direction(_direction.Direction.Unknown)

    if has_x and axis["x"] > 0:
        return _direction.Direction(_direction.Direction.PositiveX)

    if has_x and axis["x"] < 0:
        return _direction.Direction(_direction.Direction.NegativeX)

    if has_y and axis["y"] > 0:
        return _direction.Direction(_direction.Direction.PositiveY)

    if has_y and axis["y"] < 0:
        return _direction.Direction(_direction.Direction.NegativeY)

    if has_z and axis["z"] > 0:
        return _direction.Direction(_direction.Direction.PositiveZ)

    if has_z and axis["z"] < 0:
        return _direction.Direction(_direction.Direction.NegativeZ)

    return _direction.Direction(_direction.Direction.Unknown)


def get_upvector_direction(start: str = "", end: str = "", epsilon: float = 0.01) -> _direction.Direction:
    """
    This will attempt to return a Direction instance which represents the
    upvector direction of the chain between the start and end joint.

    The Direction instance is a class which provides easy access to directional
    data in different formats such as:
        axis: x, y, z
        full_string: Positive X, Negative X
        axis_vector: [1, 0, 0]
        direction_vector: [-1, 0, 0]
        cross_axis: x, y, z (the axis that crosses this one)

    Args:
        start: The first bone in the chain
        end: The last bone in the chain
        epsilon: How much variance in axis change we will tolerate

    Returns:
        Direction instance
    """
    all_joints = get_between(start, end)

    temp_a = cmds.createNode("transform")
    temp_b = cmds.createNode("transform")

    facing_direction = get_chain_facing_direction(start, end, epsilon)

    cmds.parent(temp_b, temp_a)

    cmds.xform(
        temp_a,
        matrix=cmds.xform(
            all_joints[0],
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    cmds.xform(
        temp_b,
        matrix=cmds.xform(
            all_joints[1],
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    highest_rotation_value = 0
    recorded_value = 0
    rotate_axis = "X"

    for idx, axis in enumerate(["X", "Y", "Z"]):
        value = cmds.getAttr(f"{temp_b}.rotate{axis}")
        if abs(value) > highest_rotation_value:
            rotate_axis = axis
            highest_rotation_value = abs(value)
            recorded_value = value

    cmds.delete(temp_a)

    if facing_direction == _direction.Direction.PositiveX and rotate_axis == "Z":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.NegativeY)
        return _direction.Direction(_direction.Direction.PositiveY)

    if facing_direction == _direction.Direction.NegativeX and rotate_axis == "Z":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.PositiveY)
        return _direction.Direction(_direction.Direction.NegativeY)

    if facing_direction == _direction.Direction.PositiveX and rotate_axis == "Y":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.PositiveZ)
        return _direction.Direction(_direction.Direction.NegativeZ)

    if facing_direction == _direction.Direction.NegativeX and rotate_axis == "Y":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.NegativeZ)
        return _direction.Direction(_direction.Direction.PositiveZ)

    if facing_direction == _direction.Direction.PositiveY and rotate_axis == "Z":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.PositiveX)
        return _direction.Direction(_direction.Direction.NegativeX)

    if facing_direction == _direction.Direction.NegativeY and rotate_axis == "Z":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.NegativeX)
        return _direction.Direction(_direction.Direction.PositiveX)

    if facing_direction == _direction.Direction.PositiveY and rotate_axis == "X":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.NegativeZ)
        return _direction.Direction(_direction.Direction.PositiveZ)

    if facing_direction == _direction.Direction.NegativeY and rotate_axis == "X":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.PositiveZ)
        return _direction.Direction(_direction.Direction.NegativeZ)

    if facing_direction == _direction.Direction.PositiveZ and rotate_axis == "Y":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.NegativeX)
        return _direction.Direction(_direction.Direction.PositiveX)

    if facing_direction == _direction.Direction.NegativeZ and rotate_axis == "Y":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.PositiveX)
        return _direction.Direction(_direction.Direction.NegativeX)

    if facing_direction == _direction.Direction.PositiveZ and rotate_axis == "X":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.PositiveY)
        return _direction.Direction(_direction.Direction.NegativeY)

    if facing_direction == _direction.Direction.NegativeZ and rotate_axis == "X":
        if recorded_value >= 0:
            return _direction.Direction(_direction.Direction.NegativeY)
        return _direction.Direction(_direction.Direction.PositiveY)

    return _direction.Direction(_direction.Direction.Unknown)
