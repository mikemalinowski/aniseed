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
