from PySide6 import QtCore


# --------------------------------------------------------------------------------------------------
def expandWidth(
        size_to_update: QtCore.QSize,
        size_to_consider: QtCore.QSize,
) -> QtCore.QSize:
    """
    Expands the given size in width to the given size to consider. It will not
    contract the size_to_update.

    Args:
        size_to_update (QtCore.QSize): the size to expand
        size_to_consider (QtCore.QSize): the size to consider

    Returns:
        QtCore.QSize: the expanded size
    """
    return QtCore.QSize(
        max(
            size_to_update.width(),
            size_to_consider.width(),
        ),
        size_to_update.height(),
    )


# --------------------------------------------------------------------------------------------------
def expandHeight(
        size_to_update: QtCore.QSize,
        size_to_consider: QtCore.QSize,
) -> QtCore.QSize:
    """
    Expands the given size in height to the given size to consider. It will not
    contract the size_to_update.

    Args:
        size_to_update (QtCore.QSize): the size to expand
        size_to_consider (QtCore.QSize): the size to consider

    Returns:
        QtCore.QSize: the expanded size
    """
    return QtCore.QSize(
        size_to_update.width(),
        max(
            size_to_update.height(),
            size_to_consider.height(),
        ),
    )


# --------------------------------------------------------------------------------------------------
def addWidth(
        size_to_update: QtCore.QSize,
        size_to_consider: QtCore.QSize,
) -> QtCore.QSize:
    """
    Adds the width of the given size_to_consider to the size_to_update
    """
    return QtCore.QSize(
        size_to_update.width() + size_to_consider.width(),
        size_to_update.height(),
    )


# --------------------------------------------------------------------------------------------------
def addHeight(
        size_to_update: QtCore.QSize,
        size_to_consider: QtCore.QSize,
) -> QtCore.QSize:
    """
    Adds the height of the given size_to_consider to the size_to_update
    """
    return QtCore.QSize(
        size_to_update.width(),
        size_to_update.height() + size_to_consider.height(),
    )
