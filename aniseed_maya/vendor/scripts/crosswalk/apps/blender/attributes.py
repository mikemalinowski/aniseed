

# --------------------------------------------------------------------------------------
def add_string_attribute(object_, attribute_name, value):
    """
    This should add an attribute to the object, and where the attributes are
    typed, it should be a string
    """
    object_[attribute_name] = str(value)


# --------------------------------------------------------------------------------------
def add_float_attribute(object_, attribute_name, value):
    """
    This should add an attribute to the object, and where the attributes are
    typed, it should be a float
    """
    object_[attribute_name] = float(value)


# --------------------------------------------------------------------------------------
def set_attribute(object_, attribute_name, value):
    """
    This should set the attribute with the givne name on the given object to the
    given value
    """
    if not has_attribute(object_, attribute_name):
        return

    object_[attribute_name] = value


# --------------------------------------------------------------------------------------
def get_attribute(object_, attribute_name):
    """
    This should look on the object for an attribute of this name and return its value
    """
    return object_[attribute_name]


# --------------------------------------------------------------------------------------
def has_attribute(object_, attribute_name):
    """
    This should check if an object has an attribute of this name
    """
    return attribute_name in object_
