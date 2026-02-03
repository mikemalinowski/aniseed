import bpy
from . import items


def select(item: object or str):
    """
    This should select the given item

    Args:
        item: The item or name of object to be selected
    """
    item = items.get(item)

    item.select_set(True)
    bpy.context.view_layer.objects.active = item


def selected() -> list[object]:
    """
    This should return the items which are currently selected

    Returns:
        A list of items which are currently selected
    """
    return bpy.context.selected_objects
