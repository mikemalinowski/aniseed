"""
Selection queries. Library functions should take nodes as arguments; these are
for tools and other code which works on what the user has selected.
"""
from maya import cmds


def first_selected():
    """
    Returns the first selected object.

    Returns:
        The name of the first selected object, as cmds.ls gives it (the
        shortest unique name), or None if nothing is selected
    """
    # -- cmds rather than mref.selected, because callers get the shortest
    # -- unique name, which mref does not provide
    selection = cmds.ls(selection=True)
    if selection:
        return selection[0]
    return None
