import typing


def add_string_attribute(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should add an attribute to the item, and where the attributes are
    typed, it should be a string

    Args:
        item: The item or item name to add the attribute to
        attribute_name: The name of the attribute
        value: The value of the attribute
    """
    setattr(
        item,
        attribute_name,
        value,
    )


def add_float_attribute(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should add an attribute to the item, and where the attributes are
    typed, it should be a float
    """
    setattr(
        item,
        attribute_name,
        value,
    )


def set_value(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should set the attribute with the given name on the given item to the
    given value
    """
    setattr(
        item,
        attribute_name,
        value,
    )


def get_value(item: object, attribute_name: str) -> typing.Any:
    """
    This should look on the item for an attribute of this name and return its value
    """
    return getattr(
        item,
        attribute_name,
    )


def has_attribute(item: object, attribute_name: str) -> bool:
    """
    This should check if an item has an attribute of this name
    """
    return hasattr(
        item,
        attribute_name,
    )
