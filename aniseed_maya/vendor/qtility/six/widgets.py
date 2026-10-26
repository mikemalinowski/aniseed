"""
This holds a set of small helper functions
"""
import typing
from PySide6 import QtWidgets
from . import layouts


# ------------------------------------------------------------------------------
def addLabel(
        widget: QtWidgets.QWidget,
        label: typing.AnyStr,
        min_label_width: int or None = None,
        slim: bool = True,
) -> QtWidgets.QHBoxLayout:
    """
    Adds a label to the widget, returning a layout with the label
    on the left and the widget on the right.

    Args:
        widget (QtWidgets.QWidget): the widget
        label (typing.AnyStr): the label
        min_label_width (int or None): the minimum width of the label
        slim: Whether the layout should be slimified or not (no margins)

    Returns:
        The horizontal layout containing the label
    """
    label = QtWidgets.QLabel(label)

    if slim:
        layout = layouts.slimify(QtWidgets.QHBoxLayout())

    else:
        layout = QtWidgets.QHBoxLayout()

    # -- Apply the min label width if required
    if min_label_width:
        label.setMinimumWidth(min_label_width)

    layout.addWidget(label)
    layout.addSpacerItem(
        QtWidgets.QSpacerItem(
            10,
            0,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        ),
    )
    layout.addWidget(widget)

    layout.setStretch(
        2,
        1,
    )

    return layout


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming
def getComboIndex(
        combo_box: QtWidgets.QComboBox,
        label: typing.AnyStr,
        ignore_casing: bool = False,
) -> int:
    """
    This will return the index of the first matching label within a combo
    box widget.

    If no label is found 0 is returned

    Args:
        combo_box (QtWidgets.QComboBox): the combo box to iterate over
        label (typing.AnyStr): the label to search for within the combo box
        ignore_casing (bool): whether to ignore casing when searching for the label
    Returns:
        The index of the item in the combo box. If there is no item
        then 0 is returned
    """
    # -- Convert the label to lower case if we're ignoring casing
    label = label if not ignore_casing else label.lower()

    # -- Cycling our combo box and test the string
    for i in range(combo_box.count()):

        # -- Get the current item text, and lower the casing if we're
        # -- ignoring the casing. This means we're testing both sides
        # -- of the argument in lower case
        combo_text = combo_box.itemText(i)
        combo_text = combo_text if not ignore_casing else combo_text.lower()

        if combo_text == label:
            return i

    return 0


# ------------------------------------------------------------------------------
def setComboByText(combo_box, label, ignore_casing=False):
    """
    This will return the index of the first matching label within a combo
    box qwidget.

    If no label is found 0 is returned

    :param combo_box: Widget to iterate through
    :type combo_box: QComboBox

    :param label: The combo label to match against
    :type label: str

    :param ignore_casing: If true, all text matching will be done with no
        consideration of capitalisation. The default is False.
    :type ignore_casing: bool

    :return: int
    """
    idx = getComboIndex(combo_box, label, ignore_casing=ignore_casing)
    combo_box.setCurrentIndex(idx)

