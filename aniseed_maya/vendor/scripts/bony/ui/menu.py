import os
import qute
import json
import functools

from .. import utils
from .. import resources

_MENU_JSON = os.path.join(
    os.path.dirname(__file__),
    "menu.json",
)


# --------------------------------------------------------------------------------------
def create():

    menu = qute.QMenu("Bones")
    menu.setTearOffEnabled(True)

    with open(_MENU_JSON, "r") as f:
        data = json.load(f)

    return _create_menu(
        data,
        menu,
    )

# --------------------------------------------------------------------------------------
def _create_menu(tool_list, menu):

    for item_data in tool_list:

        try:
            icon_path = resources.get(
                item_data["icon"],
            )

        except KeyError:
            icon_path = resources.get("mirror.png")

        icon = qute.QIcon(icon_path)

        # -- If it has some python code, then we consider it an action
        if item_data["type"] == "tool":

            action = menu.addAction(
                icon,
                item_data["name"],
            )

            action.triggered.connect(
                functools.partial(
                    execute_string,
                    item_data["python"],
                )
            )

        elif item_data["type"] == "menu":
            submenu = qute.QMenu(item_data["name"])

            submenu.setTearOffEnabled(True)

            menu.addMenu(
                # icon, # -- This causes a type issue, needs investigation
                submenu,
            )

            _create_menu(item_data["children"], submenu)

        elif item_data["type"] == "separator":
            menu.addSeparator()

        else:
            pass

    return menu


# --------------------------------------------------------------------------------------
def execute_string(execution_string):
    print(f"Running : {execution_string}")
    with utils.UndoChunk():
        exec(execution_string)
