import maya.cmds as mc
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
        attribute_name = f"{node}.{_TAG_ATTRIBUTE_}"
        if not mc.objExists(attribute_name):
            mc.addAttr(
                node,
                shortName=_TAG_ATTRIBUTE_,
                dataType="string",
            )

        existing_tags = aniseed_toolkit.run(
            "Get Tag Data",
            node=node,
        )

        if tag in existing_tags:
            return

        existing_tags.append(tag)
        mc.setAttr(
            attribute_name,
            ",".join(existing_tags),
            type="string",
        )


class FindChildWithTag(aniseed_toolkit.Tool):

    identifier = "Find First Child With Tag"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, node: str = "", tag: str = "", include_self=False) -> None:

        nodes = mc.listRelatives(
            node,
            allDescendents=True,
        )

        if include_self:
            nodes.append(node)

        # -- We specifically want to traverse based on depth and not just
        # -- follow branches - so we need to sort this list based on parenting
        # -- depth.
        long_names = [
            mc.ls(node, long=True)[0]
            for node in nodes
        ]
        long_names = sorted(long_names, key=lambda x: x.count("|"))

        for long_name in long_names:
            local_name = long_name.split("|")[-1]

            if aniseed_toolkit.run("Has Tag", node=local_name, tag=tag):
                return local_name


class FindAllChildrenWithTag(aniseed_toolkit.Tool):
    identifier = "Find All Children With Tag"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, node: str = "", tag: str = "", include_self=False) -> None:

        nodes = mc.listRelatives(
            node,
            allDescendents=True,
        )

        if include_self:
            nodes.append(node)

        results = list()
        for node in nodes:
            if aniseed_toolkit.run("Has Tag", node=node):
                results.append(node)

        return results


class FindAllWithTag(aniseed_toolkit.Tool):
    identifier = "Find All With Tag"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, tag: str = "", include_self=False) -> None:

        nodes = mc.ls()


        results = list()
        for node in nodes:
            if aniseed_toolkit.run("Has Tag", node=node):
                results.append(node)

        return results


class HasTagTool(aniseed_toolkit.Tool):

    identifier = "Has Tag"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, node: str = "", tag: str = "") -> bool:
        existing_tags = aniseed_toolkit.run(
            "Get Tag Data",
            node=node,
        )

        if tag in existing_tags:
            print(f"{tag} is indeed in {existing_tags}")
            return True
        return False


class GetTagData(aniseed_toolkit.Tool):


    identifier = "Get Tag Data"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]
    def run(self, node: str = "") -> list[str]:

        attribute_name = f"{node}.{_TAG_ATTRIBUTE_}"
        if not mc.objExists(attribute_name):
            return ""

        return [
            tag
            for tag in (mc.getAttr(attribute_name) or "").split(",")
            if tag
        ]
