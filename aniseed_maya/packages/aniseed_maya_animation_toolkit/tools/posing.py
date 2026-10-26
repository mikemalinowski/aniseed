"""
Animation Toolkit tools for copying a pose from some controls and pasting it
onto others, in local or world space.
"""
import logging

from maya import cmds

from aniseed import toolkits

log = logging.getLogger(__name__)


def _copy(clipboard_name: str, world_space: bool) -> None:
    """
    Stores the matrices of the selected nodes, in selection order.
    """
    clipboard = toolkits.clipboard(clipboard_name)
    clipboard["matrices"] = [
        cmds.xform(node, query=True, matrix=True, worldSpace=world_space)
        for node in cmds.ls(selection=True)
    ]


def _paste(clipboard_name: str, world_space: bool) -> None:
    """
    Applies the stored matrices to the selected nodes, in the order they
    were copied. Extra nodes (or matrices) are ignored.
    """
    matrices = toolkits.clipboard(clipboard_name).get("matrices") or []

    for node, matrix in zip(cmds.ls(selection=True), matrices):
        cmds.xform(node, matrix=matrix, worldSpace=world_space)


def _can_paste(clipboard_name: str, copy_tool: str) -> bool:
    if not toolkits.clipboard(clipboard_name).get("matrices"):
        log.warning(f"Copy a pose with {copy_tool} first")
        return False

    if not cmds.ls(selection=True):
        log.warning("Select the controls to paste the pose onto, in the order it was copied")
        return False

    return True


def _can_copy() -> bool:
    if not cmds.ls(selection=True):
        log.warning("Select the controls to copy the pose of")
        return False

    return True


# --------------------------------------------------------------------------------------
class PoseCopy(toolkits.Tool):
    """
    Remembers the local space transforms of the selected controls, for Pose
    Paste to apply to other controls (in the same order).
    """

    identifier = "Pose Copy"
    toolkit = "Animation"
    categories = ["Posing"]

    def is_valid(self) -> bool:
        return _can_copy()

    def run(self) -> None:
        _copy("Pose", world_space=False)


# --------------------------------------------------------------------------------------
class PosePaste(toolkits.Tool):
    """
    Applies the local space transforms copied with Pose Copy to the selected
    controls, in the order they were copied.
    """

    identifier = "Pose Paste"
    toolkit = "Animation"
    categories = ["Posing"]

    def is_valid(self) -> bool:
        return _can_paste("Pose", "Pose Copy")

    def run(self) -> None:
        _paste("Pose", world_space=False)


# --------------------------------------------------------------------------------------
class PoseCopyWorldSpace(toolkits.Tool):
    """
    Remembers the world space transforms of the selected controls, for Pose
    Paste (WorldSpace) to apply to other controls (in the same order).
    """

    identifier = "Pose Copy (WorldSpace)"
    toolkit = "Animation"
    categories = ["Posing"]

    def is_valid(self) -> bool:
        return _can_copy()

    def run(self) -> None:
        _copy("Pose (WorldSpace)", world_space=True)


# --------------------------------------------------------------------------------------
class PosePasteWorldSpace(toolkits.Tool):
    """
    Applies the world space transforms copied with Pose Copy (WorldSpace) to
    the selected controls, in the order they were copied.
    """

    identifier = "Pose Paste (WorldSpace)"
    toolkit = "Animation"
    categories = ["Posing"]

    def is_valid(self) -> bool:
        return _can_paste("Pose (WorldSpace)", "Pose Copy (WorldSpace)")

    def run(self) -> None:
        _paste("Pose (WorldSpace)", world_space=True)
