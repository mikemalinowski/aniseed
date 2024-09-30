import os

SHAPESHIFT_SEARCH_PATH_ENVVAR = "SHAPESHIFT_SHAPE_LIBRARY_PATHS"

_user_paths = os.environ.get(
    SHAPESHIFT_SEARCH_PATH_ENVVAR,
    ""
).split(",")

SEARCH_PATHS = [
    user_path
    for user_path in _user_paths
    if user_path
]


SEARCH_PATHS.append(
    os.path.join(
            os.path.dirname(__file__),
            "data",
        )
)
