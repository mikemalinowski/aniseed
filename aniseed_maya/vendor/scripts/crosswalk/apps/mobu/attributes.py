import pyfbsdk as mobu

from . import objects


# --------------------------------------------------------------------------------------
def add_string_attribute(object_, attribute_name, value):
    """
    This should add an attribute to the object, and where the attributes are
    typed, it should be a string
    """
    object_ = objects.get_object(object_)

    object_.PropertyCreate(
        attribute_name,
        mobu.FBPropertyType.kFBPT_charptr,
        "String",
        True,
        True,
        None,
    )
    property_ = object_.PropertyList.Find(attribute_name)

    property_.Data = value

    return property_


# --------------------------------------------------------------------------------------
def add_float_attribute(object_, attribute_name, value):
    """
    This should add an attribute to the object, and where the attributes are
    typed, it should be a float
    """
    object_ = objects.get_object(object_)

    object_.PropertyCreate(
        attribute_name,
        mobu.FBPropertyType.kFBPT_double,
        "Number",
        True,
        True,
        None,
    )
    property_ = object_.PropertyList.Find(attribute_name)

    property_.Data = value

    return property_



# --------------------------------------------------------------------------------------
def set_attribute(object_, attribute_name, value):
    """
    This should set the attribute with the givne name on the given object to the
    given value
    """
    property_ = get_attribute(object_, attribute_name)

    property_.Data = value


# --------------------------------------------------------------------------------------
def get_attribute(object_, attribute_name):
    """
    This should look on the object for an attribute of this name and return its value
    """
    object_ = objects.get_object(object_)

    return object_.PropertyList.Find(attribute_name)


# --------------------------------------------------------------------------------------
def has_attribute(object_, attribute_name):
    """
    This should check if an object has an attribute of this name
    """
    object_ = objects.get_object(object_)

    return object_.PropertyList.Find(attribute_name) is not None
