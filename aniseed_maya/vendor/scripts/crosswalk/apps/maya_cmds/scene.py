import os
import maya.cmds as mc


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
    return mc.file(q=True, sn=True)


def save():
    """
    Instigates a save of the current scene to the current filepath
    """
    return mc.file(save=True)


def save_as(filepath: str):
    """
    This will save the active scene to the given filepath

    Args:
        filepath: The filepath to save the scene to
    """
    mc.file(rename=filepath)

    file_type = "mayaAscii"
    if filepath.lower().endswith(".mb"):
        file_type = "mayaBinary"

    return mc.file(
        save=True,
        type=file_type,
    )


def load(filepath: str, force: bool = False):
    """
    This will open the given filepath as the active scene

    Args:
        filepath: The absolute path to the file to open
        force: If true no prompt will be shown.
    """
    return mc.file(
        filepath,
        open=True,
        force=force,
    )
