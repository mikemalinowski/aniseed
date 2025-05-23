import qtility
from Qt import QtWidgets, QtCore, QtGui


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ButtonWidget(QtWidgets.QWidget):
    """
    This is a simple button widget which allows for a callable to be passed. When the
    user clicks the button the callable is instigated.
    """
    changed = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, button_name, func, parent=None):
        super(ButtonWidget, self).__init__(parent=parent)

        # -- Store our input values
        self._func = func

        # -- Define our base layout
        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )

        # -- Add our colour button
        self.button = QtWidgets.QPushButton(button_name)
        self.layout().addWidget(self.button)

        # -- Hook up the events
        self.button.clicked.connect(self.instigate)

    # ----------------------------------------------------------------------------------
    def instigate(self):
        self._func()
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    # noinspection PyMethodMayBeStatic
    def get_value(self):
        return None

    # ----------------------------------------------------------------------------------
    def set_value(self, v):
        pass
