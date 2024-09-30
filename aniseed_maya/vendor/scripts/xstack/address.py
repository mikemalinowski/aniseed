"""
This module handles the logic around resolving and constructing attribute
addresses within a stack.

Addresses always take the form of

[COMPONENT LABEL].[CATEGORY].[ATTRIBUTE NAME]
"""
import re

ADDRESS_REGEX = re.compile(r"(\[.*\].\[(option|requirement|output)].\[.*\])")


# --------------------------------------------------------------------------------------
def get_label(address):
    """
    Returns the label part of the address
    """
    try:
        return address.split(".")[0][1:-1]

    except IndexError:
        return None


# --------------------------------------------------------------------------------------
def get_category(address):
    """
    Returns the category (or type) part of the address
    """
    try:
        return address.split(".")[1][1:-1]

    except IndexError:
        return None



# --------------------------------------------------------------------------------------
def get_attribute_name(address):
    """
    Returns the attribute name from the address
    """
    try:
        return address.split(".")[2][1:-1]

    except IndexError:
        return None


# --------------------------------------------------------------------------------------
def get_attribute(address, stack):
    """
    This will convert an address to an actual attribute within the stack

    Args:
        address: Address to resolve
        stack: Stack to get attribute from

    Returns:
        xstack.Attribute
    """

    # -- Break the address into its component parts
    component_label = get_label(address)
    category = get_category(address)
    attribute_name = get_attribute_name(address)

    # -- Attempt to find a matching component
    component = _get_component_with_label(
        component_label,
        stack,
    )

    # -- Switch out what we are looking for based on the classification
    if category == "option":
        return component.option(attribute_name)

    if category == "requirement":
        return component.requirement(attribute_name)

    if category == "output":
        return component.output(attribute_name)

    return None


# --------------------------------------------------------------------------------------
def form_address(attribute, category):
    """
    Given an attribute, we will form an address from it
    """
    return f"[{attribute.component().label()}].[{category}].[{attribute.name()}]"


# --------------------------------------------------------------------------------------
def is_address(address):
    """
    This will test whether the value being given is recognised as an address
    """
    if isinstance(address, str) and ADDRESS_REGEX.search(address):
        return True

    return False


# --------------------------------------------------------------------------------------
def _get_component_with_label(label, stack):
    """
    This is a private funciton that cycles the components of a stack looking
    for the first component with a matching label
    """
    for component in stack.components():
        if component.label() == label:
            return component

    return None


# --------------------------------------------------------------------------------------
def _get_uuid_from_label(label, stack):
    """
    Given a component label, this will return the uuid of that component
    """
    for component in stack.components():
        if component.label() == label:
            return component.uuid()

    return None


# --------------------------------------------------------------------------------------
def _is_uuid(data):
    """
    Convenience function to check whether the data we are given is a uuid formed string
    """
    if str(data).count("-") == 4 and len(str(data)) == 36:
        return True

    return False
