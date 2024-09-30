import qute


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ColorPicker(qute.QWidget):
    """
    This widget allows for a colour to be selected by the user. The colour is also
    visualually presented to the user
    """

    changed = qute.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, default_colour, size=30, parent=None):
        super(ColorPicker, self).__init__(parent=parent)

        # -- Store our input values
        self._colour = default_colour
        self._size = size

        # -- Define our base layout
        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )

        # -- Add our colour button
        self.button = qute.QPushButton()
        self.layout().addWidget(self.button)

        # -- Ensure we are initialized correctly
        self.update_size()
        self.reflect_colour()

        # -- Hook up the events
        self.button.clicked.connect(self.select_colour)

    # ----------------------------------------------------------------------------------
    def select_colour(self):

        # -- Prompt for a new colour
        new_colour = qute.QColorDialog.getColor(
            qute.QColor(*self._colour),
            parent=self,
            title="Select Colour",
        )

        if not new_colour:
            return

        # -- Store our new colour choice
        self.set_value(
            [
                new_colour.red(),
                new_colour.green(),
                new_colour.blue(),
            ]
        )

    # ----------------------------------------------------------------------------------
    def reflect_colour(self):

        colour_string = ",".join(
            [
                str(v)
                for v in self._colour
            ]
        )

        style = f"background-color: rgb({colour_string});"

        self.button.setStyleSheet(style)

    # ----------------------------------------------------------------------------------
    def update_size(self):

        self.button.setMinimumHeight(self._size)
        self.button.setMinimumWidth(self._size)
        self.button.setMaximumHeight(self._size)
        self.button.setMaximumWidth(self._size)

    # ----------------------------------------------------------------------------------
    def get_value(self):
        return self._colour

    # ----------------------------------------------------------------------------------
    def set_value(self, v):
        self._colour = v
        self.reflect_colour()
        self.changed.emit()