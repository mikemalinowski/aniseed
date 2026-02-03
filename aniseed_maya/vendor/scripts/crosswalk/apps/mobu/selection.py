import pyfbsdk as mobu

from . import items


def select(item: object or str):
    """
    This should select the given item

    Args:
        item: The item or name of object to be selected
    """
    item = items.get(item)

    for comp in mobu.FBSystem().Scene.Components:
        comp.Selected = comp == item


def selected() -> list[object]:
    """
    This should return the items which are currently selected

    Returns:
        A list of items which are currently selected
    """
    results = mobu.FBModelList()

    mobu.FBGetSelectedModels(
        results,
        None,  # -- Search all hierarchies
        True,  # -- Return if they are selected
        True,  # -- Sort by selection order
    )

    return results
