import aniseed_toolkit
from maya import cmds


def hide(items: list[str] = None) -> None:
    """
    This will hide all the given nodes. However, it will first do a
    node type test, and if it is a joint it will hide it using the joint
    style attribute rather than the visibility attribute.

    Args:
        items: List of nodes to hide

    Returns:
        None
    """
    if not items:
        items = cmds.ls(sl=True)

    if not isinstance(items, list):
        items = [items]

    for item in items:

        if  cmds.nodeType(item, "joint"):
            cmds.setAttr(
                f"{item}.drawStyle",
                2,  # Invisible
            )

        else:
            cmds.setAttr(
                f"{item}.visibility",
                False,
            )


def show(items: list[str] = None) -> None:
    """
    This will show all the given nodes. However, it will first do a
    node type test, and if it is a joint it will show it using the joint
    style attribute rather than the visibility attribute.

    Args:
        items: List of nodes to hide

    Returns:
        None
    """
    if not items:
        items = cmds.ls(sl=True)

    if not isinstance(items, list):
        items = [items]

    for item in items:

        if cmds.nodeType(item, "joint"):
            cmds.setAttr(
                f"{item}.drawStyle",
                0,  # Bone
            )

        else:
            cmds.setAttr(
                f"{item}.visibility",
                True,
            )
