from Qt import QtCore, QtWidgets, QtGui

from .. import host


# noinspection PyUnresolvedReferences
class ShapeSelector(QtWidgets.QComboBox):
    """
    This will show a combo box with the given items for the user to select one.
    The available shapes are provided by the current host.
    """

    def __init__(self, default_item, parent=None):
        super().__init__(parent=parent)

        current_index = 0

        host_app = host.get()
        shape_list = host_app.control_shapes() if host_app else list()

        for iterative_idx, item in enumerate(shape_list):
            self.addItem(item)

            if item == default_item:
                current_index = iterative_idx

        self.setCurrentIndex(current_index)
