"""
Helpers for creating and wiring constraints.
"""
import mref


def parent_and_scale(driver, driven, maintain_offset: bool = True) -> tuple:
    """
    Parent and scale constrains the driven node to the driver.

    Returns:
        The parent constraint and the scale constraint
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
