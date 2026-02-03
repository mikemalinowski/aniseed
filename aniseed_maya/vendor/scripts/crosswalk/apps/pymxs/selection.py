from pymxs import runtime as rt

from . import items


def select(item: object or str):
    """
    This should select the given item

    Args:
        item: The item or name of object to be selected
    """
    node = items.get(item)

    if node:
        rt.select(node)


def selected() -> list[object]:
    """
    This should return the items which are currently selected

    Returns:
        A list of items which are currently selected
    """
    return rt.selection
