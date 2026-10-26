import typing
import pyfbsdk as mobu

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
    item = items.get(item)

    item.PropertyCreate(
        attribute_name,
        mobu.FBPropertyType.kFBPT_charptr,
        "String",
        True,
        True,
        None,
    )
    property_ = item.PropertyList.Find(attribute_name)

    property_.Data = value

    return property_


def add_float_attribute(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should add an attribute to the item, and where the attributes are
    typed, it should be a float
    """
    item = items.get(item)

    item.PropertyCreate(
        attribute_name,
        mobu.FBPropertyType.kFBPT_double,
        "Number",
        True,
        True,
        None,
    )
    property_ = item.PropertyList.Find(attribute_name)

    property_.Data = value

    return property_


def set_value(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should set the attribute with the given name on the given item to the
    given value
    """
    item = items.get(item)
    item.PropertyList.Find(attribute_name).Data = value


def get_value(item: object, attribute_name: str) -> typing.Any:
    """
    This should look on the item for an attribute of this name and return its value
    """
    item = items.get(item)

    return item.PropertyList.Find(attribute_name).Data


def has_attribute(item: object, attribute_name: str) -> bool:
    """
    This should check if an item has an attribute of this name
    """
    item = items.get(item)

    return item.PropertyList.Find(attribute_name) is not None
