from Qt import QtWidgets, QtCore, QtGui


# --------------------------------------------------------------------------------------
class LimitedInteger(QtWidgets.QSpinBox):

    # ----------------------------------------------------------------------------------
    def __init__(self, minimum=None, maximum=None, parent=None):
        super(LimitedInteger, self).__init__(parent=parent)

        if minimum:
            self.setMinimum(minimum)

        if maximum:
            self.setMaximum(maximum)


class VectorWidget(QtWidgets.QWidget):

    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(VectorWidget, self).__init__(parent=parent)

        self.setLayout(QtWidgets.QHBoxLayout())

        self.x = QtWidgets.QDoubleSpinBox(self)
        self.y = QtWidgets.QDoubleSpinBox(self)
        self.z = QtWidgets.QDoubleSpinBox(self)

        self.layout().addWidget(self.x)
        self.layout().addWidget(self.y)
        self.layout().addWidget(self.z)

        self.x.valueChanged.connect(self._emit_change)
        self.y.valueChanged.connect(self._emit_change)
        self.z.valueChanged.connect(self._emit_change)

    def set_value(self, value):
        self.x.setValue(value[0])
        self.y.setValue(value[1])
        self.z.setValue(value[2])
        self.changed.emit()

    def get_value(self):
        return [
            self.x.value(),
            self.y.value(),
            self.z.value(),
        ]

    def _emit_change(self, *args):
        self.changed.emit()

