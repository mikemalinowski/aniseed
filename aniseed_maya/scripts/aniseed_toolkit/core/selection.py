"""
Selection queries. Library functions should take nodes as arguments; these are
for tools and other code which works on what the user has selected.
"""
from maya import cmds


def first_selected():
    """
    This will return the first selected object
    """
    selection = cmds.ls(selection=True)
    if selection:
        return selection[0]
    return None
