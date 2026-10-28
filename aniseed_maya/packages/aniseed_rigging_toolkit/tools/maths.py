"""
Rigging Toolkit tools for spatial maths between nodes: measuring the distance
between them and finding an upvector position.
"""
import logging

from maya import cmds

import aniseed
import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)


def _resolve_from_selection(values: list) -> list or None:
    """
    Returns the given node names, with each empty one replaced by the
    selected node at its index. Logs a warning and returns None if there are
    not enough selected nodes to do so.
    """
    selection = cmds.ls(selection=True)
    resolved = []

    for index, value in enumerate(values):
        if value:
            resolved.append(value)
            continue

        if index >= len(selection):
            log.warning(f"Give the nodes in the options, or select at least {len(values)} nodes")
            return None

        resolved.append(selection[index])

    return resolved


# --------------------------------------------------------------------------------------
class DistanceBetweenTool(toolkits.Tool):
    """
    Logs the world space distance between two nodes: Node A and Node B, or
    the first and second selected nodes when they are not given.
    """

    identifier = "Distance Between"
    toolkit = "Rigging"
    categories = ["Math"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node A",
            value="",
            description="The node to measure from, used instead of the first selected node when given",
        )

        self.declare_option(
            name="Node B",
            value="",
            description="The node to measure to, used instead of the second selected node when given",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Node A", "Node B"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def _nodes(self) -> list or None:
        return _resolve_from_selection(
            [self.option("Node A").get(), self.option("Node B").get()],
        )

    def is_valid(self) -> bool:
        return self._nodes() is not None

    def run(self) -> None:
        node_a, node_b = self._nodes()

        distance = au.core.maths.distance_between(
            node_a=node_a,
            node_b=node_b,
        )
        log.info(f"Distance between {node_a} and {node_b} is {distance}")


# --------------------------------------------------------------------------------------
class CalculateUpvectorPosition(toolkits.Tool):
    """
    Logs the world space position for an upvector (pole vector) of the
    plane through three nodes, such as the joints of a limb: Point A, Point
    B and Point C, or the first, second and third selected nodes when they
    are not given. The position is out from Point B, at Length times the
    chain length. Turn on Create to create (and select) a transform there.
    """

    identifier = "Calculate Upvector Position"
    toolkit = "Rigging"
    categories = ["Transforms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Point A",
            value="",
            description="The start of the chain, used instead of the first selected node when given",
        )

        self.declare_option(
            name="Point B",
            value="",
            description="The middle of the chain, used instead of the second selected node when given",
        )

        self.declare_option(
            name="Point C",
            value="",
            description="The end of the chain, used instead of the third selected node when given",
        )

        self.declare_option(
            name="Length",
            value=0.5,
            description="How far out from Point B the position is, as a factor of the chain length",
        )

        self.declare_option(
            name="Create",
            value=False,
            description="Whether to create (and select) a transform at the position",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Point A", "Point B", "Point C"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def _points(self) -> list or None:
        return _resolve_from_selection(
            [
                self.option("Point A").get(),
                self.option("Point B").get(),
                self.option("Point C").get(),
            ],
        )

    def is_valid(self) -> bool:
        return self._points() is not None

    def run(self) -> None:
        point_a, point_b, point_c = self._points()

        position = au.core.maths.calculate_upvector_position(
            point_a=point_a,
            point_b=point_b,
            point_c=point_c,
            length=self.option("Length").get(),
            create=self.option("Create").get(),
        )
        log.info(f"Upvector position is {[position.x, position.y, position.z]}")
