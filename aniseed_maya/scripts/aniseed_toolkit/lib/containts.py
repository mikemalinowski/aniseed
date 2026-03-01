from maya import cmds


def remove_all(nodes: list[str] = ""):
    for node in nodes:
        for child in cmds.listRelatives(node, children=True) or list():
            if "constraint" in cmds.nodeType(child).lower():
                cmds.delete(child)
