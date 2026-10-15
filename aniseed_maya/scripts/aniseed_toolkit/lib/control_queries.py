"""
Helpers for querying the rig controls (controller tagged nodes) in the scene.
"""
import mref
from maya import cmds


def has_curve_shapes(node) -> bool:
    """
    Returns True if the given node has at least one nurbsCurve shape.

    Args:
        node: The node (name or mref item) to test
    """
    return bool(mref.get(node).children(node_type="nurbsCurve"))


def curve_controls() -> list[str]:
    """
    Returns every controller tagged node in the scene which has at least one
    nurbsCurve shape.

    The names are returned exactly as maya reports them because callers
    compare and parse them as strings (e.g. for location tokens or skip lists).
    """
    # -- cmds rather than mref, as mref would turn maya's (possibly partial
    # -- path) names into short names
    return [
        node
        for node in cmds.controller(allControllers=True, query=True) or []
        if has_curve_shapes(node)
    ]
