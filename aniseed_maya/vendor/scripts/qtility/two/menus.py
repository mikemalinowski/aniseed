import os
import typing

from PySide2 import QtWidgets
from PySide2 import QtGui


# ------------------------------------------------------------------------------
def create(
        structure: typing.Dict[str, typing.Any],
        parent: QtWidgets.QWidget or None = None,
        name: typing.AnyStr = None,
        icon_paths: typing.List[str] = None,
        icon_map: typing.Dict[str, typing.AnyStr] = None
) -> QtWidgets.QMenu:
    """
    This will generate a menu based on a dictionary structure, whereby
    the key is the label and the value is a function call. You can optionally
    pass an icon path, and any icon found in that location with the same
    name as a key will be used.

    Args:
        structure: Dictionary to generate the menu from. This dictionary
            is built of key value pairs where the key is the label and the value
            can be one of the following:
                * Function : This function will be called when the
                    action is triggered

                * Dictionary : If a dictionary is found as a value then a sub
                    menu is created. You can have any number of nested dictionaries

                * None : If the value is None then a seperator will be added
                    regardless of the key.
        parent: The parent of the menu.
        name: The name of the menu.
        icon_paths: When adding items to the menu, icons with the same
            name as the keys will be looked for in any of these locations. This
            can either be a single string location or a list of locations.
        icon_map: Optional dictionary of specific icons for actions with specific
            names

    Returns:
        QMenu
    """
    if isinstance(parent, QtWidgets.QMenu):
        menu = parent

    else:
        menu = QtWidgets.QMenu(name or '', parent)

    for label, target in structure.items():

        # -- Deal with seperators first
        if not target:
            menu.addSeparator()
            continue

        # -- Now check if we have a sub menu
        if isinstance(target, dict):
            sub_menu = QtWidgets.QMenu(label, menu)

            icon = _icon(label, icon_paths, icon_map)

            if icon:
                sub_menu.setIcon(
                    QtGui.QPixmap(
                        icon,
                    ),
                )

            create(
                structure=target,
                parent=sub_menu,
                name=label,
                icon_paths=icon_paths,
                icon_map=icon_map
            )

            menu.addMenu(
                sub_menu,
            )

            continue

        # -- Finally, check if the target is callable
        if callable(target):

            icon = _icon(label, icon_paths, icon_map)

            if icon:
                # -- Create the menu action
                action = QtWidgets.QAction(
                    QtGui.QIcon(icon),
                    label,
                    menu,
                )

            else:
                # -- Create the menu action
                action: QtWidgets.QAction = QtWidgets.QAction(
                    label,
                    menu,
                )

            # -- Connect the menu action signal/slot
            action.triggered.connect(target)

            # -- Finally add the action to the menu
            menu.addAction(action)

        # -- this allows the user to pre-construct their own actions with more advanced set-ups
        elif isinstance(target, QtWidgets.QAction):
            menu.addAction(target)

    return menu


# ------------------------------------------------------------------------------
def _icon(label, icon_paths, icon_map=None):
    """
    Private function for finding png icons with the label name
    from any of the given icon paths

    :param label: Name of the icon to search for
    :type label: str

    :param icon_paths: single path, or list of paths to check along
    :type icon_paths: str or list(str, str)

    :return: absolute icon path or None
    """
    if icon_map and label in icon_map:
        return icon_map[label]

    for icon_path in icon_paths or list():

        if not icon_path:
            continue

        for filename in os.listdir(icon_path):
            if filename[:-4] == label:
                return os.path.join(
                    icon_path,
                    filename,
                )

    return None
