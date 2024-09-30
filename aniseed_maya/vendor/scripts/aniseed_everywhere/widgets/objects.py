import functools
import qute
import xstack_app
from crosswalk import app

from .. import resources


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class CustomLineEdit(qute.QLineEdit):

    # ----------------------------------------------------------------------------------
    def __init__(self, default_value, component=None, *args, **kwargs):
        super(CustomLineEdit, self).__init__(default_value, *args, **kwargs)

        self.component = component

    # ----------------------------------------------------------------------------------
    def contextMenuEvent(self, event):

        menu = self.createStandardContextMenu()

        if not self.component:
            menu.popup(event.globalPos())
            return

        # -- Add a separator
        menu.addSeparator()

        parent = self.component.parent()
        last_menu = menu

        while parent:

            submenu = qute.QMenu(parent.label())

            for output in parent.outputs():

                action = submenu.addAction(
                    qute.QIcon(xstack_app.resources.get("address.png")),
                    output.name(),
                )

                action.triggered.connect(
                    functools.partial(
                        self.apply_address,
                        output.address(),
                    ),
                )

            last_menu.addSeparator()
            last_menu.addMenu(submenu)

            parent = parent.parent()

            # -- The last parent is the rig, so dont add that
            if not parent.parent():
                break

            last_menu = submenu

        menu.popup(event.globalPos())

    # ----------------------------------------------------------------------------------
    def apply_address(self, address, *args, **kwargs):
        self.setText(address)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ObjectSelector(qute.QWidget):
    """
    This is a selector field that exposes buttons to make it easier
    to fill the field based on the selection
    """
    changed = qute.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, default_value="", button_size=30, component=None, parent=None):
        super(ObjectSelector, self).__init__(parent=parent)

        # -- Store our input values
        self._button_size = button_size

        # -- Define our base layout
        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QHBoxLayout(),
            ),
        )

        # -- Add our colour button
        self.text_field = CustomLineEdit(default_value, component=component)
        self.layout().addWidget(self.text_field)

        # -- Add the buttons
        self.scene_to_field_button = self.icon_button(resources.get("store.png"))
        self.field_to_scene_button = self.icon_button(resources.get("select.png"))

        self.layout().addWidget(self.scene_to_field_button)
        self.layout().addWidget(self.field_to_scene_button)

        # -- Ensure we are initialized correctly
        self.update_size()

        # -- Hook up the events
        self.scene_to_field_button.clicked.connect(self.scene_to_field)
        self.field_to_scene_button.clicked.connect(self.field_to_scene)
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
    def scene_to_field(self):
        try:
            self.set_value(
                app.objects.get_name(
                    app.selection.selected()[0]
                )
            )

        except IndexError:
            self.set_value("")

    # ----------------------------------------------------------------------------------
    def field_to_scene(self):
        try:
            app.selection.select(self.get_value())

        except RuntimeError:
            print(f"Failed to select {self.get_value()}")

    # ----------------------------------------------------------------------------------
    def update_size(self):
        buttons = [
            self.scene_to_field_button,
            self.field_to_scene_button,
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


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ObjectMap(qute.QWidget):
    """
    This allows for a key/value pairing to be made where the value is always an
    object and the key is a text string
    """

    changed = qute.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, button_size=30, parent=None):
        super(ObjectMap, self).__init__(parent=parent)

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
        # -- Ensure we are initialized correctly
        self.update_size()

        # -- Hook up the events
        self.add_button.clicked.connect(self.add)
        self.remove_button.clicked.connect(self.remove)
        self.up_button.clicked.connect(self.move_up)
        self.down_button.clicked.connect(self.move_down)

    # ----------------------------------------------------------------------------------
    def _item(self, key, value):

        item = qute.QListWidgetItem(f"{key} -> {value}")
        item.key_ = key
        item.value_ = value

        self.list_widget.addItem(item)

    # ----------------------------------------------------------------------------------
    def add(self):
        for item in app.selection.selected():

            item = app.objects.get_name(item)

            label = qute.utilities.request.text(
                title="Provide Label",
                label=f"Please give a label to assign with {item}",
                parent=self,
            )

            if not label:
                return

            self.list_widget.addItem(
                self._item(
                    label,
                    item,
                ),
            )

        self.changed.emit()

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

        result = dict()

        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            result[item.key_] = item.value_

        return result

    # ----------------------------------------------------------------------------------
    def set_value(self, v):

        for k, v in v.items():
            self.list_widget.addItem(
                self._item(
                    key=k,
                    value=v,
                ),
            )

        self.changed.emit()
