"""
Joint creation and joint chain utilities: replicating, reversing and measuring
chains, moving rotations to and from joint orients, twist joints, and the
facing and upvector directions of a chain.

Note on maya.cmds: most functions here take node names from the caller and
return the names Maya gives back (e.g. cmds.rename returns a partial path such
as "grp|joint1" when the short name is not unique, and callers rely on those
exact strings). Their error behaviour (the ValueError cmds raises for a missing
or ambiguous name) is also relied upon. mref resolves names differently, so
those calls stay on cmds; mref is used for the temporary nodes these functions
create and delete themselves.
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
    Creates a joint named using the aniseed configuration (the joint
    classification with the given description and location).

    The selection is cleared before the joint is created, and the new joint
    is left selected.

    Args:
        description: The descriptive part of the name to apply
        location: The location part of the name to apply
        parent: The node to parent the joint under. If empty, the joint
            stays at the scene root.
        config: The aniseed rig configuration used to generate the name
        match_to: If given, the joint is matched to this node's world
            space matrix

    Returns:
        The name of the created joint, as returned by Maya
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
    """
    Creates joints spread evenly between the root joint and the tip joint.
    Each joint is parented under the root joint, matched to it in world
    space and then offset along its translateX.

    The selection is cleared before each joint is created.

    Args:
        root_joint: The joint the spread joints are parented under and
            start from
        tip_joint: The joint whose translation (along the given axis)
            defines the length of the spread
        joint_count: The number of joints to create (a whole number, at
            least 2)
        axis: The axis of the tip joint's translation used to measure the
            spread length. The joints themselves are always offset along
            translateX.
        naming_function: An optional callable taking no arguments which
            returns the name for each new joint. If not given, each joint
            is named "SpreadJoint".

    Returns:
        List of the created joint names
    """
    created_joints = []

    upper_increment = cmds.getAttr(
        f"{tip_joint}.translate{axis.upper()}",
    ) / (joint_count - 1)

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
    Copies the translate, rotate, scale, jointOrient and preferredAngle
    values (per axis) from the first given joint to the second.

    Args:
        from_this: The joint to copy values from
        to_this: The joint to copy values to
        link: If true, instead of setting values, the attributes of
            from_this are connected (forced) to those of to_this.

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
    Replicates an individual joint (see copy_attributes for the attributes
    which are copied) and makes it a child of the given parent.

    The selection is cleared and the new joint is created with Maya's
    default joint name (joint1, joint2, ...) unless copy_local_name is set.

    Args:
        joint: Joint to replicate
        parent: Node to parent the new joint under. If empty or None, the
            new joint stays at the scene root.
        worldspace: If True, the new joint is matched to the world space
            matrix of the given joint after the attributes are copied.
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

    The result is read from the full path of the end node, so the start
    node must be one of its ancestors (or the end node itself), otherwise
    a ValueError is raised.

    Args:
        start: The highest level joint to search from
        end: The lowest level joint to search from.

    Returns:
        List of short (leaf) node names, ordered from start to end
    """
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

    The new joints get Maya's default joint names (joint1, joint2, ...)
    unless replacements are given.

    Args:
        from_this: Joint from which to start duplicating
        to_this: Joint to which the duplicating should stop. Only joints
            between this and from_this will be replicated.
        parent: The node the replicated chain should be parented under
        world: Whether to apply the first replicated chains transform
            in worldspace, otherwise it will be given the same local space
            attribute data.
        replacements: A dictionary of replacements (search: replace) to
            apply to the default names of the duplicated joints.

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
    Reverses the hierarchy of the joint chain, so the last joint becomes
    the root (under the original root's parent, or the scene root) and the
    first joint becomes the tip.

    Note that the given list is reversed in place and returned.

    Args:
        joints: List of joints in the chain to reverse, ordered root to tip

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
    joint hierarchy below it (every descendant joint). It allows for you to
    specify the parent for the duplicated chain, as well as optionally
    attribute-link it.

    Args:
        joint_root: The joint from which to duplicate from
        parent: The parent node for the duplicated chain. If empty, the new
            root stays at the scene root.
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
    This will calculate the length of the chain in total, as the sum of the
    world space distances between each consecutive pair of joints from
    start to end.

    Args:
        start: The joint from which to start measuring
        end: The joint to which measuring should end
        log_result: Not used (the result is never printed). Kept for
            compatibility.

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

    return distance


@tool(
    "Move Joint Rotations To Orients",
    classification="Rigging",
    categories=["Joints"],
)
def move_rotations_to_orients(joints: list[str] = None) -> None:
    """
    Moves the rotations on the given joints to the joint orients
    attributes (zeroing the rotations) whilst retaining the world
    transform of each joint.

    Args:
        joints: A joint or list of joints to move the rotation attributes
            for. Uses the selection if no joints are given.

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
    Moves the values from the joint orient of the given joints to their
    rotation (zeroing the joint orients) whilst retaining the world
    transform of each joint.

    Args:
        joints: A joint or list of joints to alter. Uses the selection if
            no joints are given.

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
    Rolls each of the given joints around one of its own local axes by the
    given amount, keeping the world transforms of its children.

    The new orientation is applied through the joint's world matrix, so
    the resulting values end up on the joint's rotate channels. The given
    joints are selected afterwards.

    Args:
        joints: A joint or list of joints to roll (required)
        axis: The local axis to roll around: "x", "y" or "z"
        value: The amount to roll by, in degrees

    Returns:
        None
    """
    if isinstance(joints, str):
        joints = [joints]

    # -- Create our mapping joints
    for joint in joints:

        # -- A temporary joint which is matched to the joint, has its
        # -- rotation moved to its orients and is then rolled
        cmds.select(clear=True)
        transient_joint = mref.get(cmds.joint())
        transient_joint.set_matrix(
            cmds.xform(
                joint,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
            space="world",
        )
        move_rotations_to_orients(joints=[transient_joint.name()])
        transient_joint.attr(f"rotate{axis.upper()}").set(value)

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
            matrix=transient_joint.get_matrix(space="world"),
        )

        for child, matrix in child_matrices.items():
            cmds.xform(
                child,
                worldSpace=True,
                matrix=matrix,
            )

        # -- Finally delete the transient
        transient_joint.delete()

    cmds.select(joints)
    return None


def chain_from_ordered_dict(joint_data, location, config, parent, prefix="", subtract_label=""):
    """
    Creates a chain of joints (each one parented under the previous one)
    from an ordered dictionary of joint names and attribute values.

    Each joint is created with create() and first reset to identity
    (translate, rotate and jointOrient zeroed, scale one) before the given
    attribute values are applied.

    Args:
        joint_data: Ordered dictionary where each key is a joint description
            and each value is a dictionary of attribute names (e.g. "tx",
            "jointOrientZ") and the values to set on that joint
        location: The location part of the joint names
        config: The aniseed rig configuration used to generate the names
        parent: The node the first joint is parented under
        prefix: A string prefixed to each description
        subtract_label: A string removed from each description

    Returns:
        List of the created joint names, in chain order
    """
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
    """
    Makes the given joints display as referenced (unselectable in the
    viewport) by enabling their drawing overrides and setting the display
    type to Reference. Joints which cannot be changed (e.g. missing nodes)
    are silently skipped.

    Args:
        joints: A joint or list of joints
    """

    if isinstance(joints, str):
        joints = [joints]

    for joint in joints:
        try:
            cmds.setAttr(joint + ".overrideEnabled", 1)
            cmds.setAttr(joint + ".overrideDisplayType", 2)  # 2 = Reference
        except:
            pass


def unreference(joints):
    """
    Sets the drawing override display type of the given joints back to
    Normal (overrideEnabled is left as it is). Stops silently at the first
    joint which cannot be changed.

    Args:
        joints: A joint or list of joints
    """
    if isinstance(joints, str):
        joints = [joints]

    try:
        for joint in joints:
            cmds.setAttr(joint + ".overrideDisplayType", 0)  # 0 = Normal
    except:
        pass


def is_referenced(joint):
    """
    Returns whether the given joint is displayed as referenced, i.e. its
    drawing overrides are enabled and its display type is Reference.

    Args:
        joint: The joint to check

    Returns:
        True if the joint is displayed as referenced
    """
    if not cmds.getAttr(joint + ".overrideEnabled"):
        return False

    if cmds.getAttr(joint + ".overrideDisplayType") != 2:  # 2 = Reference
        return False

    return True


def reparent_unknown_children(known_joints, new_parent):
    """
    Reparents (keeping world transforms) every child of the given known
    joints which is not itself one of the known joints to the new parent.

    Args:
        known_joints: List of joints whose children should be checked
        new_parent: The node to move the unknown children under

    Returns:
        List of the short names of the reparented children
    """

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
    of the start joint and spread between the start and end.

    Each twist joint is created with create(), matched to the start joint
    and offset along the down-the-bone axis. If the offset moves the joint
    away from the end joint, the offset is negated (for chains pointing
    down the negative axis).

    Args:
        start: The joint the twist joints are parented under
        end: The joint the twist joints spread towards
        twist_count: The number of twist joints to create
        description: The descriptive part of the twist joint names
        location: The location part of the twist joint names
        config: The aniseed rig configuration used to generate the names
        down_bone_axis: The axis ("x", "y" or "z") pointing down the bone

    Returns:
        List of the created twist joint names
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
    """
    Context manager which stores the local (object space) matrices of the
    given nodes on entry and restores them on exit, skipping any node which
    no longer exists.

    Args:
        joints: List of nodes whose transforms should be held

    Attributes:
        joints: The nodes given
        matrices: Dictionary of node to its stored local matrix (filled
            on entry)
    """

    def __init__(self, joints):
        self.joints = joints
        self.matrices = dict()

    def __enter__(self):
        """
        Stores the local matrix of every node.

        Returns:
            This HeldTransforms instance
        """
        for joint in self.joints:
            self.matrices[joint] = cmds.xform(joint, query=True, matrix=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Restores the stored local matrix of every node which still exists.
        Exceptions are not suppressed.
        """
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
    down-the-bone, worked out from the sum of the local translations of
    every joint after the start joint.

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
        Direction instance (Unknown if more than one axis is used, or none)
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

    It is worked out from the facing direction of the chain and the
    rotation of the second joint relative to the first (measured with two
    temporary transforms, which are deleted again). The chain must contain
    at least two joints.

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

    temp_a = mref.create("transform")
    temp_b = mref.create("transform")

    facing_direction = get_chain_facing_direction(start, end, epsilon)

    temp_a.add_child(temp_b)

    temp_a.set_matrix(
        cmds.xform(
            all_joints[0],
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        space="world",
    )

    temp_b.set_matrix(
        cmds.xform(
            all_joints[1],
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        space="world",
    )

    highest_rotation_value = 0
    recorded_value = 0
    rotate_axis = "X"

    for axis in ["X", "Y", "Z"]:
        value = temp_b.attr(f"rotate{axis}").get()
        if abs(value) > highest_rotation_value:
            rotate_axis = axis
            highest_rotation_value = abs(value)
            recorded_value = value

    temp_a.delete()

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
