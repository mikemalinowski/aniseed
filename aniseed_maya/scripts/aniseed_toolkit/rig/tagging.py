"""
Tagging nodes with string tags, and finding nodes by tag.

The tags are stored as a comma separated string in an aniseed_tagging
attribute. Node names are returned exactly as maya reports them, so the
queries which return node names use cmds rather than mref.
"""
import logging

from maya import cmds
import mref

from ..registry import tool
from ..core._nodes import resolve as _resolve


_TAG_ATTRIBUTE_ = "aniseed_tagging"

log = logging.getLogger(__name__)


@tool(
    "Tag Node",
    classification="Rigging",
    categories=["Tagging"],
)
def tag(node: str = "", tag: str = "") -> None:
    """
    Adds the given tag to the node, creating the tagging attribute if
    needed. If the node already has the tag, a message is logged and
    nothing is changed.

    Args:
        node: Node to tag
        tag: Tag to apply

    Returns:
        None
    """
    attribute_name = f"{node}.{_TAG_ATTRIBUTE_}"
    if not mref.objExists(attribute_name):
        mref.addAttr(
            node,
            shortName=_TAG_ATTRIBUTE_,
            dataType="string",
        )

    existing_tags = get_tags(node)

    if tag in existing_tags:
        log.info(f"{node} is already tagged with {tag}")
        return

    existing_tags.append(tag)
    mref.setAttr(
        attribute_name,
        ",".join(existing_tags),
        type="string",
    )


def _descendants_by_depth(node: str, include_self: bool) -> list[str]:
    """
    Returns the short names of all the descendants of the node (and the
    node itself if include_self is True), sorted by their depth in the
    hierarchy - shallowest first.
    """
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

    return [long_name.split("|")[-1] for long_name in long_names]


@tool(
    "Find First Child With Tag",
    classification="Rigging",
    categories=["Tagging"],
)
def get_first_child(node: str = "", tag: str = "", include_self=False) -> None:
    """
    Returns the shallowest descendant of the node which has the given tag.
    The node must have at least one child (an error is raised otherwise).

    Args:
        node: The node to search beneath
        tag: The tag to look for
        include_self: If True the node itself is also considered

    Returns:
        The short name of the first node with the tag, or None if there is
        none.
    """
    for local_name in _descendants_by_depth(node, include_self):
        if has_tag(local_name, tag):
            return local_name


@tool(
    "Find All Children With Tag",
    classification="Rigging",
    categories=["Tagging"],
)
def all_children(node: str = "", tag: str = "", include_self=False) -> list:
    """
    Returns all the descendants of the node which have the given tag,
    shallowest first. The node must have at least one child (an error is
    raised otherwise).

    Args:
        node: The node to search beneath
        tag: The tag to look for
        include_self: If True the node itself is also considered

    Returns:
        The short names of the nodes with the tag
    """
    return [
        local_name
        for local_name in _descendants_by_depth(node, include_self)
        if has_tag(local_name, tag)
    ]


@tool(
    "Find All With Tag",
    classification="Rigging",
    categories=["Tagging"],
)
def find_all(tag: str = "", include_self=False) -> None:
    """
    Returns every node in the scene which has the given tag.

    Args:
        tag: The tag to look for
        include_self: Not used

    Returns:
        The names of the nodes with the tag
    """
    return [
        node
        for node in cmds.ls()
        if has_tag(node, tag)
    ]


@tool(
    "Has Tag",
    classification="Rigging",
    categories=["Tagging"],
)
def has_tag(node: str = "", tag: str = "") -> bool:
    """
    Returns True if the node has the given tag.

    Args:
        node: The node to test
        tag: The tag to look for
    """
    existing_tags = get_tags(node)

    if tag in existing_tags:
        return True
    return False


@tool(
    "Get Tag Data",
    classification="Rigging",
    categories=["Tagging"],
)
def get_tags(node: str = "") -> list[str]:
    """
    Returns the tags of the node.

    Args:
        node: The node to read the tags from

    Returns:
        The list of tags. Note that an empty string (not a list) is
        returned if the node has never been tagged.
    """
    attribute_name = f"{node}.{_TAG_ATTRIBUTE_}"
    if not mref.objExists(attribute_name):
        return ""

    # -- Attribute.get rather than the getAttr passthrough, which would turn
    # -- a tag string matching a node name into a node
    return [
        tag
        for tag in (_resolve(attribute_name).get() or "").split(",")
        if tag
    ]
