"""
Space helpers for rigs, such as finding the root (world) control.
"""
import mref


def get_root_control():
    """
    Returns the controller transform with the smallest hierarchy depth.

    Priority:
    1. Maya controller tags
    2. *_CTRL naming convention fallback

    Returns:
        str or None
    """
    controls = set()

    # --- Get controls from Maya controller tags ---
    for tag in mref.ls(type="controller") or []:
        source = tag.attr("controllerObject").source()
        if source:
            controls.add(source.node())

    # --- Fallback naming convention ---
    controls.update(mref.ls("*_CTRL", type="transform") or [])

    if not controls:
        return None

    # -- The depth is measured by the number of nodes in the dag path
    shallowest = min(controls, key=lambda node: node.full_name().count("|"))

    return shallowest.name()
