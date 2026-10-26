"""
This module attempts to access widgets and values in a blind manor - allowing
you to extract the most common forms of data from them. This is particularly
useful when you want to represent values through an interface without hard-
coding what they are.
"""
import typing
from PySide6 import QtWidgets

_NUMERIC_UI_MAX = 9**9
_NUMERIC_UI_MIN = _NUMERIC_UI_MAX * -1


def qwidget(
        value: typing.Any,
        label: str = '',
        tooltip: str = '',
        options: typing.Any = None,
) -> QtWidgets.QWidget or None:
    """
    Given the data type of the value, this will make a guess at the best
    fit ui element to represent that value.

    Args:
        value: The value you want to represent through a widget
        label: The label of the widget (if that widget supports a label)
        tooltip: The tooltip of the widget (if that widget supports a tooltip)
        options: Any widget specific options

    Returns:
        A QWidget of a type relevant to the value given.
    """

    if type(value) == type:
        value_type = value
    else:
        value_type = type(value)

    # -- Determine the type of the value coming in
    value_type = type(value)

    if value_type is bool:
        derived = QtWidgets.QCheckBox(label)
        derived.setChecked(value)
        derived.setToolTip(tooltip)
        return derived

    if isinstance(value, str):

        # -- If we are given options for a string, then we show it as a
        # -- combo rather than a string entry
        if options:
            derived = QtWidgets.QComboBox()
            derived.setToolTip(tooltip)

            default_idx = 0

            for idx, item in enumerate(options):
                derived.addItem(item)

                # -- If we have a match, store the idx so we can
                # -- set the value to it
                if item == value:
                    default_idx = idx

            derived.setCurrentIndex(default_idx)

        else:
            derived = QtWidgets.QLineEdit()
            derived.setText(value)
            derived.setToolTip(tooltip)

        return derived

    if value_type is float:
        derived = QtWidgets.QDoubleSpinBox()
        derived.setMaximum(_NUMERIC_UI_MAX)
        derived.setMinimum(_NUMERIC_UI_MIN)
        derived.setDecimals(4)
        derived.setValue(value)
        derived.setToolTip(tooltip)
        return derived

    if value_type is int:
        derived = QtWidgets.QSpinBox()
        derived.setMaximum(_NUMERIC_UI_MAX)
        derived.setMinimum(_NUMERIC_UI_MIN)
        derived.setValue(value)
        derived.setToolTip(tooltip)
        return derived

    if value_type in [list, tuple]:
        derived = QtWidgets.QComboBox()
        derived.setToolTip(tooltip)

        for item in value:
            derived.addItem(item)

        return derived

    elif value_type is dict:
        widget = QtWidgets.QComboBox()
        widget.setToolTip(tooltip)

        for k, v in value.items():
            widget.addItem(k, userData=v)
        return widget

    else:
        return None


# noinspection PyPep8Naming,PyUnresolvedReferences
def value(widget: QtWidgets.QWidget) -> typing.Any:
    """
    Given a QWidget it will call the widgets specific method to return
    the likely value represented by that widget.

    Args:
        widget: QWidget to derive the value from

    Returns:
        The value from the widget
    """
    if isinstance(widget, QtWidgets.QAbstractSpinBox):
        return widget.value()

    if isinstance(widget, QtWidgets.QLineEdit):
        return widget.text()

    if isinstance(widget, QtWidgets.QComboBox):
        data = widget.itemData(widget.currentIndex())
        return data or widget.currentText()

    if isinstance(widget, QtWidgets.QAbstractButton):
        return widget.isChecked() if widget.isCheckable() else widget.isDown()

    if hasattr(widget, "get_value"):
        return widget.get_value()

    return None


# noinspection PyPep8Naming,PyUnresolvedReferences
def apply(widget: QtWidgets.QWidget, value: typing.Any) -> bool:
    """
    This will attempt to apply/set the given widget to the
    given value.

    Args:
        widget: The widget to apply the value to
        value: The value to apply the widget to

    Returns:
        True if the setting of the widget value was successful
    """
    if isinstance(widget, QtWidgets.QAbstractSpinBox):
        widget.setValue(float(value))
        return True

    if isinstance(widget, QtWidgets.QLineEdit):
        widget.setText(str(value))
        return True

    if isinstance(widget, QtWidgets.QComboBox):
        for i in range(widget.count()):
            if widget.itemText(i) == str(value):
                widget.setCurrentIndex(i)
                return True

    if isinstance(widget, QtWidgets.QAbstractButton):
        widget.setChecked(bool(value))
        return True

    if isinstance(widget, QtWidgets.QListWidget):
        if isinstance(value, list):
            for item in value:
                widget.addItem(item)
            return True

    if hasattr(widget, "set_value"):
        widget.set_value(value)
        return True

    return False


# noinspection PyPep8Naming,PyUnresolvedReferences
def connect(widget: QtWidgets.QWidget, callback: typing.Callable) -> bool:
    """
    This is a blind approach to connecting the most likely value change
    event of a given widget to the given callback.

    Note: Because of the nature of signals, they can give a variety of
    different arguments during the signal call. For that reason it is
    highly recommended to utilise *args, **kwargs within the callback
    if you do not know exactly which signal will be connected.

    Args:
        widget: The widget expected to emit the change signal
        callback: The callback/function which should be called upon
            a value changed event

    Returns:
        True on successful connection, False otherwise.
    """
    if isinstance(widget, QtWidgets.QLineEdit):
        widget.textChanged.connect(callback)
        return True

    if isinstance(widget, QtWidgets.QAbstractSpinBox):
        widget.valueChanged.connect(callback)
        return True

    if isinstance(widget, QtWidgets.QComboBox):
        widget.currentIndexChanged.connect(callback)
        return True

    if isinstance(widget, QtWidgets.QAbstractButton):
        widget.clicked.connect(callback)
        return True

    if hasattr(widget, "changed"):
        widget.changed.connect(callback)
        return True

    return False
