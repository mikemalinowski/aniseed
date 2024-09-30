import os
import qute
import json
import functools

from . import resources
from . import user_flow

_MENU_JSON = os.path.join(
    os.path.dirname(__file__),
    "menu.json",
)



# --------------------------------------------------------------------------------------
def create():

    menu = qute.QMenu("Shapeshift")

    with open(_MENU_JSON, "r") as f:
        data = json.load(f)

    return _create_menu(
        data,
        menu,
    )

# --------------------------------------------------------------------------------------
def _create_menu(tool_list, menu):

    for item_data in tool_list:

        # -- If it has some python code, then we consider it an action
        if item_data["type"] == "tool":

            action = menu.addAction(
                qute.QIcon(
                    resources.get(
                        item_data["icon"],
                    ),
                ),
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
            submenu.setIcon(
                qute.QIcon(
                    item_data["icon"],
                ),
            )
            menu.addMenu(submenu)

            _create_menu(item_data["children"], submenu)

        elif item_data["type"] == "separator":
            menu.addSeparator()

        else:
            pass

    return menu


# --------------------------------------------------------------------------------------
def execute_string(execution_string):
    print(f"Should run : {execution_string}")
    exec(execution_string)
