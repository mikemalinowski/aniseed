"""
Rigging Toolkit tools for building rig mechanisms: working out spline
positions from joints. The twist and ik alignment tools are in
aniseed_standard/tools/rigging.py, as they use aniseed_standard.rigging.
"""
import logging

from maya import cmds

import aniseed
import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
class CalculateFourPointSplineFromJoints(toolkits.Tool):
    """
    Logs the four control point positions of a single span cubic curve
    which follows the given joints (in order), for building a bezier spline
    which keeps the joints' transforms. Uses the selected joints when Joints
    is empty.
    """

    identifier = "Calculate Four Spline Positions From Joints"
    toolkit = "Rigging"
    categories = ["Rigging"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Joints",
            value=[],
            description="The joints (in order) the spline follows. The selection is used if empty",
        )

    def option_widget(self, option_name: str):
        if option_name == "Joints":
            # -- The options ui applies the value itself, and ObjectList
            # -- appends what it is given, so it is created empty
            return aniseed.widgets.ObjectList()
        return None

    def _joints(self) -> list:
        return list(self.option("Joints").get() or []) or cmds.ls(selection=True)

    def is_valid(self) -> bool:
        if len(self._joints()) < 2:
            log.warning("Set Joints (or select the joints, in order) to calculate the spline positions from")
            return False

        return True

    def run(self) -> None:
        positions = au.core.maths.calculate_four_point_spline_positions(
            nodes=self._joints(),
        )
        log.info(f"Spline positions: {positions}")
