import bpy


def create(name: str, parent: object = None) -> object:
    """
    This should create a "basic" item within the application. A basic item is
    typically expected to be a transform with little or no visual output in the viewport

    The name will be assigned to the item and if a parent is given the item will
    be made a child of that parent.

    Args:
        name: The name to assign to the item
        parent: Optional node to act as the parent
    """
    item = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(item)

    if parent:
        item.parent = get(parent)

    return item


def exists(item_name: str or object) -> bool:
    """
    This will test whether an item in the scene exists

    Args:
        item_name: The name of the item to test
    """
    return bpy.context.scene.objects.get(item_name) is not None


def get(item_name: str or object) -> object:
    """
    Given a name, this will return an api specific item. This is variable dependant
    on the application.

    Note that if you are implementing this in an application you should always test
    whether the item_name is actually already an application item.

    Args:
        item_name: The name of the item to find

    Returns:
        The found item in the applications python api
    """
    if isinstance(item_name, bpy.types.Object):
        return item_name

    return bpy.context.scene.objects.get(item_name)


def get_name(item: object or str) -> str:
    """
    This will return the name for the application item.

    Note that when implementing this function you should always test whether or not
    the given "item" is actually just a name already.

    Args:
        item: The item to return the name for
    """
    if isinstance(item, str):
        return item

    return item.name


def all_items_with_attribute(attribute_name: str) -> list[object]:
    """
    This should return all items which have an attribute with the given name

    Args:
        attribute_name: The name of the attribute to search for
    """
    results = list()

    for item in bpy.context.scene.objects:
        if attribute_name in item:
            results.append(item)

    return results


def get_children(item: object or str) -> list[object]:
    """
    This should return all children of the given item

    Args:
        item: The item to get the children of

    Returns:
        List of child items
    """
    item = get(item)

    return item.children


def get_parent(item: object or str) -> object:
    """
    This should return the parent of the given item

    Args:
        item: The item to get the parent of
    Returns:
        The parent of the given item
    """
    item = get(item)

    return item.parent


def set_parent(item: object or str, parent: object or str) -> None:
    """
    This should return the parent of the given item

    Args:
        item: The item to set the parent of
        parent: The parent item
    """
    item = get(item)
    item.parent = get(parent)



def delete(item: object or str) -> None:
    """
    This should delete the given item

    Args:
        item: The item to delete
    """
    item = get(item)
    with bpy.context.temp_override(selected_objects=[item]):
        bpy.ops.object.delete()
