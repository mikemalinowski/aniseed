"""
Transform utilities: creating named transforms, matching, relative matrices,
positioning between nodes, aiming, scaling translations and driving
transforms from matrices.

Nodes given by the caller are read and written with xform through mref
(rather than the Transform trait), so anything xform accepts keeps working.
"""
import typing

from maya import cmds
import mref

from ..registry import tool
from ..core import direction as _direction
from ..core import _nodes

if typing.TYPE_CHECKING:
    import aniseed


@tool(
    "Create Basic Transform",
    classification="Creation",
    user_facing=False,
)
def create(
        classification: str,
        description: str,
        location: str,
        config: "aniseed.RigConfiguration",
        parent=None,
        match_to=None,
) -> str:
    """
    Creates a transform named using the aniseed config, and optionally
    parents it and matches its transform.

    Args:
        classification: The classification part of the name to apply
        description: The description part of the name to apply
        location: The location part of the name to apply
        config: The aniseed configuration instance
        parent: Optionally provide a parent, and this node will be made
            a child of it on creation (keeping its world transform).
        match_to: Optionally the node name (str) or flat world matrix
            (list/tuple of 16 floats) to match the new node to. Other types
            are ignored.

    Returns:
        The name of the created node, as given by the rename (the shortest
        unique name at that point, before any parenting)
    """
    node = mref.create("transform")

    # -- cmds.rename rather than node.rename because its return value (the
    # -- shortest unique name) is what this function returns
    node_name = cmds.rename(
        node.full_name(),
        config.generate_name(
            classification=classification,
            description=description,
            location=location,
        ),
    )

    if parent:
        node.set_parent(_nodes.resolve(parent))

    if match_to:
        if isinstance(match_to, str):
            node.set_matrix(
                mref.xform(match_to, query=True, matrix=True, worldSpace=True),
                space="world",
            )

        elif isinstance(match_to, (list, tuple)):
            node.set_matrix(match_to, space="world")

    return node_name


def create_locator_at_center(components=None) -> str:
    """
    Creates a locator at the center of the currently selected components
    (or nodes), using a temporary cluster.

    Note that the cluster is always made from the current selection;
    components is only used to decide whether there is anything to work on
    (if it is not given, the selection is used for that too).

    Args:
        components: Optional list of components. If neither this nor the
            selection has anything in it, nothing is created.

    Returns:
        The result of cmds.spaceLocator (a list holding the name of the
        locator transform), or an empty string if there was nothing to work
        on
    """
    components = components or mref.selected()
    # -- If nothing selected, do nothing
    if not components:
        return ""

    # -- Create a temporary cluster (from the selection), snap the locator
    # -- to its handle, then remove the cluster and constraint
    temp_cluster = mref.cluster()
    locator = mref.spaceLocator()
    temp_constraint = mref.pointConstraint(
        temp_cluster[1],
        locator,
        maintainOffset=False
    )
    mref.delete(temp_cluster, temp_constraint)

    return locator.names()


def drive_from_local_matrix(driver, driven) -> mref.ReferencedItem:
    """
    Drives the translate, rotate and scale of the driven transform from
    the local matrix of the driver (via a decomposeMatrix node). This makes
    the driven node mimic the local transform of the driver.

    Args:
        driver: The transform whose local matrix should be read
        driven: The transform to drive

    Returns:
        The decomposeMatrix node
    """
    driver = mref.get(driver)
    driven = mref.get(driven)

    decompose_node = mref.create("decomposeMatrix")
    driver.attr("matrix").connect(decompose_node.inputMatrix)
    decompose_node.outputTranslate.connect(driven.attr("translate"))
    decompose_node.outputRotate.connect(driven.attr("rotate"))
    decompose_node.outputScale.connect(driven.attr("scale"))

    return decompose_node


@tool(
    "Position Between",
    categories=["Transforms"],
)
def position_between(
    node: str = "",
    from_this: str = "",
    to_this: str = "",
    factor = 0.5,
):
    """
    Sets the translation of the given node to a position between from_this
    and to_this, using a temporary point constraint. A factor of zero puts
    the node on top of from_this, whilst a factor of 1 puts it on top of
    to_this.

    Args:
        node: The node to adjust the position for
        from_this: The first node to consider
        to_this: The second node to consider
        factor: The factor value to use

    Returns:
        None
    """
    constraint = mref.pointConstraint(
        to_this,
        node,
        maintainOffset=False,
    )[0]

    mref.pointConstraint(
        from_this,
        node,
        maintainOffset=False,
    )

    # -- The targets are to_this then from_this
    weights = constraint.weight_attributes()
    weights[0].set(1 - factor)
    weights[-1].set(factor)

    # -- Keep the constrained result once the constraint is removed
    matrix = mref.xform(
        node,
        query=True,
        matrix=True,
    )

    constraint.delete()

    mref.xform(
        node,
        matrix=matrix,
    )


@tool(
    "Get Relative Matrix",
    categories=["Transforms"],
    user_facing=False,
)
def get_relative_matrix(node: str = "", relative_to: str = "") -> list[float]:
    """
    Returns the matrix of node relative to relative_to, i.e. the local
    matrix node would have if it were a child of relative_to.

    Args:
        node: The node to consider as the child
        relative_to: The node to consider as the parent

    Returns:
        The relative matrix as a flat list of 16 floats
    """
    parent_buffer = mref.create("transform")
    child_buffer = mref.create("transform")

    parent_buffer.add_child(child_buffer)

    # -- The buffers use xform without a space flag where the original
    # -- maths did, as an explicit objectSpace flag (get_matrix/set_matrix)
    # -- can differ in the last floating point bits
    parent_buffer.xform(
        matrix=mref.xform(relative_to, query=True, matrix=True, worldSpace=True),
    )

    child_buffer.set_matrix(
        mref.xform(node, query=True, matrix=True, worldSpace=True),
        space="world",
    )

    relative_matrix = child_buffer.xform(query=True, matrix=True)
    parent_buffer.delete()

    return relative_matrix


@tool(
    "Apply Relative Matrix",
    categories=["Transforms"],
    user_facing=False,
)
def apply_relative_matrix(node: str, matrix: list[float], relative_to: str = ""):
    """
    Applies the matrix to the node as if the node were a child of the
    relative_to node (the reverse of get_relative_matrix). The node's world
    transform is set; its actual parent is not changed.

    Args:
        node: The node to adjust
        matrix: The relative matrix to apply, as a flat list of 16 floats
        relative_to: The node to use as the parent space

    Returns:
        None
    """
    parent_buffer = mref.create("transform")
    child_buffer = mref.create("transform")

    parent_buffer.add_child(child_buffer)

    # -- xform without a space flag, as in get_relative_matrix
    parent_buffer.xform(
        matrix=mref.xform(relative_to, query=True, matrix=True, worldSpace=True),
    )

    child_buffer.xform(matrix=matrix)

    mref.xform(
        node,
        matrix=child_buffer.get_matrix(space="world"),
        worldSpace=True,
    )

    parent_buffer.delete()


def snap_position(snap_this, to_this=None):
    """
    Sets the world space translation of snap_this to that of to_this, or to
    the origin if to_this is not given. Rotation and scale are untouched.

    Args:
        snap_this: The node to move
        to_this: The node to move it to

    Returns:
        None
    """
    translation = [0, 0, 0]

    if to_this:
        translation = mref.xform(
            to_this,
            query=True,
            translation=True,
            worldSpace=True,
        )

    mref.xform(
        snap_this,
        translation=translation,
        worldSpace=True,
    )


def aim_at(node, target, aim_axis, up_axis, up_target=None):
    """
    Rotates the node to aim at the target, using a temporary aim
    constraint.

    Args:
        node: The node to rotate
        target: The node to aim at
        aim_axis: The axis of node to point at the target, as "x", "-x",
            "y" etc. (see Direction.from_string)
        up_axis: The axis of node to point towards the up target (or the
            scene up if there is no up target), in the same form
        up_target: Optional node to use as the up object. If not given the
            scene up is used.

    Returns:
        None
    """
    aim_vector = _direction.Direction.from_string(aim_axis).direction_vector
    up_vector = _direction.Direction.from_string(up_axis).direction_vector

    if up_target:
        temp_constraint = mref.aimConstraint(
            target,
            node,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=up_target,
        )
    else:
        # -- Aim with the scene up as the up vector
        temp_constraint = mref.aimConstraint(
            target,
            node,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="scene",
        )

    mref.delete(temp_constraint)


def scale_translation(node, scale_by=1.0):
    """
    Multiplies the translate X, Y and Z values of the given node.

    Args:
        node: Node to scale the translation values of
        scale_by: Amount to scale by

    Returns:
        None
    """
    node = mref.get(node)
    for axis in ["X", "Y", "Z"]:
        attr = node.attr(f"translate{axis}")

        if attr:
            attr.set(attr.get() * scale_by)


def scale_translation_of_hierarchy(root_node, scale_by=1.0):
    """
    Multiplies the translate values of the root node and of every
    transform and joint below it (see scale_translation).

    Args:
        root_node: The top node of the hierarchy
        scale_by: Amount to scale by

    Returns:
        None
    """
    root_node = mref.get(root_node)
    all_nodes = [root_node]
    all_nodes.extend(root_node.children(recursive=True))

    for node in all_nodes:
        if node.node_type() in ["transform", "joint"]:
            scale_translation(node, scale_by)
