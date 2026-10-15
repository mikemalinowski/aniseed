"""
Tagging nodes with string tags, and finding nodes by tag.
"""
from maya import cmds

from ..registry import tool


_TAG_ATTRIBUTE_ = "aniseed_tagging"


@tool(
    "Tag Node",
    classification="Rigging",
    categories=["Visibility"],
)
def tag(node: str = "", tag: str = "") -> None:
    """
    Args:
        node: Node to tag
        tag: Tag to apply

    Returns:
        None
    """
    attribute_name = f"{node}.{_TAG_ATTRIBUTE_}"
    if not cmds.objExists(attribute_name):
        cmds.addAttr(
            node,
            shortName=_TAG_ATTRIBUTE_,
            dataType="string",
        )

    existing_tags = get_tags(node)

    if tag in existing_tags:
        print("tag already exists")
        return

    existing_tags.append(tag)
    cmds.setAttr(
        attribute_name,
        ",".join(existing_tags),
        type="string",
    )


@tool(
    "Find First Child With Tag",
    classification="Rigging",
    categories=["Visibility"],
)
def get_first_child(node: str = "", tag: str = "", include_self=False) -> None:

    nodes = cmds.listRelatives(
        node,
        allDescendents=True,
    )

    if include_self:
        nodes.append(node)

    # -- We specifically want to traverse based on depth and not just
    # -- follow branches - so we need to sort this list based on parenting
    # -- depth.
    long_names = [
        cmds.ls(node, long=True)[0]
        for node in nodes
    ]
    long_names = sorted(long_names, key=lambda x: x.count("|"))

    for long_name in long_names:
        local_name = long_name.split("|")[-1]

        if has_tag(local_name, tag):
            return local_name


@tool(
    "Find All Children With Tag",
    classification="Rigging",
    categories=["Visibility"],
)
def all_children(node: str = "", tag: str = "", include_self=False) -> list:

    nodes = cmds.listRelatives(
        node,
        allDescendents=True,
    )

    if include_self:
        nodes.append(node)

    # -- We specifically want to traverse based on depth and not just
    # -- follow branches - so we need to sort this list based on parenting
    # -- depth.
    long_names = [
        cmds.ls(node, long=True)[0]
        for node in nodes
    ]
    long_names = sorted(long_names, key=lambda x: x.count("|"))
    results = []
    for long_name in long_names:
        local_name = long_name.split("|")[-1]

        if has_tag(local_name, tag):
            results.append(local_name)

    return results


@tool(
    "Find All With Tag",
    classification="Rigging",
    categories=["Visibility"],
)
def find_all(tag: str = "", include_self=False) -> None:

    nodes = cmds.ls()


    results = list()
    for node in nodes:
        if has_tag(node, tag):
            results.append(node)

    return results


@tool(
    "Has Tag",
    classification="Rigging",
    categories=["Visibility"],
)
def has_tag(node: str = "", tag: str = "") -> bool:
    existing_tags = get_tags(node)

    if tag in existing_tags:
        return True
    return False


@tool(
    "Get Tag Data",
    classification="Rigging",
    categories=["Visibility"],
)
def get_tags(node: str = "") -> list[str]:

    attribute_name = f"{node}.{_TAG_ATTRIBUTE_}"
    if not cmds.objExists(attribute_name):
        return ""

    return [
        tag
        for tag in (cmds.getAttr(attribute_name) or "").split(",")
        if tag
    ]
