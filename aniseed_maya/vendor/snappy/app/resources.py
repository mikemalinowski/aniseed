import os


def get(resource_path: str) -> str:
    """
    This will return the absolute path to a resource relative
    to the _resources folder
    """
    return os.path.join(
        os.path.dirname(__file__),
        "_resources",
        resource_path,
    )
