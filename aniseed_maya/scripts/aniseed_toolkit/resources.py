import os

resource_root_paths = [
    os.path.join(
        os.path.dirname(__file__),
        "_resources",
    ),
]

def get(resource_path: str) -> str:
    """
    This will return the absolute path to a resource relative
    to the _resources folder
    """
    for resource_root in resource_root_paths:
        resolved_resource_path = os.path.join(resource_root, resource_path)
        print("testing for resolved_resource_path :: %s" % resolved_resource_path)
        if os.path.exists(resolved_resource_path):
            return resolved_resource_path

    return os.path.join(resource_root_paths[0], resource_path)


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


def register_resource_path(resource_path: str):
    if resource_path not in resource_root_paths:
        resource_root_paths.append(resource_path)
        print("registered resource path!")
