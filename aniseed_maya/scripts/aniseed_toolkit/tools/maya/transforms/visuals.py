import mref
import aniseed_toolkit


class ShowAxisTool(aniseed_toolkit.Tool):
    identifier = "Show Axis"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(
        self,
        node: str = "",
        visibility: bool = True,
    ):
        for node in mref.selected():
            if node.has_attribute("displayLocalAxis"):
                node.displayLocalAxis.set(visibility)
