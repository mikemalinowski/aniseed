import qute
from crosswalk import app


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ObjectList(qute.QWidget):
    """
    This shows a list of items where the user can add to it and define the order
    the items appear in the list
    """

    changed = qute.Signal()
    moved_up = qute.Signal(str)
    moved_down = qute.Signal(str)
    removed = qute.Signal(str)
    added = qute.Signal(qute.QListWidgetItem)

    # ----------------------------------------------------------------------------------
    def __init__(self, default_items=None, button_size=30, parent=None):
        super(ObjectList, self).__init__(parent=parent)

        # -- Store our input values
        self._button_size = button_size

        # -- Define our base layout
        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QHBoxLayout(),
            ),
        )

        # -- Add our colour button
        self.list_widget = qute.QListWidget()
        self.layout().addWidget(self.list_widget)

        self.button_layout = qute.QVBoxLayout()

        self.add_button = qute.QPushButton("+")
        self.remove_button = qute.QPushButton("-")
        self.up_button = qute.QPushButton("Up")
        self.down_button = qute.QPushButton("Dn")

        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.remove_button)
        self.button_layout.addWidget(self.up_button)
        self.button_layout.addWidget(self.down_button)
        self.layout().addLayout(self.button_layout)

        self.button_layout.addSpacerItem(
            qute.QSpacerItem(
                10,
                0,
                qute.QSizePolicy.Expanding,
                qute.QSizePolicy.Expanding,
            ),
        )

        # -- Ensure we are initialized correctly
        self.update_size()

        # -- Add any default items
        if default_items:
            for item in default_items:

                item = qute.QListWidgetItem(item)
                self.list_widget.addItem(item)
                self.added.emit(item)

        # -- Hook up the events
        self.add_button.clicked.connect(self.add)
        self.remove_button.clicked.connect(self.remove)
        self.up_button.clicked.connect(self.move_up)
        self.down_button.clicked.connect(self.move_down)

    # ----------------------------------------------------------------------------------
    def clear(self):
        self.list_widget.clear()

    # ----------------------------------------------------------------------------------
    def add(self):
        for item in app.selection.selected():
            item = qute.QListWidgetItem(item)
            self.list_widget.addItem(item)
            self.added.emit(item)

        self.changed.emit()
        # self.added.emit("")

    # ----------------------------------------------------------------------------------
    def remove(self):
        if not self.list_widget.currentItem():
            return

        self.list_widget.takeItem(
            self.list_widget.currentRow(),
        )

        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def move_up(self):

        if not self.list_widget.currentItem():
            return

        # -- Get the index of the process we want to shift
        index_to_shift = self.list_widget.currentRow()

        # -- Remove the process from the list
        item = self.list_widget.takeItem(index_to_shift)

        # -- Re-insert it one level less (or the same level if its at the top
        # -- of the list already)
        shift_by = min(
            index_to_shift - 1,
            self.list_widget.count(),
        )

        self.list_widget.insertItem(
            shift_by,
            item,
        )
        self.list_widget.setCurrentRow(shift_by)
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def move_down(self):

        if not self.list_widget.currentItem():
            return

        # -- Get the index of the process we want to shift
        index_to_shift = self.list_widget.currentRow()

        # -- Remove the process from the list
        item = self.list_widget.takeItem(index_to_shift)

        # -- Re-insert it one level less (or the same level if its at the top
        # -- of the list already)
        shift_by = max(
            index_to_shift + 1,
            0,
        )
        self.list_widget.insertItem(
            shift_by,
            item,
        )
        self.list_widget.setCurrentRow(shift_by)
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def update_size(self):
        buttons = [
            self.add_button,
            self.remove_button,
            self.up_button,
            self.down_button,
        ]

        for button in buttons:
            button.setMinimumHeight(self._button_size)
            button.setMinimumWidth(self._button_size)
            button.setMaximumHeight(self._button_size)
            button.setMaximumWidth(self._button_size)

    # ----------------------------------------------------------------------------------
    def get_value(self):

        result = list()

        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            result.append(item.text())

        return result

    # ----------------------------------------------------------------------------------
    def set_value(self, v):

        for item in v or list():
            self.list_widget.addItem(item)

        self.changed.emit()


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class TextList(ObjectList):

    # ----------------------------------------------------------------------------------
    def __init__(self, button_size=30, parent=None):
        super(TextList, self).__init__(parent=parent)

    # ----------------------------------------------------------------------------------
    def add(self, value=None):

        if not value:
            value = qute.utilities.request.text(
                title="Add String",
                label="Type in the string you want to add",
                parent=self,
            )

        if not value:
            return

        item = qute.QListWidgetItem(value)
        self.list_widget.addItem(item)
        self.added.emit(item)
        self.changed.emit()
