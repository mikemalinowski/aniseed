"""
Rigging Toolkit tools for tagging nodes, so they can be found by tag later.
"""
import logging

import aniseed
import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
class TagNode(toolkits.Tool):
    """
    Adds Tag to the tags of Node (stored in its aniseed_tagging attribute,
    which is created if need be). Nothing changes if Node already has the tag.
    """

    identifier = "Tag Node"
    toolkit = "Rigging"
    categories = ["Tagging"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node to tag",
        )

        self.declare_option(
            name="Tag",
            value="",
            description="The tag to add to the node",
        )

    def option_widget(self, option_name: str):
        if option_name == "Node":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        return None

    def is_valid(self) -> bool:
        if not self.option("Node").get() or not self.option("Tag").get():
            log.warning("Give the Node to tag and the Tag to add")
            return False

        return True

    def run(self) -> None:
        au.rig.tagging.tag(
            node=self.option("Node").get(),
            tag=self.option("Tag").get(),
        )
