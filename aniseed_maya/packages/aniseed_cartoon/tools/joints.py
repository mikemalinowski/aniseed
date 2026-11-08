"""
Rigging Toolkit tools for joints which the cartoon components use, such as
spreading twist joints along a bone.
"""
import logging

from maya import cmds
from maya.api import OpenMaya as om

import aniseed
from aniseed import toolkits

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
class DistributeTwistJoints(toolkits.Tool):
    """
    Spreads the Twist Joints evenly along the bone from Root to Child, along
    Root's down-the-bone axis (the local axis of Root that points most
    towards Child). The first twist sits on the Root and the last on the
    Child (a single twist sits on the Root). Only the twists' positions
    change; their orientations are left as they are.

    If Root, Child and Twist Joints are all left empty, the selection is used
    instead: the first selected joint is the Root, the second is the Child
    and the rest are the Twist Joints (in selection order).
    """

    identifier = "Distribute Twist Joints"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Root",
            value="",
            description="The joint at the start of the bone",
        )

        self.declare_option(
            name="Child",
            value="",
            description="The joint at the end of the bone",
        )

        self.declare_option(
            name="Twist Joints",
            value=[],
            description="The twist joints to spread along the bone, in order",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Root", "Child"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        if option_name == "Twist Joints":
            return aniseed.widgets.ObjectList()

        return None

    def _joints(self):
        """
        Returns the root, child and twists from the options, or from the
        selection when every option is empty.
        """
        root = self.option("Root").get()
        child = self.option("Child").get()
        twists = self.option("Twist Joints").get() or []

        if not root and not child and not twists:
            selection = cmds.ls(selection=True)
            return (
                selection[0] if selection else "",
                selection[1] if len(selection) > 1 else "",
                selection[2:],
            )

        return root, child, twists

    def is_valid(self) -> bool:
        root, child, twists = self._joints()

        if not root or not child or not twists:
            log.warning("Set Root, Child and Twist Joints, or select the root, then the child, then the twists")
            return False

        for node in [root, child] + list(twists):
            if not cmds.objExists(node):
                log.warning(f"{node} does not exist")
                return False

        return True

    def run(self) -> None:
        root, child, twists = self._joints()

        root_matrix = om.MMatrix(cmds.xform(root, query=True, matrix=True, worldSpace=True))

        # -- The child's position in the root's space, and its down-the-bone axis
        child_local = om.MPoint(cmds.xform(child, query=True, translation=True, worldSpace=True)) * root_matrix.inverse()
        axis = max(range(3), key=lambda idx: abs(child_local[idx]))

        # -- The first twist sits on the root and the last on the child
        steps = max(len(twists) - 1, 1)

        for idx, twist in enumerate(twists):
            local = [0.0, 0.0, 0.0]
            local[axis] = child_local[axis] * (idx / steps)

            world = om.MPoint(*local) * root_matrix
            cmds.xform(twist, translation=[world.x, world.y, world.z], worldSpace=True)

        log.info(f"Distributed {len(twists)} twist joints between {root} and {child}")
