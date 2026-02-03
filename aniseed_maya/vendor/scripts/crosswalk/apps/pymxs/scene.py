import os
from pymxs import runtime as rt


def name() -> str:
    """
    This will return the name of the active scene

    Returns:
        The name (not including suffix) of the scene
    """
    return rt.maxFileName


def path() -> str:
    """
    Returns the absolute path to the current scene.

    Returns:
        The absolute path to the current scene
    """
    return os.path.join(
        rt.maxFilePath,
        rt.maxFileName,
    )


def save():
    """
    Instigates a save of the current scene to the current filepath
    """
    return rt.saveMaxFile()


def save_as(filepath: str):
    """
    This will save the active scene to the given filepath

    Args:
        filepath: The filepath to save the scene to
    """
    return rt.saveMaxFile(filepath)


def load(filepath: str, force: bool = False):
    """
    This will open the given filepath as the active scene

    Args:
        filepath: The absolute path to the file to open
        force: If true no prompt will be shown.
    """
    return rt.loadMaxFile(
        filepath,
        quiet=force,
    )
