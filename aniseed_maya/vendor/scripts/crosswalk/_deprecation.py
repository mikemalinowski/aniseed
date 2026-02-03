# """
# This module contains deprecated code paths that should not be used but
# are preserved for the sake of backwards compatibility.
# """
#
# class DeprecatedObjectsModule:
#
# class HierarchicalObject:
#     """
#     This should never be re-implemented in other applications. This is here to serve
#     as a stand-in object in a standalone environment.
#     """
#
#     ALL_OBJECTS = []
#
#     def __init__(self):
#
#         name = ""
#         parent = ""
#         self.children = list()
#
#         HierarchicalObject.ALL_OBJECTS.append(self)
#
#
# # --------------------------------------------------------------------------------------
# def create(name: str, parent=None):
#     """
#     This should create a "basic" object within the application. A basic object is
#     typically expected to be a transform with little or no visual output in the viewport
#
#     The name will be assigned to the object and if a parent is given the object will
#     be made a child of that parent.
#     """
#     item = HierarchicalObject()
#     item.name = name
#     item.parent = parent
#
#     return item
#
#
# # --------------------------------------------------------------------------------------
# def exists(itemname):
#     """
#     This will test whether an object in the scene exists
#     """
#     for item in HierarchicalObject.ALL_OBJECTS:
#         if item.name == itemname:
#             return True
#
#     return False
#
#
# # --------------------------------------------------------------------------------------
# def get_object(itemname: str):
#     """
#     Given a name, this will return an api specific object. This is variable dependant
#     on the application.
#
#     Note that if you are implementing this in an application you should always test
#     whether the itemname is actually already an application object.
#     """
#     if isinstance(itemname, HierarchicalObject):
#         return itemname
#
#     for item in HierarchicalObject.ALL_OBJECTS:
#         if item.name == itemname:
#             return item
#
#
# # --------------------------------------------------------------------------------------
# def get_name(item):
#     """
#     This will return the name for the application object.
#
#     Note that when implementing this function you should always test whether or not
#     the given "object" is actually just a name already.
#     """
#     if isinstance(item, str):
#         return item
#
#     return item.name
#
#
# # --------------------------------------------------------------------------------------
# def all_objects_with_attribute(attribute_name):
#     """
#     This should return all objects which have an attribute with the given name
#     """
#     results = list()
#
#     for item in HierarchicalObject.ALL_OBJECTS:
#         if hasattr(object, attribute_name):
#             results.append(item)
#
#     return results
#
#
# # --------------------------------------------------------------------------------------
# def get_children(item):
#     """
#     This should return all children of the given object
#     """
#     item = get_object(item)
#
#     return item.children
#
#
# # --------------------------------------------------------------------------------------
# def get_parent(item):
#     """
#     This should return the parent of the given object
#     """
#     item = get_object(item)
#
#     return item.parent
#
#
# # --------------------------------------------------------------------------------------
# def set_parent(item, parent):
#     """
#     This should return the parent of the given object
#     """
#     item = get_object(item)
#
#     item.parent = parent
#
# # --------------------------------------------------------------------------------------
# def delete(item):
#     """
#     This should delete the given object
#     """
#     HierarchicalObject.ALL_OBJECTS.remove(item)
