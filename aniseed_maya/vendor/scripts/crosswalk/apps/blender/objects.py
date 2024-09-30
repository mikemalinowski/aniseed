import bpy


# --------------------------------------------------------------------------------------
def create(name: str, parent=None):
    """
    This should create a "basic" object within the application. A basic object is
    typically expected to be a transform with little or no visual output in the viewport

    The name will be assigned to the object and if a parent is given the object will
    be made a child of that parent.
    """
    object_ = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(object_)

    if parent:
        object_.parent = get_object(parent)

    return object_


# --------------------------------------------------------------------------------------
def exists(object_name):
    """
    This will test whether an object in the scene exists
    """
    return bpy.context.scene.objects.get(object_name) is not None


# --------------------------------------------------------------------------------------
def get_object(object_name: str):
    """
    Given a name, this will return an api specific object. This is variable dependant
    on the application.

    Note that if you are implementing this in an application you should always test
    whether the object_name is actually already an application object.
    """
    if isinstance(object_name, bpy.types.Object):
        return object_name

    return bpy.context.scene.objects.get(object_name)


# --------------------------------------------------------------------------------------
def get_name(object_):
    """
    This will return the name for the application object.

    Note that when implementing this function you should always test whether or not
    the given "object" is actually just a name already.
    """
    if isinstance(object_, str):
        return object_

    return object_.name


# --------------------------------------------------------------------------------------
def all_objects_with_attribute(attribute_name):
    """
    This should return all objects which have an attribute with the given name
    """
    results = list()

    for object_ in bpy.context.scene.objects:
        if attribute_name in object_:
            results.append(object_)

    return results


# --------------------------------------------------------------------------------------
def get_children(object_):
    """
    This should return all children of the given object
    """
    object_ = get_object(object_)

    return object_.children


# --------------------------------------------------------------------------------------
def get_parent(object_):
    """
    This should return the parent of the given object
    """
    object_ = get_object(object_)

    return object_.parent

# --------------------------------------------------------------------------------------
def set_parent(object_, parent):
    """
    This should return the parent of the given object
    """
    object_ = get_object(object_)
    object_.parent = get_object(parent)



# --------------------------------------------------------------------------------------
def delete(object_):
    """
    This should delete the given object
    """
    object_ = get_object(object_)
    with bpy.context.temp_override(selected_objects=[object_]):
        bpy.ops.object.delete()
