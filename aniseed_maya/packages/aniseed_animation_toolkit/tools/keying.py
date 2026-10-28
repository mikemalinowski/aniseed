"""
Animation Toolkit tools for keying controls, and for matching a limb's ik and
fk controls (through the snappy groups aniseed's limbs set up).
"""
import logging

import mref
import snappy
from maya import cmds

import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)


def _snap_groups(nodes: list) -> list:
    """
    Returns the snappy groups the given nodes belong to.
    """
    groups = []

    for node in nodes:
        groups.extend(snappy.groups(node))

    return sorted(set(groups))


def _ikfk_group(nodes: list) -> str or None:
    """
    Returns the ikfk snappy group of the limb the given nodes belong to, or
    None.
    """
    for group in _snap_groups(nodes):
        if "IKFK" in group:
            return group

    return None


def _snap(nodes: list, tag: str) -> None:
    """
    Snaps the snappy groups (of the given nodes) whose name contains the tag,
    over the selected frame range of the time slider if more than one frame
    is selected, otherwise at the current frame.
    """
    start_time = None
    end_time = None

    if mref.time.selected_number_of_frames() > 1:
        start_time = mref.time.selected_start_frame()
        end_time = mref.time.selected_end_frame()

    for group in _snap_groups(nodes):
        if tag in group:
            snappy.snap(
                group=group,
                start_time=start_time,
                end_time=end_time,
            )


def _requires_selection(message: str) -> bool:
    if not cmds.ls(selection=True):
        log.warning(message)
        return False

    return True


def _requires_ikfk_limb() -> bool:
    if not _requires_selection("Select a control of the limb"):
        return False

    if not _ikfk_group(cmds.ls(selection=True)):
        log.warning("Could not find an ikfk group for the selection")
        return False

    return True


# --------------------------------------------------------------------------------------
class KeyAllRigControls(toolkits.Tool):
    """
    Keys every control of the rig the first selected node belongs to, or of
    every aniseed rig in the scene if nothing is selected.
    """

    identifier = "Key All Rig Controls"
    toolkit = "Animation"
    categories = ["Keys", "Controls"]

    def is_valid(self) -> bool:
        if au.rig.rig_controls() is None:
            log.warning("The selection is not part of an aniseed rig")
            return False

        return True

    def run(self) -> None:
        controls = au.rig.rig_controls()

        if controls:
            cmds.setKeyframe(controls)


# --------------------------------------------------------------------------------------
class SnapIkToFk(toolkits.Tool):
    """
    Matches the ik controls of the selected limb to its fk controls. If more
    than one frame is selected in the time slider, it is matched (and keyed)
    on every frame of that range.
    """

    identifier = "Snap Ik To Fk (Selected Limb)"
    toolkit = "Animation"
    categories = ["Keys", "Controls"]

    def is_valid(self) -> bool:
        return _requires_selection("Select a control of the limb to snap")

    def run(self) -> None:
        _snap(cmds.ls(selection=True), "IKOnly")


# --------------------------------------------------------------------------------------
class SnapFkToIk(toolkits.Tool):
    """
    Matches the fk controls of the selected limb to its ik controls. If more
    than one frame is selected in the time slider, it is matched (and keyed)
    on every frame of that range.
    """

    identifier = "Snap Fk To Ik (Selected Limb)"
    toolkit = "Animation"
    categories = ["Keys", "Controls"]

    def is_valid(self) -> bool:
        return _requires_selection("Select a control of the limb to snap")

    def run(self) -> None:
        _snap(cmds.ls(selection=True), "FKOnly")


# --------------------------------------------------------------------------------------
class SwitchIkfk(toolkits.Tool):
    """
    Switches the selected limb between ik and fk, matching the controls it
    switches to onto the pose of the ones it switches from, so the limb does
    not move.
    """

    identifier = "Switch IKFK (Selected Limb)"
    toolkit = "Animation"
    categories = ["Keys", "Controls"]

    def is_valid(self) -> bool:
        return _requires_ikfk_limb()

    def run(self) -> None:
        nodes = cmds.ls(selection=True)

        namespace = ""
        if ":" in nodes[0]:
            namespace = nodes[0].split(":")[0] + ":"

        ikfk_attribute = snappy.get_data(_ikfk_group(nodes), "ikfk_attribute")
        ikfk_address = f"{namespace}{ikfk_attribute}"

        if cmds.getAttr(ikfk_address) > 0.001:
            log.info("Switching to ik")
            _snap(nodes, "IKOnly")
            cmds.setAttr(ikfk_address, 0.0)

        else:
            log.info("Switching to fk")
            _snap(nodes, "FKOnly")
            cmds.setAttr(ikfk_address, 1.0)


# --------------------------------------------------------------------------------------
class MatchIkfkOverTime(toolkits.Tool):
    """
    Matches the selected limb's ik and fk controls on every frame of the
    range selected in the time slider.
    """

    identifier = "Match IKFK Over Time (Selected Limb)"
    toolkit = "Animation"
    categories = ["Keys", "Controls"]

    def is_valid(self) -> bool:
        return _requires_ikfk_limb()

    def run(self) -> None:
        snappy.snap_over_time(
            group=_ikfk_group(cmds.ls(selection=True)),
            start_time=mref.time.selected_start_frame(),
            end_time=mref.time.selected_end_frame(),
        )
