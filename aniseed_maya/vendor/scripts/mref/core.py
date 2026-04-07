import types
import typing
import os
import inspect
import factories
from maya import cmds
from maya.api import OpenMaya as om


class Trait:
    """
    This is the base trait class. Traits expose functionality
    to the ReferenceItem.
    """

    # -- If traits implement the same methods then the trait with
    # -- the highest priority will always have its method executed.
    priority = 0

    def __init__(self, pointer, item):
        self._pointer = pointer
        self.item = item

    @classmethod
    def can_bind(cls, pointer):
        return False


class TraitLibrary(factories.Factory):
    """
    This is a factory which is used to find and take traits from.
    """
    _instance = None

    def __init__(self):
        super(
            TraitLibrary,
            self,
        ).__init__(
            abstract=Trait,
            paths=[
                os.path.join(
                    os.path.dirname(__file__),
                    "traits",
                ),
            ]
        )

    def plugins(self, include_disabled=False):
        """
        We re-implement this method as we always want to return the plugin list
        based on the priority value
        """
        plugins = super(TraitLibrary, self).plugins(include_disabled=include_disabled)
        plugins.sort(key=lambda x: x.priority)
        return plugins

    @classmethod
    def singleton(cls):
        """
        We typically do not need to re-instance this factory, therefore in
        most cases its better to access it as a singleton.
        """
        if TraitLibrary._instance is None:
            TraitLibrary._instance = cls()
        return TraitLibrary._instance


class ReferencedItem:
    """
    This is the class which developers will usually interact with. This class
    will have traits bound to it.
    """

    def __init__(self, item: "ReferencedItem|str|om.MObject"):

        # -- We can be given a variety of variable types, so we
        # -- resolve that down to an mobject
        self._pointer = self._resolve_pointer(item)

        # -- Cycle our trait library and bind any traits which state
        # -- that they can bind to an mobject of this type.
        self.traits = [
            trait(self._pointer, self)
            for trait in TraitLibrary.singleton().plugins()
            if trait.can_bind(self._pointer)
        ]

        # -- This is where we will store all of the functions from all of the
        ## -- traits. That way we can do a function look up very quickly.
        self.func_mapping = dict()

        for trait in self.traits:

            # -- Get all the callables for the trait
            for callable_item in inspect.getmembers(trait):

                # -- Ignore private or built in methods
                if callable_item[0].startswith("_"):
                    continue

                # -- Providing it is a method, we add it to the func mapping
                # -- for printing as well as this classes internal dictionary.
                if isinstance(callable_item[1], types.MethodType):
                    self.func_mapping[callable_item[0]] = callable_item[1]
                    self.__dict__[callable_item[0]] = callable_item[1]

    def __repr__(self) -> str:
        """
        This will build up a string which shows the name of this object
        along with all the traits that make it up.
        """
        string = "<"
        if hasattr(self, "name"):
            string += self.name()

        else:
            string += str(self)

        string += " ["
        for trait in self.traits:
            string += f"{trait.__class__.__name__}, "

        return string[:-2] + "]>"

    def __eq__(self, other: typing.Any) -> bool:
        """
        This will return true of this object is the same as the other
        given object.
        """
        if not isinstance(other, self.__class__):
            return False
        if self._pointer == other.pointer():
            return True
        return False

    def __hash__(self) -> int:
        """
        This will return the has of the fully qualified name of this object.
        """
        if hasattr(self, "full_name"):
            return hash(self.full_name())

        if hasattr(self, "name"):
            return hash(self.name())

        return hash(str(self))

    def __lt__(self, other) -> bool:
        """
        This will return whether this object is considered lower than the other.
        We do this by looking at its string
        """
        return str(self) < str(other)

    def assigned_traits(self) -> list[Trait]:
        """
        This will return a list of the traits assigned to this item
        """
        return [trait.__name__ for trait in self.traits]

    def print_methods(self) -> None:
        """
        This is a help function which will log all the functions from all the
        traits bound to this object.
        """
        for method_name in sorted(self.func_mapping.keys()):
            print(method_name)

    @classmethod
    def _resolve_pointer(cls, item: "ReferencedItem|str|om.MObject") -> om.MObject:
        """
        This will test the variable type coming in and resolve it down
        to an mobject.
        """
        if isinstance(item, om.MObject):
            return item

        if isinstance(item, ReferencedItem):
            return item.pointer()

        if isinstance(item, str):
            sel = om.MSelectionList()
            sel.add(item)

            if "." in item:
                return sel.getPlug(0)
            return sel.getDependNode(0)

    def pointer(self) -> om.MObject:
        """
        This will return the mobject represented by this object.
        """
        return self._pointer

def get(identifier: typing.Any) -> ReferencedItem|list[ReferencedItem]:
    """
    This will take in either an object (in the form of a string, reference item or
    mobject) or a list of items in the same supported formats and return either the
    ReferenceItem or a list of ReferencedItems.
    """
    if isinstance(identifier, list):
        return ReferenceList(
            ReferencedItem(sub_identifier)
            for sub_identifier in identifier
        )
    return ReferencedItem(identifier)


def create(node_type, unique=True, *args, **kwargs) -> ReferencedItem|list[ReferencedItem]:
    """
    This will use the normal cmds create but return the ReferencedItem
    casts. For any types which return a list of items, then a list of
    ReferencedItems is returned.
    """
    # -- If we have been given a name argument and we need to
    # -- make it unique, do that before we do anything else.
    if unique and "name" in kwargs:
        desired_name = kwargs.pop("name")
        kwargs["name"] = unique_name(desired_name)

    parent = kwargs.get("parent", None)
    result = cmds.createNode(node_type, *args, **kwargs)

    if isinstance(result, list):
        return ReferenceList(
            get(node)
            for node in result
        )
    node = get(result)

    if parent:
        node.set_parent(parent)
    return node


def selected() -> list[ReferencedItem]:
    """
    This will return the current selection as a list of ReferencedItems.
    """
    return ReferenceList(
        get(node)
        for node in cmds.ls(selection=True, long=True)
    )


def find(search_string: str, **kwargs) -> list[ReferencedItem]:
    """
    This will use a wildcard search (cmds.ls) and return the results
    as ReferencedItems.
    """
    # -- Long is a forced argument
    if "long" in kwargs:
        kwargs.pop("long")

    return ReferenceList(
        get(node)
        for node in cmds.ls(search_string, long=True, **kwargs)
    )


def select(nodes: ReferencedItem|list[ReferencedItem]) -> None:
    """
    This will select the given nodes
    """
    if not isinstance(nodes, list):
        nodes = [nodes]

    nodes = [node.full_name() if isinstance(node, ReferencedItem) else node for node in nodes]
    cmds.select(nodes)


def delete(nodes: ReferencedItem|list[ReferencedItem]) -> None:
    if not isinstance(nodes, list):
        nodes = [nodes]

    for node in nodes:
        if isinstance(node, ReferencedItem):
            node = node.full_name()
        cmds.delete(node)


class ReferenceList(list):

    def names(self):
        results = []

        for node in self:
            if isinstance(node, ReferencedItem):
                results.append(node.name())
            else:
                results.append(node)
        return results

    def full_names(self):
        results = []

        for node in self:
            if isinstance(node, ReferencedItem):
                results.append(node.full_name())
            else:
                results.append(node)
        return results


def unique_name(name):
    counter = 1
    proposed_name = name

    while cmds.objExists(proposed_name):
        counter += 1
        proposed_name = f"{name}{counter}"

    return proposed_name
