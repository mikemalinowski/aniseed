import pyfbsdk as mobu

from . import objects


def select(object_):
    """
    This should select the given object
    """
    object_ = objects.get_object(object_)

    for comp in mobu.FBSystem().Scene.Components:
        comp.Selected = comp == object_


def selected():
    """
    This should return the objects which are currently selected
    """
    results = mobu.FBModelList()

    mobu.FBGetSelectedModels(
        results,
        None,  # -- Search all hierarchies
        True,  # -- Return if they are selected
        True,  # -- Sort by selection order
    )

    return results
