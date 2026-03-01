import aniseed
from maya import cmds


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

