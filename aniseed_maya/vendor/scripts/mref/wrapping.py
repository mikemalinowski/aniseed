from maya import cmds

from . import core, ReferenceList


def wrapped_cmds(func):
    """
    This will take in a command and resolve all the arguments
    into string names suitable for maya.cmds and then return
    the output as mref items. This means that a developer can
    interchangably use cmds and mref together.
    """
    def _inner(*args, **kwargs):
        args = list(args)

        for idx, arg in enumerate(args):
            args[idx] = _convert_to_cmds(arg)

        for k, v in kwargs.items():
            kwargs[k] = _convert_to_cmds(v)

        result = getattr(cmds, func)(*args, **kwargs)

        return _convert_to_mref(result)
    return _inner


def _convert_to_mref(variable):
    """
    This will convert object names etc to mrefs and lists
    of object names to ReferenceLists of ReferencedItems.

    Values that cannot be cast to a ReferencedItem (e.g. unsupported node types,
    or non-node return values like ints/floats/bools from cmds queries) are
    returned unchanged, mirroring `core.get`'s fallback behavior.
    """
    if isinstance(variable, core.ReferenceList):
        return variable

    if isinstance(variable, core.ReferencedItem):
        return variable

    if isinstance(variable, dict):
        for k, v in variable.items():
            variable[k] = _convert_to_mref(v)
        return variable

    if isinstance(variable, list):
        return ReferenceList(
            [
                _convert_to_mref(sub_variable)
                for sub_variable in variable
            ]
        )

    return core.get(variable)


def _convert_to_cmds(variable):
    if isinstance(variable, core.ReferencedItem):
        return variable.full_name()

    if isinstance(variable, core.ReferenceList):
        return variable.full_names()

    return variable
