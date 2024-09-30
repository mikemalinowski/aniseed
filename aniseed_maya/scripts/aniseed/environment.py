import os
import shapeshift
import aniseed_everywhere


# --------------------------------------------------------------------------------------
def initialize_environment():

    # -- Aniseed is built upon aniseed_everywhere, and therefore we will add our
    # -- own component path by using the environment variable protocol
    components_path = os.path.join(
        os.path.dirname(__file__),
        "components",
    ).replace("\\", "/")

    # -- Ensure we read out any existing paths before we add our own. Note that this
    # -- only modifies the path for the interpreters instance, not the system.
    paths = os.environ.get(aniseed_everywhere.constants.RIG_COMPONENTS_PATHS_ENVVAR, "")
    paths += f",{components_path}"

    os.environ[aniseed_everywhere.constants.RIG_COMPONENTS_PATHS_ENVVAR] = paths

    # -- Add our shapes directory to shapeshift - this makes any aniseed shapes
    # -- be available through shapeshift
    shape_path = os.path.join(
        os.path.dirname(__file__),
        "_res",
        "shapes",
    ).replace("\\", "/")

    shape_paths = os.environ.get(shapeshift.constants.SHAPESHIFT_SEARCH_PATH_ENVVAR, "")
    shape_paths += f",{shape_path}"
    os.environ[shapeshift.constants.SHAPESHIFT_SEARCH_PATH_ENVVAR] = shape_paths

    return True
