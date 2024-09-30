"""
This module is responsible for generating the menu structure for Callisto
"""
import sys

import qute
import webbrowser
import blackout
import aniseed_everywhere

import maya
import maya.cmds as mc

from aniseed_everywhere.config import title
from . import resources
from . import constants

MENU_NAME = "Aniseed"
MENU_OBJ = "AniseedMenuRoot"

CRITICAL_MODULES = [
    "aniseed",
    "aniseed_everywhere",
    "crosswalk",
    "xstack",
    "xstack_app",
    "bony",
    "shapeshift",
]


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def build_menu():
    """
    This will setup the menu and interface mechanisms for the Crab Rigging
    Tool.

    :return: 
    """

    # -- If the menu already exists, we will delete it to allow
    # -- us to rebuild it
    if mc.menu(MENU_OBJ, exists=True):
        mc.deleteUI(MENU_OBJ)

    # -- Create the new menu for Crab
    new_menu = mc.menu(
        MENU_OBJ,
        label=MENU_NAME,
        tearOff=True,
        parent=maya.mel.eval('$temp=$gMainWindow'),
    )

    _add_menu_item(
        "Aniseed Builder",
        _launch_app,
        icon=aniseed_everywhere.resources.get("icon.png"),
    )

    mc.menuItem(divider=True, parent=new_menu)
    _add_menu_item(
        "Website",
        _menu_goto_website,
        icon=resources.get("website.png"),
    )

    mc.menuItem(divider=True, parent=new_menu)
    _add_menu_item(
        "Reload",
        _menu_reload,
        icon=resources.get("reload.png"),
    )

    mc.menuItem(divider=True, parent=new_menu)
    _add_menu_item(
        "About",
        _menu_show_version_data,
        icon=resources.get("about.png"),
    )

    # -- We specifically only want this menu to be visibile
    # -- in the rigging menu
    cached_menu_set = mc.menuSet(query=True, currentMenuSet=True)
    rigging_menu_set = maya.mel.eval('findMenuSetFromLabel("Rigging")')

    # -- Set our menu to the rigging menu and add it to
    # -- the menu set
    mc.menuSet(currentMenuSet=rigging_menu_set)
    mc.menuSet(addMenu=new_menu)

    # -- Restore the users cached menu set
    mc.menuSet(currentMenuSet=cached_menu_set)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def _add_menu_item(label, callable_func, icon=None, parent=MENU_OBJ):
    return mc.menuItem(
        MENU_OBJ + label.replace(" ", "_"),
        label=label,
        command=callable_func,
        parent=parent,
        image=icon,
    )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def _launch_app(*args, **kwargs):
    mc.evalDeferred("import aniseed;aniseed.app.launch()")


# --------------------------------------------------------------------------------------
# noinspection PyUnusedLocal
def _menu_goto_website(*args, **kwargs):
    webbrowser.open(constants.website)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def _menu_reload(*args, **kwargs):


    for package in CRITICAL_MODULES:
        blackout.drop(package)

    mc.evalDeferred("import aniseed;aniseed.app.launch()")

# --------------------------------------------------------------------------------------
def _menu_show_version_data(*args, **kwargs):

    version_data = []

    for package in CRITICAL_MODULES:

        try:
            version = sys.modules.get(package).__version__
            label = f'{package} : {version}'
            version_data.append(label)

        except AttributeError:
            label = f"{package.rjust(15, ' ')} : No Version Data"

    version_data = "\n".join(version_data)

    author_data = (
        "Developed by Mike Malinowski\n"
        f"{constants.website}\n"
    )

    qute.utilities.request.message(
        title="About Aniseed",
        label=(
            "Aniseed Information\n\n"
            f"{version_data}\n\n"
            f"{author_data}"
        ),
    )
