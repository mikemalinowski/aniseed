from maya import cmds


def add_to(nodes: str or list[str], set_name: str) -> None:
    """
    This will add the given object or objects to the set with the given
    name. Note, this will create the set if one does not exist.

    Args:
        nodes: A node or list of nodes to add to the set with the given
            name.

        set_name: The name of the set to add the nodes to
    """
    # -- Check we have a set
    if cmds.objExists(set_name):
        if not cmds.nodeType(set_name) == 'objectSet':
            raise Exception(f"{set_name} is not a set!")
    else:
        cmds.sets(name=set_name, empty=True)

    cmds.sets(
        nodes,
        add=set_name,
    )
