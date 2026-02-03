import maya.cmds as mc

from . import items


def select(item: object or str):
    """
    This should select the given item

    Args:
        item: The item or name of object to be selected
    """
    if isinstance(item, list):
        item = [
            items.get(i)
            for i in item
        ]
    else:
        item = items.get(item)

    mc.select(item)


def selected() -> list[object]:
    """
    This should return the items which are currently selected

    Returns:
        A list of items which are currently selected
    """
    return mc.ls(sl=True) or list()
