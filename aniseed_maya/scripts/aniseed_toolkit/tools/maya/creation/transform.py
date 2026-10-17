import aniseed
import aniseed_toolkit


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
        return aniseed_toolkit.scene.transforms.create_locator_at_center()
