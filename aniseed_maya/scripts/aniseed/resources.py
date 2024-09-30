import os
import functools


# --------------------------------------------------------------------------------------
@functools.lru_cache()
def get(resource_name: str) -> str:
    """
    Returns a file from the _res directory.

    Args:
        resource_name:

    :return:
    """
    return os.path.join(
        os.path.dirname(__file__),
        '_res',
        resource_name,
    )
