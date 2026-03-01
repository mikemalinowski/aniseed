import aniseed
import aniseed_toolkit


class CreateGuide(aniseed_toolkit.Tool):
    identifier = "Create Guide"
    classification = "Rigging"
    categories = [
        "Creation",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["joint", "parent", "link_to"]:
            return aniseed.widgets.ObjectSelector()

    def run(
        self,
        joint="",
        parent=None,
        position_only=False,
        shape="core_cube",
        scale=3.0,
        link_to=None,
    ) -> str:
        """
        Creates a simple guide control object to transform a joint

        Args:
            joint: The joint to drive with this guide
            parent: The parent of this guide
            position_only: If True, the joint will only be position constrained
                to the guide control
            shape: The shape of the guide control (accessible via
                aniseed_toolkit/_resources/shapes
            scale: The scale of the guide control shape
            link_to: If given, a guide line will be drawn between this node
                and the linked node

        Returns:
            Name of the guide control node
        """
        return aniseed_toolkit.guide.create(
            joint=joint,
            parent=parent,
            position_only=position_only,
            shape=shape,
            scale=scale,
            link_to=link_to,
        )


class GuideTween(aniseed_toolkit.Tool):

    identifier = "Create Guide Tween"
    classification = "Rigging"
    categories = [
        "Creation",
    ]

    def run(self, drive_this, from_this, to_this, parent=None, factor=None):
        """
        Creates a blended constraint
        """
        return aniseed_toolkit.guide.create_tween(
            drive_this=drive_this,
            from_this=from_this,
            to_this=to_this,
            parent=parent,
        )
