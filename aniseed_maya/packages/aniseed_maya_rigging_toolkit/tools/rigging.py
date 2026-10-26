"""
Rigging Toolkit tools for building rig mechanisms: twist setups, aligning a
joint chain for ik, and working out spline positions from joints.
"""
import logging

from maya import cmds

import aniseed
import aniseed_toolkit
from aniseed import toolkits

log = logging.getLogger(__name__)


class _DefaultNaming:
    """
    Stands in for an aniseed.RigConfiguration, which the tools are run
    without. It names nodes in the same
    [location]_[classification]_[description]_[##] form as the default rig
    configuration.
    """

    organisational = "org"
    control = "ctrl"
    zero = "zero"
    offset = "off"

    def generate_name(
            self,
            classification: str,
            description: str,
            location: str,
            counter: int = 1,
            unique: bool = True,
    ) -> str:
        while True:
            formatted_counter = str(counter).rjust(2, "0")
            name = f"{location.lower()}_{classification}_{description.lower()}_{formatted_counter}"

            if not unique or not cmds.objExists(name):
                return name
            counter += 1


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
        positions = aniseed_toolkit.core.maths.calculate_four_point_spline_positions(
            nodes=self._joints(),
        )
        log.info(f"Spline positions: {positions}")


# --------------------------------------------------------------------------------------
class CreateTwist(toolkits.Tool):
    """
    Creates a twist setup: an org holding a root and a tip control, with
    Twist Count twist controls between them which blend from the root to the
    tip. Description and Location are used in the node names.
    """

    identifier = "Create Twist Setup"
    toolkit = "Rigging"
    categories = ["Rigging"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Twist Count",
            value=3,
            description="The number of twist controls to create",
        )

        self.declare_option(
            name="Description",
            value="",
            description="The description used in all the node names",
        )

        self.declare_option(
            name="Location",
            value="",
            description="The location (side) used in all the node names",
        )

    def run(self) -> None:
        twist_setup = aniseed_toolkit.rigging.twist.create_twist_setup(
            twist_count=self.option("Twist Count").get(),
            description=self.option("Description").get(),
            location=self.option("Location").get(),
            config=_DefaultNaming(),
        )
        log.info(f"Created twist setup {twist_setup.org()}")


# --------------------------------------------------------------------------------------
class AlignBonesForIk(toolkits.Tool):
    """
    Aligns the bones of a chain, from Root down to Tip, so each faces down
    Primary Axis with Polevector Axis facing the pole vector. Every joint,
    including the tip, is aligned. If Root and Tip are not given, select the
    root and then the tip.

    Retain Child Transforms keeps the world transforms of any children which
    are not part of the chain (twist joints are re-positioned along their
    bone). Pinned joints are unpinned while aligning and pinned again after.
    """

    identifier = "Align Bones For Ik"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Root",
            value="",
            description="The joint to start aligning from (the first selected joint if not given)",
        )

        self.declare_option(
            name="Tip",
            value="",
            description="The joint to stop aligning at (the second selected joint if not given)",
        )

        self.declare_option(
            name="Primary Axis",
            value="positive x",
            description="The axis which runs down each bone",
        )

        self.declare_option(
            name="Polevector Axis",
            value="positive y",
            description="The axis which faces the pole vector",
        )

        self.declare_option(
            name="Retain Child Transforms",
            value=True,
            description="Whether to keep the world transforms of children which are not part of the chain",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Root", "Tip"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        if option_name in ["Primary Axis", "Polevector Axis"]:
            return aniseed.widgets.ItemSelector(
                items=aniseed_toolkit.rigging.bone_alignment.AXIS_LABELS,
                default_item=self.option(option_name).get(),
            )

        return None

    def is_valid(self) -> bool:
        selection_count = len(cmds.ls(selection=True))

        if not self.option("Root").get() and selection_count != 2:
            log.warning("Set Root (or select the root and then the tip)")
            return False

        if not self.option("Tip").get() and selection_count != 2:
            log.warning("Set Tip (or select the root and then the tip)")
            return False

        labels = aniseed_toolkit.rigging.bone_alignment.AXIS_LABELS
        primary_axis = self.option("Primary Axis").get()
        polevector_axis = self.option("Polevector Axis").get()

        if primary_axis not in labels or polevector_axis not in labels:
            log.warning(f"Primary Axis and Polevector Axis must each be one of {labels}")
            return False

        if primary_axis[-1] == polevector_axis[-1]:
            log.warning("Polevector Axis must be a different axis to Primary Axis")
            return False

        return True

    def run(self) -> None:
        pre_selection = cmds.ls(selection=True)

        aniseed_toolkit.rigging.bone_alignment.align_bones_for_ik(
            root=self.option("Root").get() or pre_selection[0],
            tip=self.option("Tip").get() or pre_selection[1],
            primary_axis=self.option("Primary Axis").get(),
            polevector_axis=self.option("Polevector Axis").get(),
            retain_child_transforms=self.option("Retain Child Transforms").get(),
        )

        cmds.select(pre_selection)
