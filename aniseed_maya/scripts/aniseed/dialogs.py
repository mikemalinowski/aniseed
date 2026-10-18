"""
Small user dialogs used by components: asking for a count, and clearing,
saving and loading option data as json files.
"""
import json
import os

import qtility
import crosswalk


def request_count(count, title: str, message: str) -> int:
    """
    Returns the given count, or if it is None, asks the user for it.
    """
    if count is None:
        count = int(qtility.request.text(title=title, message=message))
    return count


def _scene_directory() -> str:
    """
    Returns the directory of the currently open scene file
    """
    return os.path.dirname(crosswalk.scene.path())


def clear_option(option, title: str, message: str, empty_value) -> None:
    """
    Asks the user to confirm, and if they do, sets the option to the
    given empty value.

    Args:
        option: The component option to clear
        title: The title of the confirmation dialog
        message: The message shown in the confirmation dialog
        empty_value: The value to set the option to
    """
    if not qtility.request.confirmation(title=title, message=message):
        return

    option.set(empty_value)


def save_json_file(title: str, get_data: callable) -> None:
    """
    Asks the user for a file path and writes the data to it as json.

    Args:
        title: The title of the file dialog
        get_data: Callable returning the data to write. It is only called
            if the user picks a file path.
    """
    filepath = qtility.request.filepath(
        title=title,
        path=_scene_directory(),
        save=True,
    )

    if not filepath:
        return

    data = get_data()

    with open(filepath, "w") as f:
        json.dump(data, f, sort_keys=True, indent=4)


def load_json_file(title: str, option) -> None:
    """
    Asks the user for a json file and sets the option to its contents.

    Args:
        title: The title of the file dialog
        option: The component option to store the loaded data in
    """
    filepath = qtility.request.filepath(
        title=title,
        path=_scene_directory(),
        save=False,
    )

    if not filepath:
        return

    with open(filepath, "r") as f:
        option.set(json.load(f))
