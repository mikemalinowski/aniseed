"""
Helpers for creating and wiring constraints.
"""
import mref

from ..core import _nodes


def parent_and_scale(driver, driven, maintain_offset: bool = True) -> tuple:
    """
    Parent and scale constrains the driven node to the driver.

    Args:
        driver: The node to constrain to
        driven: The node to constrain
        maintain_offset: If True the driven node keeps its current offset
            from the driver

    Returns:
        A tuple of the parent constraint and the scale constraint (mref
        items)
    """
    parent_constraint = mref.parentConstraint(
        driver,
        driven,
        maintainOffset=maintain_offset,
    )[0]

    scale_constraint = mref.scaleConstraint(
        driver,
        driven,
        maintainOffset=maintain_offset,
    )[0]

    return parent_constraint, scale_constraint


def blend_weights(attribute, constraint) -> mref.ReferencedItem:
    """
    Drives a two target constraint from a single 0-1 attribute. At 0 the
    first target is fully weighted and at 1 the second target is fully
    weighted.

    Args:
        attribute: The attribute to drive the blend
        constraint: The constraint whose two target weights should be driven

    Returns:
        The reverse node which drives the weight of the first target
    """
    attribute = mref.get(attribute)
    weight_attributes = mref.get(constraint).weight_attributes()

    reverse_node = mref.create("reverse")
    attribute.connect(reverse_node.inputX)
    reverse_node.outputX.connect(weight_attributes[0])
    attribute.connect(weight_attributes[1])

    return reverse_node


def remove_all(nodes: list[str] = ""):
    """
    Deletes every constraint which is a direct child of the given nodes
    (any child whose node type contains "constraint").

    Args:
        nodes: The nodes to remove the constraints from

    Returns:
        None
    """
    for node in nodes:
        # -- listRelatives rather than children(), so nodes which are not
        # -- dag nodes (and so have no children) are skipped, not an error
        children = mref.listRelatives(
            _nodes.resolve(node),
            children=True,
            fullPath=True,
        )
        for child in children or []:
            if "constraint" in child.node_type().lower():
                child.delete()
