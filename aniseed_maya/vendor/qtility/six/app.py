from PySide6 import QtWidgets

# ------------------------------------------------------------------------------
def get(*args, **kwargs) -> QtWidgets.QApplication:
    """
    This will return the QApplication instance if one is available, otherwise
    it will create one

    Args:

    Returns:
        A qapplication instance
    """
    q_app: QtWidgets.QApplication = QtWidgets.QApplication.instance()

    if not q_app:
        q_app = QtWidgets.QApplication([])

    return q_app
