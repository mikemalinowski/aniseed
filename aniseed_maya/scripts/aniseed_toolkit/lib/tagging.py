from maya import cmds
import aniseed_toolkit

_TAG_ATTRIBUTE_ = "aniseed_tagging"


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

    existing_tags = aniseed_toolkit.run(
        "Get Tag Data",
        node=node,
    )

    if tag in existing_tags:
        print("tag already exists")
        return

    existing_tags.append(tag)
    cmds.setAttr(
        attribute_name,
        ",".join(existing_tags),
        type="string",
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

        if aniseed_toolkit.run("Has Tag", node=local_name, tag=tag):
            return local_name


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

        if aniseed_toolkit.run("Has Tag", node=local_name, tag=tag):
            results.append(local_name)

    return results


def find_all(tag: str = "", include_self=False) -> None:

    nodes = cmds.ls()


    results = list()
    for node in nodes:
        if aniseed_toolkit.run("Has Tag", node=node):
            results.append(node)

    return results


def has_tag(node: str = "", tag: str = "") -> bool:
    existing_tags = aniseed_toolkit.run(
        "Get Tag Data",
        node=node,
    )

    if tag in existing_tags:
        return True
    return False


def get_tags(node: str = "") -> list[str]:

    attribute_name = f"{node}.{_TAG_ATTRIBUTE_}"
    if not cmds.objExists(attribute_name):
        return ""

    return [
        tag
        for tag in (cmds.getAttr(attribute_name) or "").split(",")
        if tag
    ]
