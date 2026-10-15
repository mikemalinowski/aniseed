"""
Transform utilities: creating named transforms, matching, relative matrices,
positioning between nodes, aiming, scaling translations and driving
transforms from matrices.
"""
import typing

from maya import cmds
import mref

from ..registry import tool
from ..core import direction as _direction

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
    This will create a basic transform node but will name it using the aniseed
    config, and optionally set the parenting and transforms.

    Args:
        classification: The classification part of the name to apply
        description: The description part of the name to apply
        location: The location part of the name to apply
        config: The aniseed configuration instance
        parent: Optionally provide a parent, and this node will be made
            a child of it on creation.
        match_to: Optionally provide a node to match transform to on creation

    Returns:
        The name of the created node
    """
    # -- Create our component org to keep everything together
    node = cmds.rename(
        cmds.createNode("transform"),
        config.generate_name(
            classification=classification,
            description=description,
            location=location,
        ),
    )

    if parent:
        cmds.parent(
            node,
            parent,
        )

    if match_to:
        if isinstance(match_to, str):
            cmds.xform(
                node,
                matrix=cmds.xform(
                    match_to,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

        elif isinstance(match_to, (list, tuple)):
            cmds.xform(
                node,
                matrix=match_to,
                worldSpace=True,
            )

    return node


def create_locator_at_center(components=None) -> str:
    """
    Creates a locator at the center of the current selected components

    Returns:
        The name of the created locator
    """
    components = components or cmds.ls(selection=True)
    # -- If nothing selected, do nothing
    if not components:
        return ""

    # -- Create a temporary cluster, snap position, remove temporary cluster/constraint
    temp_cluster = cmds.cluster()
    locator = cmds.spaceLocator()
    temp_constraint = cmds.pointConstraint(
        temp_cluster[1],
        locator,
        maintainOffset=False
    )
    cmds.delete(temp_cluster, temp_constraint)

    return locator


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
    This will set the translation of the given node to be at a position
    between from_this and to_this based on the factor value. A factor
    of zero will mean a position on top of from_this, whilst a factor
    of 1 will mean a position on bottom of to_this.

    Args:
        node: The node to adjust the position for
        from_this: The first node to consider
        to_this: The second node to consider
        factor: The factor value to use

    Returns:
        None
    """
    cns = cmds.pointConstraint(
        to_this,
        node,
        maintainOffset=False,
    )[0]

    cmds.pointConstraint(
        from_this,
        node,
        maintainOffset=False,
    )

    cmds.setAttr(
        cns + "." + cmds.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[0],
        1 - factor
    )

    cmds.setAttr(
        cns + "." + cmds.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[-1],
        factor,
    )

    xform = cmds.xform(
        node,
        query=True,
        matrix=True,
    )

    cmds.delete(cns)

    cmds.xform(
        node,
        matrix=xform,
    )


@tool(
    "Get Relative Matrix",
    categories=["Transforms"],
    user_facing=False,
)
def get_relative_matrix(node: str = "", relative_to: str = "") -> list[float]:
    """
    This will get a matrix which is the relative matrix between the relative_to
    and the node item

    Args:
        node: The node to consider as the child
        relative_to: The node to consider as the parent

    Returns:
        relative matrix as a list (maya.cmds)
    """
    parent_buffer = cmds.createNode("transform")
    child_buffer = cmds.createNode("transform")

    cmds.parent(
        child_buffer,
        parent_buffer,
    )

    cmds.xform(
        parent_buffer,
        matrix=cmds.xform(
            relative_to,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
    )

    cmds.xform(
        child_buffer,
        matrix=cmds.xform(
            node,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    relative_matrix = cmds.xform(
        child_buffer,
        query=True,
        matrix=True,
    )
    cmds.delete(parent_buffer)

    return relative_matrix


@tool(
    "Apply Relative Matrix",
    categories=["Transforms"],
    user_facing=False,
)
def apply_relative_matrix(node: str, matrix: list[float], relative_to: str = ""):
    """
    This will apply the matrix to the node as if the node were a child
    of the relative_to node

    Args:
        node: The node to adjust
        matrix: The matrix to apply (maya.cmds)
        relative_to: The node to use as a parent for spatial transforms

    Returns:
        None
    """
    parent_buffer = cmds.createNode("transform")
    child_buffer = cmds.createNode("transform")

    cmds.parent(
        child_buffer,
        parent_buffer,
    )

    cmds.xform(
        parent_buffer,
        matrix=cmds.xform(
            relative_to,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
    )

    cmds.xform(
        child_buffer,
        matrix=matrix,
    )

    cmds.xform(
        node,
        matrix=cmds.xform(
            child_buffer,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    cmds.delete(parent_buffer)


def snap_position(snap_this, to_this=None):
    translation = [0, 0, 0]

    if to_this:
        translation = cmds.xform(
            to_this,
            query=True,
            translation=True,
            worldSpace=True,
        )

    cmds.xform(
        snap_this,
        translation=translation,
        worldSpace=True,
    )


def aim_at(node, target, aim_axis, up_axis, up_target=None):
    """
    This will a
    """
    aim_vector = _direction.Direction.from_string(aim_axis).direction_vector
    up_vector = _direction.Direction.from_string(up_axis).direction_vector

    if up_target:

        temp_constraint = cmds.aimConstraint(
            target,
            node,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=up_target,
        )
    else:
        # aim with assumed scene as upvector
        temp_constraint = cmds.aimConstraint(
            target,
            node,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="scene",
        )


    cmds.delete(temp_constraint)


def scale_translation(node, scale_by=1.0):
    """
    Scales the translation values of the given node
    Args:
        node: Node to scale the translation values of
        scale_by: Amount to scale by

    Returns:

    """
    node = mref.get(node)
    for axis in ["X", "Y", "Z"]:
        attr = node.attr(f"translate{axis}")

        if attr:
            attr.set(attr.get() * scale_by)


def scale_translation_of_hierarchy(root_node, scale_by=1.0):
    root_node = mref.get(root_node)
    all_nodes = [root_node]
    all_nodes.extend(root_node.children(recursive=True))

    for node in all_nodes:
        if node.node_type() in ["transform", "joint"]:
            scale_translation(node, scale_by)
