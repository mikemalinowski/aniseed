import maya.cmds as mc

from . import objects


# --------------------------------------------------------------------------------------
def add_string_attribute(object_, attribute_name, value):
    """
    This should add an attribute to the object, and where the attributes are
    typed, it should be a string
    """
    object_ = objects.get_name(object_)

    mc.addAttr(
        object_,
        shortName=attribute_name,
        dt="string"
    )

    mc.setAttr(
        f"{object_}.{attribute_name}",
        value,
        type="string",
    )

    return f"{object_}.{attribute_name}"


# --------------------------------------------------------------------------------------
def add_float_attribute(object_, attribute_name, value):
    """
    This should add an attribute to the object, and where the attributes are
    typed, it should be a float
    """
    object_ = objects.get_name(object_)

    mc.addAttr(
        object_,
        shortName=attribute_name,
        at="float",
        dv=value
    )

    return f"{object_}.{attribute_name}"


# --------------------------------------------------------------------------------------
def set_attribute(object_, attribute_name, value):
    """
    This should set the attribute with the givne name on the given object to the
    given value
    """
    object_ = objects.get_name(object_)

    kwargs = {}

    if isinstance(value, str):
        kwargs["type"] = "string"

    mc.setAttr(
        f"{object_}.{attribute_name}",
        value,
        **kwargs
    )


# --------------------------------------------------------------------------------------
def get_attribute(object_, attribute_name):
    """
    This should look on the object for an attribute of this name and return its value
    """
    object_ = objects.get_name(object_)

    return mc.getAttr(
        f"{object_}.{attribute_name}",
    )


# --------------------------------------------------------------------------------------
def has_attribute(object_, attribute_name):
    """
    This should check if an object has an attribute of this name
    """
    object_ = objects.get_name(object_)

    return mc.objExists(
        f"{object_}.{attribute_name}"
    )