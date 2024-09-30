import maya.cmds as mc


# --------------------------------------------------------------------------------------
def add_separator_attr(node):
    """
    Adds an underscored attribute as an attribute separator

    :param node: Node to add the separator to
    :tpye node: pm.nt.DependNode

    :return: None
    """
    character = "_"
    name_to_use = character * 8

    while mc.objExists(f"{node}.{name_to_use}"):
        name_to_use += character

    mc.addAttr(
        node,
        shortName=name_to_use,
        k=True,
    )
    mc.setAttr(f"{node}.{name_to_use}", lock=True)
