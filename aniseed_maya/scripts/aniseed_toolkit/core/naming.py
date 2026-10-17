"""
Helpers for generating unique node names.
"""
import mref


def unique(name):
    """
    Returns a name which no node in the scene has. If the given name is
    free it is returned unchanged, otherwise a number is appended, counting
    up from 1 (name1, name2, ...).

    Args:
        name: The name to make unique

    Returns:
        The unique name
    """
    base_name = name
    counter = 1

    while mref.objExists(name):
        name = f"{base_name}{counter}"
        counter += 1

    return name
