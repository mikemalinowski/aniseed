import qute


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ItemSelector(qute.QComboBox):
    """
    This will show a combo box with the given items for the user to select one
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, items, default_item, parent=None):
        super(ItemSelector, self).__init__(parent=parent)

        idx_to_apply = 0

        for iterative_idx, item in enumerate(items):
            self.addItem(item)

            if item == default_item:
                idx_to_apply = iterative_idx

        self.setCurrentIndex(idx_to_apply)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class LocationSelector(qute.QComboBox):
    """
    This will show a combo box with the given items for the user to select one
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, config, parent=None):
        super(LocationSelector, self).__init__(parent=parent)

        locations = [
            config.middle,
            config.left,
            config.right,
            config.front,
            config.back,
        ]

        for iterative_idx, item in enumerate(locations):
            self.addItem(item)

        self.setCurrentIndex(0)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class AxisSelector(qute.QComboBox):
    """
    This will show a combo box with the given items for the user to select one
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(AxisSelector, self).__init__(parent=parent)

        for iterative_idx, item in enumerate(["X", "Y", "Z"]):
            self.addItem(item)
