import maya.cmds as mc
import maya.api.OpenMaya as om


# --------------------------------------------------------------------------------------
def create(name: str, parent=None):
    """
    This should create a "basic" object within the application. A basic object is
    typically expected to be a transform with little or no visual output in the viewport

    The name will be assigned to the object and if a parent is given the object will
    be made a child of that parent.
    """
    node = mc.createNode("transform")

    node = mc.rename(
        node,
        name,
    )

    if parent:
        mc.parent(
            node,
            parent
        )

    return get_object(node)


# --------------------------------------------------------------------------------------
def exists(object_name):
    """
    This will test whether an object in the scene exists
    """
    return mc.objExists(object_name)


# --------------------------------------------------------------------------------------
def get_object(object_name: str):
    """
    Given a name, this will return an api specific object. This is variable dependant
    on the application.

    Note that if you are implementing this in an application you should always test
    whether the object_name is actually already an application object.
    """
    if isinstance(object_name, om.MObject):
        return object_name

    try:
        selection_list = om.MSelectionList()
        selection_list.add(object_name)

        return selection_list.getDependNode(0)

    except RuntimeError:
        raise RuntimeError(f"Could not find node {object_name}")


# --------------------------------------------------------------------------------------
def get_name(object_):
    """
    This will return the name for the application object.

    Note that when implementing this function you should always test whether or not
    the given "object" is actually just a name already.
    """
    if isinstance(object_, str):
        return object_

    try:
        return om.MFnDependencyNode(object_).name()

    except ValueError:
        raise ValueError(f"Could not get dependency node for {object_}")


# --------------------------------------------------------------------------------------
def all_objects_with_attribute(attribute_name):
    """
    This should return all objects which have an attribute with the given name
    """
    nodes = list(
        set(
            mc.ls(
                f"*.{attribute_name}",
                r=True,
                o=True,
            ),
        ),
    )

    return [
        get_object(node)
        for node in nodes
    ]


# --------------------------------------------------------------------------------------
def get_children(object_):
    """
    This should return all children of the given object
    """
    name = get_name(object_)

    return mc.listRelatives(name, children=True) or list()


# --------------------------------------------------------------------------------------
def get_parent(object_):
    """
    This should return the parent of the given object
    """
    name = get_name(object_)

    try:
        return mc.listRelatives(name, parent=True)[0]

    except IndexError:
        return None


# --------------------------------------------------------------------------------------
def set_parent(object_, parent):
    """
    This should return the parent of the given object
    """
    if parent:
        mc.parent(get_name(object_), parent)
    else:
        mc.parent(get_name(object_), world=True)


# --------------------------------------------------------------------------------------
def delete(object_):
    """
    This should delete the given object
    """
    name = get_name(object_)

    mc.delete(name)
