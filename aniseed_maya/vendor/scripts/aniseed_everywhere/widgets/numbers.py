import qute


# --------------------------------------------------------------------------------------
class LimitedInteger(qute.QSpinBox):

    # ----------------------------------------------------------------------------------
    def __init__(self, minimum=None, maximum=None, parent=None):
        super(LimitedInteger, self).__init__(parent=parent)

        if minimum:
            self.setMinimum(minimum)

        if maximum:
            self.setMaximum(maximum)
