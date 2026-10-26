"""
Animation Toolkit tools for a rig's controls: selecting and zeroing them.
"""
import logging

from maya import cmds

import aniseed_toolkit
from aniseed import toolkits

log = logging.getLogger(__name__)


def _rig_controls(namespace: str) -> list or None:
    """
    Returns the controls of the rig to work on (see
    aniseed_toolkit.rig.rig_controls), logging a warning if the selection is
    not part of a rig.
    """
    controls = aniseed_toolkit.rig.rig_controls(namespace)

    if controls is None:
        log.warning("The selection is not part of an aniseed rig")

    return controls


# --------------------------------------------------------------------------------------
class SelectControls(toolkits.Tool):
    """
    Selects every control of a rig: the rig the first selected node belongs
    to, or every aniseed rig in the scene if nothing is selected. Give a
    Namespace to select the controls of the rig in that namespace instead.
    """

    identifier = "Select Controls"
    toolkit = "Animation"
    categories = ["Selection", "Controls"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Namespace",
            value="",
            description="The namespace of the rig to select, used instead of the selection when given",
        )

    def is_valid(self) -> bool:
        return _rig_controls(self.option("Namespace").get()) is not None

    def run(self) -> None:
        cmds.select(_rig_controls(self.option("Namespace").get()))


# --------------------------------------------------------------------------------------
class SelectAlternateControls(toolkits.Tool):
    """
    Selects the alternate of every rig control whose name contains Replace
    This: the control with Replace This replaced by With This, where one
    exists. For instance, the right side controls of the left side ones.
    """

    identifier = "Select Alternate Controls"
    toolkit = "Animation"
    categories = ["Selection", "Controls"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Replace This",
            value="_LF",
            description="The part of the control names to replace",
        )

        self.declare_option(
            name="With This",
            value="_RT",
            description="What to replace it with",
        )

    def run(self) -> None:
        replace_this = self.option("Replace This").get()
        with_this = self.option("With This").get()

        alternates = []

        for control in aniseed_toolkit.rig.all_controls():
            if replace_this not in control:
                continue

            alternate = control.replace(replace_this, with_this)
            if cmds.objExists(alternate):
                alternates.append(alternate)

        cmds.select(alternates)


# --------------------------------------------------------------------------------------
class SelectFilteredControls(toolkits.Tool):
    """
    Selects every rig control whose name contains Name Filter.
    """

    identifier = "Select Filtered Controls"
    toolkit = "Animation"
    categories = ["Selection", "Controls"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Name Filter",
            value="_LF",
            description="The text the control names must contain",
        )

    def run(self) -> None:
        name_filter = self.option("Name Filter").get()

        cmds.select(
            [
                control
                for control in aniseed_toolkit.rig.all_controls()
                if name_filter in control
            ]
        )


# --------------------------------------------------------------------------------------
class SelectControlsByLocation(toolkits.Tool):
    """
    Selects every rig control which shares the location (side) of the first
    selected control.
    """

    identifier = "Select Controls By Location"
    toolkit = "Animation"
    categories = ["Selection", "Controls"]

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select a control to select the controls of its location")
            return False

        return True

    def run(self) -> None:
        cmds.select(aniseed_toolkit.rig.controls_by_location(cmds.ls(selection=True)))


# --------------------------------------------------------------------------------------
class SelectOpposite(toolkits.Tool):
    """
    Selects the controls of the opposing location (side) to the selected
    controls. Opposites which do not exist are skipped.
    """

    identifier = "Select Opposite"
    toolkit = "Animation"
    categories = ["Selection", "Controls"]

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the controls to find the opposites of")
            return False

        return True

    def run(self) -> None:
        opposites = [
            opposite
            for opposite in aniseed_toolkit.rig.opposing_controls(cmds.ls(selection=True))
            if cmds.objExists(opposite)
        ]

        if not opposites:
            log.warning("No opposite controls were found for the selection")
            return

        cmds.select(opposites)


# --------------------------------------------------------------------------------------
class ZeroSelection(toolkits.Tool):
    """
    Zeros out the animatable channels of the selected controls: translation
    and rotation are set to zero, scale to one, and keyable user defined
    attributes to their defaults. Turn on Key On Reset to key the controls
    afterwards.
    """

    identifier = "Zero Selection"
    toolkit = "Animation"
    categories = ["Selection", "Controls"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Key On Reset",
            value=False,
            description="Whether to key the controls after zeroing them",
        )

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the controls to zero")
            return False

        return True

    def run(self) -> None:
        for node in cmds.ls(selection=True):
            control = aniseed_toolkit.rig.control.get(node)

            if not control:
                continue

            aniseed_toolkit.rig.zero(control.ctl)

            if self.option("Key On Reset").get():
                cmds.setKeyframe(control.ctl)


# --------------------------------------------------------------------------------------
class ZeroRig(toolkits.Tool):
    """
    Zeros out the animatable channels of every control of a rig: the rig the
    first selected node belongs to, or every aniseed rig in the scene if
    nothing is selected. Give a Namespace to zero the rig in that namespace
    instead. Turn on Key On Reset to key the controls afterwards.
    """

    identifier = "Zero Rig"
    toolkit = "Animation"
    categories = ["Selection", "Controls"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Key On Reset",
            value=False,
            description="Whether to key the controls after zeroing them",
        )

        self.declare_option(
            name="Namespace",
            value="",
            description="The namespace of the rig to zero, used instead of the selection when given",
        )

    def is_valid(self) -> bool:
        return _rig_controls(self.option("Namespace").get()) is not None

    def run(self) -> None:
        for control in _rig_controls(self.option("Namespace").get()):
            aniseed_toolkit.rig.zero(control)

            if self.option("Key On Reset").get():
                cmds.setKeyframe(control)
