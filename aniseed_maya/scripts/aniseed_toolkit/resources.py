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


def contents(resource_path: str) -> list[str]:
    """
    This will return the list of absolute filepaths from
    within the given resource location
    """
    search_root = os.path.join(
        os.path.dirname(__file__),
        "_resources",
        resource_path,
    )

    results = []

    for root, _, files in os.walk(search_root):
        for filename in files:
            results.append(
                os.path.join(
                    root,
                    filename,
                )
            )

    return results
