from maya import cmds


def unique(name):
    """
    Returns a unique version of the given name by appending a number
    to the end
    """
    base_name = name
    counter = 1

    while cmds.objExists(name):
        name = f"{base_name}{counter}"
        counter += 1

    return name
