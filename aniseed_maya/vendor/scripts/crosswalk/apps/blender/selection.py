import bpy
from . import objects


def select(object_):
    """
    This should select the given object
    """
    object_ = objects.get_object(object_)

    object_.select_set(True)
    bpy.context.view_layer.objects.active = object_


def selected():
    """
    This should return the objects which are currently selected
    """
    return bpy.context.selected_objects
