from maya import cmds


def add_separator(node: str = "") -> None:
    """
    Adds an underscored attribute as an attribute separator

    Args:
        node: Node to add the separator to

    Return:
        None
    """
    if not node:
        node = cmds.ls(sl=True)[0]

    character = "_"
    name_to_use = character * 8

    while cmds.objExists(f"{node}.{name_to_use}"):
        name_to_use += character

    cmds.addAttr(
        node,
        shortName=name_to_use,
        keyable=True,
    )
    cmds.setAttr(f"{node}.{name_to_use}", lock=True)
