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


def lock_and_hide(nodes: list, attributes: list, lock=True, hide=True) -> None:
    """
    This will lock and hide (optionally) the list of attributes from the list
    of nodes.
    :param nodes:
    :param attributes:
    :return:
    """
    for node in nodes:
        for attribute in attributes:
            cmds.setAttr(
                f"{node}.{attribute}",
                lock=lock,
                channelBox=not hide,
                keyable=not hide,
            )
