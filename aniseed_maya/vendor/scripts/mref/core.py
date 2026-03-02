import types
import traceback
import os
import inspect
import factories
from maya import cmds
from maya.api import OpenMaya as om


class Trait:

    priority = 0

    def __init__(self, pointer, item):
        self._pointer = pointer
        self.item = item

    @classmethod
    def can_bind(cls, pointer):
        return False


class TraitLibrary(factories.Factory):

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
        plugins = super(TraitLibrary, self).plugins(include_disabled=include_disabled)
        plugins.sort(key=lambda x: x.priority)
        return plugins

    @classmethod
    def singleton(cls):
        if TraitLibrary._instance is None:
            TraitLibrary._instance = cls()
        return TraitLibrary._instance


class ReferencedItem:

    def __init__(self, item):

        self._pointer = self._resolve_pointer(item)

        self.traits = [
            trait(self._pointer, self)
            for trait in TraitLibrary.singleton().plugins()
            if trait.can_bind(self._pointer)
        ]
        self.func_mapping = dict()

        for trait in self.traits:
            for callable_item in inspect.getmembers(trait):

                if callable_item[0].startswith("_"):
                    continue
                if isinstance(callable_item[1], types.MethodType):
                    self.func_mapping[callable_item[0]] = callable_item[1]
                    self.__dict__[callable_item[0]] = callable_item[1]

    def __repr__(self):
        string = "<"
        if hasattr(self, "name"):
            string += self.name()

        else:
            string += str(self)

        string += " ["
        for trait in self.traits:
            string += f"{trait.__class__.__name__}, "

        return string[:-2] + "]>"

    # def __getattr__(self, attr):
    #     if attr in self.func_mapping:
    #         return self.func_mapping[attr]
    #     traceback.print_stack()
    #     raise AttributeError(f"{self._pointer} does not contain {attr}")

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self._pointer == other.pointer():
            return True
        return False

    def assigned_traits(self):
        return [trait.__name__ for trait in self.traits]

    def print_methods(self):
        for method_name in sorted(self.func_mapping.keys()):
            print(method_name)

    @classmethod
    def _resolve_pointer(cls, item):

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

    def pointer(self):
        return self._pointer
    #
    # def __repr__(self):
    #     return "foo"
    #     return f"{self} [{','.join(self.assigned_traits())}]"

def get(identifier):
    if isinstance(identifier, list):
        return [
            ReferencedItem(sub_identifier)
            for sub_identifier in identifier
        ]
    return ReferencedItem(identifier)


def create(*args, **kwargs):
    result = cmds.createNode(*args, **kwargs)

    if isinstance(result, list):
        return [
            get(node)
            for node in result
        ]
    return get(result)


def selected():
    return [
        get(node)
        for node in cmds.ls(sl=True)
    ]
