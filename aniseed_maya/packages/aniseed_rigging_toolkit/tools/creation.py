"""
Rigging Toolkit tools for creating nodes: guides to lay out joints, and
locators.
"""
import logging

from maya import cmds

import aniseed
import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
class CreateGuide(toolkits.Tool):
    """
    Creates a guide control which drives the Joint, matched to the joint's
    transform. Position Only constrains just the joint's position rather
    than its whole transform. Shape and Scale set the look of the guide.
    Give a Parent to parent the guide under it, and Link To to draw a guide
    line from the guide to that node.
    """

    identifier = "Create Guide"
    toolkit = "Rigging"
    categories = ["Creation"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Joint",
            value="",
            description="The joint for the guide to drive",
        )

        self.declare_option(
            name="Parent",
            value="",
            description="The node to parent the guide under, if any",
        )

        self.declare_option(
            name="Position Only",
            value=False,
            description="Whether the guide only drives the position of the joint",
        )

        self.declare_option(
            name="Shape",
            value="core_cube",
            description="The name of the shape to give the guide",
        )

        self.declare_option(
            name="Scale",
            value=3.0,
            description="The scale of the guide's shape",
        )

        self.declare_option(
            name="Link To",
            value="",
            description="A node to draw a guide line to from the guide, if any",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Joint", "Parent", "Link To"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        joint = self.option("Joint").get()

        if not joint:
            log.warning("Set the Joint for the guide to drive")
            return False

        if not cmds.objExists(joint):
            log.warning(f"The Joint does not exist: {joint}")
            return False

        return True

    def run(self) -> None:
        guide = au.rig.guide.create(
            joint=self.option("Joint").get(),
            parent=self.option("Parent").get() or None,
            position_only=self.option("Position Only").get(),
            shape=self.option("Shape").get(),
            scale=self.option("Scale").get(),
            link_to=self.option("Link To").get() or None,
        )
        log.info(f"Created guide {guide}")


# --------------------------------------------------------------------------------------
class CreateLocatorAtCenterTool(toolkits.Tool):
    """
    Creates a locator at the center of the selected components (such as
    vertices) or geometry.
    """

    identifier = "Create Locator At Center"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the components (or geometry) to create a locator at the center of")
            return False

        return True

    def run(self) -> None:
        locator = au.scene.transforms.create_locator_at_center()
        log.info(f"Created locator {locator}")
