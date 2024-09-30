import maya.cmds as mc

from . import objects


def select(object_):
    """
    This should select the given object
    """
    mc.select(objects.get_name(object_))


def selected():
    """
    This should return the objects which are currently selected
    """
    return mc.ls(sl=True) or list()
