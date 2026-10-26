import re
import typing
import os
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

    DynamicFunctionNotFound = 12325092

    def __init__(self, pointer, item):
        self._pointer = pointer
        self.item = item

    @classmethod
    def can_bind(cls, pointer):
        return False

    def dynamic_function(self, item):
        return Trait.DynamicFunctionNotFound

class TraitLibrary(factories.Factory):
    """
    This is a factory which is used to find and take traits from.
    """
    _instance = None

    def __init__(self):
        super().__init__(
            abstract=Trait,
            paths=[
                os.path.join(
                    os.path.dirname(__file__),
                    "traits",
                ),
            ]
        )
        self._cached_plugins = None

    def plugins(self, include_disabled=False):
        """
        We re-implement this method as we always want to return the plugin list
        based on the priority value.

        The sorted plugin list is cached on the default code path —
        traits don't change after the library is initialised, and
        re-discovering them on every ``ReferencedItem`` construction
        is by far the largest cost in hot loops. Pass
        ``include_disabled=True`` to bypass the cache.
        """
        if include_disabled:
            plugins = super().plugins(include_disabled=True)
            plugins.sort(key=lambda x: x.priority)
            return plugins

        if self._cached_plugins is None:
            plugins = super().plugins(include_disabled=False)
            plugins.sort(key=lambda x: x.priority)
            self._cached_plugins = plugins

        return self._cached_plugins

    def invalidate_plugin_cache(self):
        """
        Clears the cached plugin list. Call this if you've programmatically
        registered or unregistered traits via the underlying factory and need
        the next ``plugins()`` call to re-discover them.
        """
        self._cached_plugins = None

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
    _plug_regex = re.compile(r"(\w+)(?:\[(\d+)\])?")

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

    def __getattr__(self, name: str):
        # -- Iterate traits in reverse so that the highest-priority trait
        # -- wins when multiple traits define the same attribute.
        for trait in reversed(self.traits):
            try:
                return getattr(trait, name)
            except AttributeError:
                pass
        raise AttributeError(f"{name} is not part of {self}")

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
        if isinstance(self._pointer, om.MObject):
            return om.MObjectHandle(self._pointer).hashCode()

        if isinstance(self._pointer, om.MPlug):
            return hash((
                om.MObjectHandle(self._pointer.node()).hashCode(),
                om.MObjectHandle(self._pointer.attribute()).hashCode(),
            ))

        return hash(str(self))

    def __lt__(self, other) -> bool:
        if isinstance(other, ReferencedItem):
            return self._sort_key() < other._sort_key()
        if isinstance(other, str):
            return self._sort_key() < other
        return NotImplemented

    def _sort_key(self) -> str:
        if hasattr(self, "full_name"):
            return self.full_name()
        if hasattr(self, "name"):
            return self.name()
        return str(self)

    def assigned_traits(self) -> list[str]:
        """
        This will return a list of the traits assigned to this item
        """
        return [trait.__class__.__name__ for trait in self.traits]

    def print_methods(self) -> None:
        """
        This is a help function which will log all the functions from all the
        traits bound to this object.
        """
        seen = set()
        for trait in self.traits:
            for name in dir(trait):
                if name.startswith("_"):
                    continue
                if not callable(getattr(trait, name, None)):
                    continue
                seen.add(name)

        for name in sorted(seen):
            print(name)

    @classmethod
    def _resolve_pointer(
        cls,
        item: "ReferencedItem|str|om.MObject|om.MPlug",
    ) -> "om.MObject|om.MPlug":
        """
        Resolve the incoming variable down to an MObject (for node-backed
        items) or an MPlug (for attribute-backed items).
        """
        if isinstance(item, om.MObject):
            return item

        if isinstance(item, om.MPlug):
            return item

        if isinstance(item, ReferencedItem):
            return item.pointer()

        if isinstance(item, str):
            if "." in item:
                return cls.get_mplug(item)
            return cls._resolve_node(item)

        raise TypeError(
            f"Cannot resolve pointer from {type(item).__name__}: {item!r}"
        )

    def pointer(self) -> "om.MObject|om.MPlug":
        """
        Returns the underlying Maya handle — an MObject for node-backed
        items, or an MPlug for attribute-backed items.
        """
        return self._pointer

    @classmethod
    def _resolve_node(cls, node_address):
        sel = om.MSelectionList()
        sel.add(node_address)
        return sel.getDependNode(0)

    @classmethod
    def get_mplug(cls, attr_string):
        """
        This will attempt to resolve the plug from the given attribute string. Note
        that this is not as simple as it should be, as there are multiple types of
        attributes in maya, each of which need accessing in slightly different ways.
        """

        # -- Firstly, if this is not an attribute address, we error out
        # -- immediately.
        if "." not in attr_string:
            raise RuntimeError(f"Not an attribute: {attr_string}")

        # -- If this is a direct attribute we return it. As this is the case
        # -- for most situations we opt for speed by asking for forgiveness
        # -- rather than permission
        try:
            sel = om.MSelectionList()
            sel.add(attr_string)
            return sel.getPlug(0)
        except RuntimeError:
            pass

        # -- To reach here we're dealing with an nested attribute or compound
        # -- attribute
        node_name, remainder = attr_string.split(".", 1)

        # -- Get the Dependency Node Fn for the node
        sel = om.MSelectionList()
        sel.add(node_name)
        obj = sel.getDependNode(0)
        fn = om.MFnDependencyNode(obj)

        # -- Get all the attribute parts
        tokens = remainder.split(".")

        # --- Now we construct a map of the alias's. This is to support special
        # -- attributes such as those on blendshapes where the address is the
        # -- alias but the actual plug is the weight[n] attribute./
        alias_map = dict(fn.getAliasList() or [])
        if tokens[0] in alias_map:
            alias_path = alias_map[tokens[0]]
            tokens = alias_path.split(".") + tokens[1:]

        # -- Define the variable we will ultimately try and return
        plug = None

        for idx, token in enumerate(tokens):

            # -- Check if this is a valid attribute form
            match = cls._plug_regex.fullmatch(token)
            if not match:
                raise RuntimeError(f"Invalid token: {token}")

            name, index = match.groups()
            index = int(index) if index is not None else None

            # If we're the first token in the address we can just get the
            # -- plug directly
            if idx == 0:
                plug = fn.findPlug(name, False)
            else:
                # -- we need to start special casing and branching based
                # -- on the plug type
                if plug.isCompound:
                    found = False
                    for c in range(plug.numChildren()):
                        child = plug.child(c)
                        if child.partialName(useLongNames=True) == name:
                            plug = child
                            found = True
                            break
                    if not found:
                        raise RuntimeError(f"Child '{name}' not found on {plug.name()}")
                else:
                    raise RuntimeError(f"{plug.name()} has no child '{name}'")

            # -- Check for an array attribute
            if index is not None:
                if not plug.isArray:
                    raise RuntimeError(f"{plug.name()} is not an array")
                plug = plug.elementByLogicalIndex(index)

        return plug

def get(identifier: typing.Any) -> ReferencedItem|list[ReferencedItem]:
    """
    This will take in either an object (in the form of a string, reference item or
    mobject) or a list of items in the same supported formats and return either the
    ReferenceItem or a list of ReferencedItems.

    If the given identifier cannot be cast to a ReferencedItem (for example, a node
    type that has no matching trait), the identifier is returned unchanged. This
    keeps `get` usable across the full set of Maya nodes, but callers should be
    prepared for a mixed return type (ReferencedItem or the original input).
    """
    if isinstance(identifier, list):
        return ReferenceList(
            get(sub_identifier)
            for sub_identifier in identifier
        )
    try:
        return ReferencedItem(identifier)
    except (TypeError, RuntimeError):
        return identifier


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

    if parent and isinstance(parent, ReferencedItem):
        parent = parent.full_name()
        kwargs["parent"] = parent

    result = cmds.createNode(node_type, *args, **kwargs)
    if isinstance(result, list):
        return ReferenceList(
            get(node)
            for node in result
        )

    return get(result)


def selected(**kwargs) -> list[ReferencedItem]:
    """
    This will return the current selection as a list of ReferencedItems.
    """
    return ReferenceList(
        get(node)
        for node in cmds.ls(selection=True, long=True, **kwargs)
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
    counter = 0
    proposed_name = name

    while cmds.objExists(proposed_name):
        counter += 1
        proposed_name = f"{name}{counter}"

    return proposed_name
