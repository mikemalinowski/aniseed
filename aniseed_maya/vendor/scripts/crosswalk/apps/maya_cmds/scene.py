import os
import maya.cmds as mc


def name():
    return ".".join(os.path.basename(path()).split(".")[:-1])


def path():
    return mc.file(q=True, sn=True)


def save():
    return mc.file(save=True)


def save_as(filepath):
    mc.file(rename=filepath)

    file_type = "mayaAscii"
    if filepath.lower().endswith(".mb"):
        file_type = "mayaBinary"

    return mc.file(
        save=True,
        type=file_type,
    )


def open(filepath, force=False):
    return mc.file(
        filepath,
        open=True,
        force=force,
    )
