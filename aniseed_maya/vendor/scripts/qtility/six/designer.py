import typing
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtWidgets import QWidget


def load(ui_file: typing.AnyStr, parent: QWidget or None = None) -> QWidget or None:
    """
    This will take a ui file built with qt designer and dynamically generate
    a qwidget

    Args:
        ui_file (typing.AnyStr): The absolute path to the ui file to load
        parent (QWidget): The parent widget

    Returns:
        The QWidget representing the ui file
    """
    ui_file = QFile(ui_file)

    if not ui_file.open(QIODevice.ReadOnly):
        return

    loader = QUiLoader()
    widget = loader.load(ui_file, parent)
    ui_file.close()
    return widget
