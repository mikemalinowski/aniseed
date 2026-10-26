import typing
from PySide2 import QtWidgets


def empty(layout: QtWidgets.QLayout) -> None:
    """
    Clears the layout of all its children, removing them entirely.

    Args:
        layout: The layout to empty.

    Returns:
        None
    """
    for i in reversed(range(layout.count())):
        item = layout.takeAt(i)

        if isinstance(item, QtWidgets.QWidgetItem):
            widget = item.widget()
            widget.setParent(None)
            widget.deleteLater()

        elif isinstance(item, QtWidgets.QSpacerItem):
            pass

        else:
            empty(item.layout())


def slimify(layout: QtWidgets.QLayout) -> QtWidgets.QLayout:
    """
    This will apply zero margins and zero spacing to the given layout
    and return the layout.

    Args:
        layout: The layout to apply zero margins and zero spacing to.

    Returns:
        The adjusted layout
    """
    # -- Apply the formatting
    layout.setContentsMargins(
        *[0, 0, 0, 0]
    )
    layout.setSpacing(0)

    return layout


# --------------------------------------------------------------------------
def widgets(layout: QtWidgets.QLayout) -> typing.List[QtWidgets.QWidget]:
    """
    Returns all the child widgets (recursively) within this layout

    :param layout: The layout to empty.
    :type layout: QLayout

    :return: None
    """

    results = list()

    def _getWidgets(layout_):

        for idx in range(layout_.count()):
            item = layout_.itemAt(idx)

            if isinstance(item, QtWidgets.QLayout):
                _getWidgets(item)
                continue

            widget = item.widget()

            if not widget:
                continue

            results.append(widget)

    _getWidgets(layout)

    return results
