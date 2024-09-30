import os
import qute

from .. import resources


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class FilepathSelector(qute.QWidget):
    """
    This is a selector field that exposes buttons to make it easier
    to fill the field based on the selection
    """
    changed = qute.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, default_value="", button_size=30, parent=None):
        super(FilepathSelector, self).__init__(parent=parent)

        # -- Store our input values
        self._button_size = button_size

        # -- Define our base layout
        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QHBoxLayout(),
            ),
        )

        # -- Add our colour button
        self.text_field = qute.QLineEdit(default_value)
        self.layout().addWidget(self.text_field)

        # -- Add the buttons
        self.set_filepath_button = self.icon_button("...")
        self.show_filepath_button = self.icon_button(resources.get("select.png"))

        self.layout().addWidget(self.set_filepath_button)
        self.layout().addWidget(self.show_filepath_button)

        # -- Ensure we are initialized correctly
        self.update_size()

        # -- Hook up the events
        self.set_filepath_button.clicked.connect(self.set_filepath)
        self.show_filepath_button.clicked.connect(self.show_filepath)
        self.text_field.textChanged.connect(self.changed)

    # ----------------------------------------------------------------------------------
    def icon_button(self, icon_path):

        button = qute.QPushButton()
        button.setIcon(
            qute.QIcon(
                icon_path,
            ),
        )
        button.setIconSize(
            qute.QSize(
                self._button_size,
                self._button_size,
            ),
        )
        return button

    # ----------------------------------------------------------------------------------
    def set_filepath(self):

        filepath = qute.utilities.request.filepath(
            title="Set Export Path",
            filter_="*.fbx (*.fbx)",
            save=True,
        )

        if not filepath:
            return

        self.set_value(
            filepath,
        )

    # ----------------------------------------------------------------------------------
    def show_filepath(self):

        if not self.text_field.text():
            return

        path = self.text_field.text().replace("/", "\\")

        if not os.path.exists(path):
            path = os.path.dirname(path)

        os.system(
            f"explorer.exe /select, \"{path}\""
        )

    # ----------------------------------------------------------------------------------
    def update_size(self):
        buttons = [
            self.set_filepath_button,
            self.show_filepath_button,
        ]

        for button in buttons:
            button.setMinimumHeight(self._button_size)
            button.setMinimumWidth(self._button_size)
            button.setMaximumHeight(self._button_size)
            button.setMaximumWidth(self._button_size)

        # self.text_field.setMinimumHeight(self._button_size+20)
        self.text_field.setStyleSheet("min-height: 30px;")

    # ----------------------------------------------------------------------------------
    def get_value(self):
        return self.text_field.text()

    # ----------------------------------------------------------------------------------
    def set_value(self, v):
        self.text_field.setText(v)
        self.changed.emit()
