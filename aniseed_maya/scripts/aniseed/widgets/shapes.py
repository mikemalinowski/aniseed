import qute
import shapeshift


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ShapeSelector(qute.QComboBox):
    """
    This will show a combo box with the given items for the user to select one
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, default_item, parent=None):
        super(ShapeSelector, self).__init__(parent=parent)

        current_index = 0

        for iterative_idx, item in enumerate(shapeshift.library.shape_library()):
            self.addItem(item)

            if item == default_item:
                current_index = iterative_idx

        self.setCurrentIndex(current_index)
