import typing
import maya.cmds as mc

from . import items


def add_string_attribute(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should add an attribute to the item, and where the attributes are
    typed, it should be a string

    Args:
        item: The item or item name to add the attribute to
        attribute_name: The name of the attribute
        value: The value of the attribute
    """
    item = items.get_name(item)

    mc.addAttr(
        item,
        shortName=attribute_name,
        dt="string"
    )

    mc.setAttr(
        f"{item}.{attribute_name}",
        value,
        type="string",
    )

    return f"{item}.{attribute_name}"


def add_float_attribute(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should add an attribute to the item, and where the attributes are
    typed, it should be a float
    """
    item = items.get_name(item)

    mc.addAttr(
        item,
        shortName=attribute_name,
        at="float",
        dv=value
    )

    return f"{item}.{attribute_name}"


def set_value(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should set the attribute with the given name on the given item to the
    given value
    """
    item = items.get_name(item)

    kwargs = {}

    if isinstance(value, str):
        kwargs["type"] = "string"

    mc.setAttr(
        f"{item}.{attribute_name}",
        value,
        **kwargs
    )


def get_value(item: object, attribute_name: str) -> typing.Any:
    """
    This should look on the item for an attribute of this name and return its value
    """
    item = items.get_name(item)

    return mc.getAttr(
        f"{item}.{attribute_name}",
    )


def has_attribute(item: object, attribute_name: str) -> bool:
    """
    This should check if an item has an attribute of this name
    """
    item = items.get_name(item)

    return mc.objExists(
        f"{item}.{attribute_name}"
    )