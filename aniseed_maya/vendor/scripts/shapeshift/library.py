import os
import json
import functools

from . import constants


# --------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def shape_data(name):
    """
    Returns the shape data for the shape with the given name
    """
    # -- Check if we're an absolute path first
    if os.path.exists(name):
        shape_file = name

    else:
        shape_file = find_shape(name)

    if not shape_file:
        print(f"Could not find shape for {name}")
        return False

    with open(shape_file, 'r') as f:
        return json.load(f)


# --------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def find_shape(name) -> str:
    """
    Looks for the shape with the given name. This will first look at any
    locations defined along the CRAB_PLUGIN_PATHS environment variable
    before inspecting built in shapes.

    :param name: Name of shape to search for
    :type name: str

    :return: Absolute path to shape
    """
    return shape_library().get(name, "")


# --------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def shape_library():
    """
    Returns a list of all the available shapes

    :return: list
    """
    shapes = dict()

    # -- If we have any paths defined by environment
    # -- variables we should add them here
    for package_path in constants.SEARCH_PATHS:

        if not package_path:
            continue

        for root, _, filenames in os.walk(package_path):
            for filename in filenames:
                if filename.lower().endswith(".json"):
                    shapes[filename[:-5]] = os.path.join(
                        root,
                        filename,
                    )

    return shapes
