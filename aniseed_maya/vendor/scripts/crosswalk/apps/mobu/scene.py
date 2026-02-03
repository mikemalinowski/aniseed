import os
from pyfbsdk import *


def name() -> str:
    """
    This will return the name of the active scene

    Returns:
        The name (not including suffix) of the scene
    """
    return ".".join(os.path.basename(path()).split(".")[:-1])

def path() -> str:
    """
    Returns the absolute path to the current scene.

    Returns:
        The absolute path to the current scene
    """
    app = FBApplication()
    return app.FBXFileName


def save():
    """
    Instigates a save of the current scene to the current filepath
    """
    save_as(path())


def save_as(filepath: str):
    """
    This will save the active scene to the given filepath

    Args:
        filepath: The filepath to save the scene to
    """
    app = FBApplication()
    app.FileSave(filepath)


def load(filepath: str, force: bool = False):
    """
    This will open the given filepath as the active scene

    Args:
        filepath: The absolute path to the file to open
        force: If true no prompt will be shown.
    """
    app = FBApplication()
    show_ui = not force
    app.FileOpen(filepath, show_ui)
    return
