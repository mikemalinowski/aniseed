import aniseed_toolkit

_TAG_ATTRIBUTE_ = "aniseed_tagging"


class TagNode(aniseed_toolkit.Tool):

    identifier = "Tag Node"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, node: str = "", tag: str = "") -> None:
        """
        Args:
            node: Node to tag
            tag: Tag to apply

        Returns:
            None
        """
        return aniseed_toolkit.tagging.tag(node, tag)


class FindChildWithTag(aniseed_toolkit.Tool):

    identifier = "Find First Child With Tag"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, node: str = "", tag: str = "", include_self=False) -> None:
        return aniseed_toolkit.tagging.get_first_child(node, tag, include_self)


class FindAllChildrenWithTag(aniseed_toolkit.Tool):
    identifier = "Find All Children With Tag"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, node: str = "", tag: str = "", include_self=False) -> None:
        return aniseed_toolkit.tagging.all_children(
            node,
            tag,
            include_self,
        )

class FindAllWithTag(aniseed_toolkit.Tool):
    identifier = "Find All With Tag"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, tag: str = "", include_self=False) -> None:
        return aniseed_toolkit.tagging.find_all(
            tag,
            include_self=include_self,
        )


class HasTagTool(aniseed_toolkit.Tool):

    identifier = "Has Tag"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, node: str = "", tag: str = "") -> bool:
        return aniseed_toolkit.tagging.has_tag(node, tag)


class GetTagData(aniseed_toolkit.Tool):


    identifier = "Get Tag Data"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]
    def run(self, node: str = "") -> list[str]:
        return aniseed_toolkit.tagging.get_tags(node)
