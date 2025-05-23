import qtility
from crosswalk import app
from Qt import QtWidgets, QtCore, QtGui


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ObjectList(QtWidgets.QWidget):
    """
    This shows a list of items where the user can add to it and define the order
    the items appear in the list
    """

    changed = QtCore.Signal()
    moved_up = QtCore.Signal(str)
    moved_down = QtCore.Signal(str)
    removed = QtCore.Signal(str)
    added = QtCore.Signal(QtWidgets.QListWidgetItem)

    # ----------------------------------------------------------------------------------
    def __init__(self, default_items=None, button_size=30, parent=None):
        super(ObjectList, self).__init__(parent=parent)

        # -- Store our input values
        self._button_size = button_size

        # -- Define our base layout
        self.setLayout(
            
            qtility.layouts.slimify(
                QtWidgets.QHBoxLayout(),
            ),
        )

        # -- Add our colour button
        self.list_widget = QtWidgets.QListWidget()
        self.layout().addWidget(self.list_widget)

        self.button_layout = QtWidgets.QVBoxLayout()

        self.add_button = QtWidgets.QPushButton("+")
        self.remove_button = QtWidgets.QPushButton("-")
        self.up_button = QtWidgets.QPushButton("Up")
        self.down_button = QtWidgets.QPushButton("Dn")

        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.remove_button)
        self.button_layout.addWidget(self.up_button)
        self.button_layout.addWidget(self.down_button)
        self.layout().addLayout(self.button_layout)

        self.button_layout.addSpacerItem(
            QtWidgets.QSpacerItem(
                10,
                0,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            ),
        )

        # -- Ensure we are initialized correctly
        self.update_size()

        # -- Add any default items
        if default_items:
            for item in default_items:

                item = QtWidgets.QListWidgetItem(item)
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
            item = QtWidgets.QListWidgetItem(item)
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
            value = qtility.request.text(
                title="Add String",
                message="Type in the string you want to add",
                parent=self,
            )

        if not value:
            return

        item = QtWidgets.QListWidgetItem(value)
        self.list_widget.addItem(item)
        self.added.emit(item)
        self.changed.emit()
