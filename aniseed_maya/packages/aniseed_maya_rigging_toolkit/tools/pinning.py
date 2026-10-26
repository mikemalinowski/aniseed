"""
Rigging Toolkit tools for pinning joints: holding them in place with world
space pin controls so they can be moved without affecting their children,
and removing those pins again.
"""
import logging

from maya import cmds

import aniseed_toolkit
from aniseed import toolkits

log = logging.getLogger(__name__)


def _requires_selection(message: str) -> bool:
    if not cmds.ls(selection=True):
        log.warning(message)
        return False

    return True


# --------------------------------------------------------------------------------------
class CreatePins(toolkits.Tool):
    """
    Pins the selected joints: each gets a world space pin control (with an
    offset) which holds the joint in place, making it easy to move a joint
    without altering its children. The last pin created is left selected.
    """

    identifier = "Create Pins"
    toolkit = "Rigging"
    categories = ["Pinning"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the joints to pin")

    def run(self) -> None:
        pins = aniseed_toolkit.rig.pinning.pin(cmds.ls(selection=True))
        log.info(f"Created {pins}")


# --------------------------------------------------------------------------------------
class PinHierarchy(toolkits.Tool):
    """
    Pins the first selected joint and every joint below it (see Create
    Pins).
    """

    identifier = "Pin Hierarchy"
    toolkit = "Rigging"
    categories = ["Pinning"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the joint at the top of the hierarchy to pin")

    def run(self) -> None:
        pins = aniseed_toolkit.rig.pinning.pin_hierarchy(cmds.ls(selection=True)[0])
        log.info(f"Created {pins}")


# --------------------------------------------------------------------------------------
class RemovePins(toolkits.Tool):
    """
    Removes the pins of the selection: select the pins, their offsets or the
    pinned joints. Each joint keeps the transform it had when its pin was
    removed.
    """

    identifier = "Remove Pins"
    toolkit = "Rigging"
    categories = ["Pinning"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the pins (or pinned joints) to remove")

    def run(self) -> None:
        aniseed_toolkit.rig.pinning.remove_pins(cmds.ls(selection=True))


# --------------------------------------------------------------------------------------
class RemoveAllPins(toolkits.Tool):
    """
    Removes every pin in the scene. Each joint keeps the transform it had
    when its pin was removed.
    """

    identifier = "Remove All Pins"
    toolkit = "Rigging"
    categories = ["Pinning"]

    def run(self) -> None:
        aniseed_toolkit.rig.pinning.remove_all_pins()
