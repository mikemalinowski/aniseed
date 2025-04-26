import os
import aniseed_toolkit
from Qt import QtCore, QtWidgets, QtGui


# noinspection PyUnresolvedReferences
class ShapeSelector(QtWidgets.QComboBox):
    """
    This will show a combo box with the given items for the user to select one
    """

    def __init__(self, default_item, parent=None):
        super(ShapeSelector, self).__init__(parent=parent)

        current_index = 0

        shape_list = [
            os.path.basename(shape).split(".")[0]
            for shape in aniseed_toolkit.run("Get Shape List") or list()
        ]

        for iterative_idx, item in enumerate(shape_list):
            self.addItem(item)

            if item == default_item:
                current_index = iterative_idx

        self.setCurrentIndex(current_index)
