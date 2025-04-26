import typing
from PySide2 import QtWidgets
from . import app


# ------------------------------------------------------------------------------
def message(
        title: typing.AnyStr = 'Text Request',
        message: typing.AnyStr = '',
        parent: QtWidgets.QWidget or None = None,
        **kwargs
) -> None:
    """
    Quick and easy access for getting text input. You do not have to have a
    QApplication instance, as this will look for one.

    Args:
        title (typing.AnyStr, optional): Title of the message.
        message (typing.AnyStr, optional): Text to show in the dialog.
        parent (QtWidgets.QWidget, optional): Parent widget.

    :return: str, or None
    """
    # -- Ensure we have a QApplication instance
    q_app = app.get()

    answer = QtWidgets.QMessageBox.information(
        parent,
        title,
        message,
    )


# ------------------------------------------------------------------------------
def confirmation(
        title: typing.AnyStr = 'Text Request',
        message: typing.AnyStr = '',
        parent: QtWidgets.QWidget or None = None,
        **kwargs
) -> bool:
    """
    Quick and easy access for getting text input. You do not have to have a
    QApplication instance, as this will look for one.

    Args:
        title (typing.AnyStr, optional): Title of the message.
        message (typing.AnyStr, optional): Text to show in the dialog.
        parent (QtWidgets.QWidget, optional): Parent widget.

    Returns:
        True if the user clicked anything other than cancel
    """
    # -- Ensure we have a QApplication instance
    q_app = app.get()

    answer = QtWidgets.QMessageBox.warning(
        parent,
        title,
        message,
        QtWidgets.QMessageBox.Yes,
        QtWidgets.QMessageBox.No,
    )

    if answer == QtWidgets.QMessageBox.Yes:
        return True

    return False


# ------------------------------------------------------------------------------
def text(
        title: typing.AnyStr = 'Text Request',
        message: typing.AnyStr = '',
        parent: QtWidgets.QWidget or None = None,
        **kwargs
) -> typing.AnyStr or None:
    """
    Quick and easy access for getting text input. You do not have to have a
    QApplication instance, as this will look for one.

    Args:
        title (typing.AnyStr, optional): Title of the message.
        message (typing.AnyStr, optional): Text to show in the dialog.
        parent (QtWidgets.QWidget, optional): Parent widget.
    Returns:
        String value if user pressed ok, or None if user cancelled
    """
    # -- Ensure we have a QApplication instance
    q_app = app.get()

    # -- Get the text
    name, ok = QtWidgets.QInputDialog.getText(
        parent,
        title,
        message,
        **kwargs
    )

    if not ok:
        return None

    return name


# ------------------------------------------------------------------------------
def filepath(
        title: typing.AnyStr = 'Text Request',
        save: bool = True,
        path: typing.AnyStr = '',
        filter_: typing.AnyStr = '* (*.*)',
        parent: QtWidgets.QWidget or None = None,
        **kwargs
) -> typing.AnyStr or None:
    """
    Quick and easy access for getting text input. You do not have to have a
    QApplication instance, as this will look for one.

    Args:
        title (typing.AnyStr, optional): Title of the message.
        save (bool, optional): If true a save dialog is opened (default) otherwise an
            open dialog is opened.
        path (typing.AnyStr, optional): Default path to open the dialog at
        filter_ (typing.AnyStr, optional): file filter string
        parent (QtWidgets.QWidget, optional): Parent widget.

    Returns:
        The given filepath if the user selected one. None if they cancelled.
    """

    # -- Ensure we have a q application instance
    q_app = app.get()

    # -- Ask for the editor location
    func = QtWidgets.QFileDialog.getOpenFileName

    if save:
        func = QtWidgets.QFileDialog.getSaveFileName

    value, _ = func(
        parent,
        title,
        path,
        filter_,
    )

    return value


# ------------------------------------------------------------------------------
def folderpath(
        title: typing.AnyStr = 'Folder Request',
        path: typing.AnyStr = '',
        parent: QtWidgets.QWidget or None = None
) -> typing.AnyStr or None:
    """
    Quick function for requesting a folder path

    Args:
        title (typing.AnyStr, optional): Title of the message.
        path (typing.AnyStr, optional): Default path to open the dialog at
        parent: QtWidgets.QWidget, optional: Parent widget.

    Returns:
        The given path if the user selected one. None if they cancelled.
    """
    q_app = app.get()

    return QtWidgets.QFileDialog.getExistingDirectory(
        parent,
        title,
        path,
        QtWidgets.QFileDialog.ShowDirsOnly,
    )


# ------------------------------------------------------------------------------
def item(
        items: typing.List[typing.AnyStr],
        title: typing.AnyStr = 'Text Request',
        message: typing.AnyStr = '',
        parent: QtWidgets.QWidget or None = None,
        *args,
        **kwargs
) -> typing.AnyStr or None:
    """
    Quick and easy access for getting text input. You do not have to have a
    QApplication instance, as this will look for one.

    Args:
        items (typing.List[typing.AnyStr]): List of items to show in the dialog.
        title (typing.AnyStr, optional): Title of the message.
        message (typing.AnyStr, optional): Text to show in the dialog.
        parent (QtWidgets.QWidget, optional): Parent widget.

    Returns:
        The string entry the user selected or None if they cancelled.
    :return: str, or None
    """
    # -- Ensure we have a QApplication instance
    q_app = app.get()

    # -- Get the text
    name, ok = QtWidgets.QInputDialog.getItem(
        parent,
        title,
        message,
        items,
        *args,
        **kwargs
    )

    if not ok:
        return None

    return name
