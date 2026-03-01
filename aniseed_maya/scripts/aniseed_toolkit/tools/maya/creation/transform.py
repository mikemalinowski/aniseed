import aniseed
import aniseed_toolkit


class BasicTransform(aniseed_toolkit.Tool):

    identifier = "Create Basic Transform"
    classification = "Creation"
    user_facing = False

    def run(
            self,
            classification: str,
            description: str,
            location: str,
            config: "aniseed.RigConfiguration",
            parent=None,
            match_to=None,
    ) -> str:
        """
        This will create a basic transform node but will name it using the aniseed
        config, and optionally set the parenting and transforms.

        Args:
            classification: The classification part of the name to apply
            description: The description part of the name to apply
            location: The location part of the name to apply
            config: The aniseed configuration instance
            parent: Optionally provide a parent, and this node will be made
                a child of it on creation.
            match_to: Optionally provide a node to match transform to on creation

        Returns:
            The name of the created node
        """
        return aniseed_toolkit.transforms.create(
            classification=classification,
            description=description,
            location=location,
            config=config,
            parent=parent,
            match_to=match_to,
        )


class CreateLocatorAtCenterTool(aniseed_toolkit.Tool):

    identifier = "Create Locator At Center"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(self) -> str:
        """
        Creates a locator at the center of the current selected components

        Returns:
            The name of the created locator
        """
        return aniseed_toolkit.transforms.create_locator_at_center()
