import os
import re
import qtility
import functools
from Qt import QtWidgets, QtGui, QtCore

from .. import resources
from ..core import ToolBox


class ToolWidget(QtWidgets.QWidget):

    _FILTER_DENOMINATORS = re.compile("\,|\;")

    def __init__(self, parent=None):
        super(ToolWidget, self).__init__(parent=parent)
        # -- Instance a singleton of the toolbox
        self.toolbox = ToolBox.singleton()

        # -- Create our main layout
        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )

        # -- Add the classification drop down menu
        self.classification_combo = QtWidgets.QComboBox()
        self.layout().addWidget(self.classification_combo)
        self.populate_classifications()

        # -- Add the tool filter which is used to filter
        # -- which items are shown
        self.tool_filter = QtWidgets.QLineEdit()
        self.tool_filter.setPlaceholderText('Tool Filter')
        self.layout().addWidget(self.tool_filter)

        # -- Add the list widget which we will show everything
        # -- within. Note that this actuall a tree widget
        self.tool_list = ToolList(
            toolbox=self.toolbox,
            parent=self,
        )
        self.layout().addWidget(self.tool_list)

        # -- This widget will show any help text
        self.help_label = QtWidgets.QLabel("")
        self.help_label.setWordWrap(True)

        # -- Set up the options layout
        self.options_group = QtWidgets.QGroupBox("Options")
        self.options_layout = QtWidgets.QVBoxLayout()
        self.options_group.setLayout(self.options_layout)

        self.layout().addWidget(self.help_label)
        self.layout().addWidget(self.options_group)

        # -- Finally, filter the view on startup
        self.perform_filter()

        # -- We dynamically generate widgets, and we want to be
        # -- able to store last selected options too. So these
        # -- variables will be used to store that data
        self._last_item = None
        self._dynamic_widgets = dict()
        self._persistent_options = dict()

        # -- Connect signals and slots
        self.tool_list.itemSelectionChanged.connect(self.popuplate_options)
        self.tool_list.itemDoubleClicked.connect(self.run_tool)
        self.tool_filter.textChanged.connect(self.perform_filter)
        self.classification_combo.currentIndexChanged.connect(self.perform_filter)

    def run_tool(self):

        tool_identifier = self.tool_list.active_tool()

        if not tool_identifier:
            return

        kwargs = self.toolbox.signature(tool_identifier)

        for key, value in kwargs.items():
            if key in self._dynamic_widgets:
                kwargs[key] = qtility.derive.value(self._dynamic_widgets[key])

        self.toolbox.run(tool_identifier, **kwargs)

    def populate_classifications(self):

        self.classification_combo.clear()

        for classification in sorted(self.toolbox.classifications()):
            self.classification_combo.addItem(classification)

    def popuplate_options(self, *args, **kwargs):

        item = self.tool_list.currentItem()

        if not item:
            return

        # -- If we're selecting the currently selected
        # -- option then we dont need to do anything
        if item == self._last_item:
            return

        # -- Empty the layout of any pre-existing items
        self._dynamic_widgets = dict()
        qtility.layouts.empty(self.options_layout)

        # -- Now attempt to access the selected item
        if not item:
            return

        # -- Only continue if we're a python trait
        tool_identifier = self.tool_list.active_tool()

        if not tool_identifier:
            return

        tool = self.toolbox.request(tool_identifier)

        # -- Store this as the last selected item
        self._last_item = item

        # -- Add a help text
        self.help_label.setText(self.toolbox.documentation(tool_identifier))

        for option_name, option_value in self.resolved_options(tool).items():

            # -- Create the widget and the layout
            widget = qtility.derive.qwidget(option_value)

            if not widget:
                continue

            layout = qtility.widgets.addLabel(
                widget,
                option_name,
                min_label_width=150,
            )

            # -- Hook up the change signal so we can tell the trait
            # -- what our default values are
            qtility.derive.connect(
                widget,
                functools.partial(
                    self.store_option_change,
                    tool_identifier,
                ),
            )

            # -- Store the widget so we can read it if the user
            # -- runs the script
            self._dynamic_widgets[option_name] = widget
            self.options_layout.addLayout(layout)

    def resolved_options(self, tool) -> dict:
        results = dict()

        kwargs = self.toolbox.signature(tool.identifier)

        for option_name, option_value in kwargs.items():
            results[option_name] = option_value

        if tool.identifier in self._persistent_options:
            results.update(self._persistent_options[tool.identifier])

        return results

    def store_option_change(self, tool_identifier, *args, **kwargs):


        resolved_arguments = dict()
        for name, widget in self._dynamic_widgets.items():
            resolved_arguments[name] = qtility.derive.value(widget)

        self._persistent_options[tool_identifier] = resolved_arguments

    def perform_filter(self, *args, **kwargs):
        """
        This will take the filter text and apply the filter to the tool list
        """
        self.tool_list.apply_filters(
            [
                data.strip()
                for data in self._FILTER_DENOMINATORS.split(self.tool_filter.text())
                if data.strip()
            ],
            classification=self.classification_combo.currentText(),
        )

class ToolList(QtWidgets.QTreeWidget):

    def __init__(self, toolbox, parent=None):
        super(ToolList, self).__init__(parent=parent)

        # -- Set the general properties
        self.setHeaderHidden(True)
        self.setIconSize(
            QtCore.QSize(
                40,
                40,
            )
        )

        # -- This filter list defines what we can show
        self.filters = []
        self._tool_items = []

        # -- Store a reference to the toolbox
        self.toolbox = toolbox
        self._category_items = dict()

        # -- Populate ourselves
        self.popuplate()

    def active_tool(self):

        item = self.currentItem()

        if not item:
            return None

        if item in [t for t in self._category_items.values()]:
            return None

        return item.text(0)

    def popuplate(self):

        # -- Declare our default icon
        default_icon = QtGui.QIcon(
            resources.get("default_tool_icon.png")
        )

        # -- Clear any current entries
        self.clear()
        self._tool_items = []

        # -- Get a list of categories, and create an item for each one
        self._category_items = dict(
            General=QtWidgets.QTreeWidgetItem(["General"])
        )

        for category in self.toolbox.categories():

            # -- If this category is already defined for any reason,
            # -- then we skip it
            if category in self._category_items:
                continue

            # -- Create the item and store a reference to it
            item = QtWidgets.QTreeWidgetItem([category])
            item.setIcon(
                0,
                QtGui.QIcon(
                    resources.get(f"icons/{category}.png") or ""
                )
            )
            self._category_items[category] = item

        # -- Add the item as a top level items in alphabetical order
        for category in sorted(self._category_items):
            self.addTopLevelItem(self._category_items[category])

        # -- Now we can add the actual tools as children of the corresponding
        # -- categories
        for tool in sorted(self.toolbox.plugins(), key=lambda t: t.identifier):

            if not tool.user_facing:
                continue

            # -- Get a list of categories to add this tool to. If none are
            # -- defined then we fall back to the general category.
            categories = tool.categories or ["General"]
            icon_path = None
            if tool.icon and os.path.exists(tool.icon):
                icon_path = tool.icon

            if not icon_path:
                resource_icon = resources.get(f"icons/{tool.identifier}.png")

                if os.path.exists(resource_icon):
                    icon_path = resource_icon

            if not icon_path:
                icon = default_icon

            else:
                icon = QtGui.QIcon(icon_path)

            for category in categories:
                item = QtWidgets.QTreeWidgetItem([tool.identifier])
                item.setIcon(0, icon)
                item.setToolTip(0, tool.run.__doc__)
                item.setHidden(self.is_tool_filtered_out(tool.identifier, tool.classification))

                self._tool_items.append(item)
                self._category_items[category].addChild(item)

        self.hide_empty_categories()


    def is_tool_filtered_out(self, identifier, classification):

        tool = self.toolbox.request(identifier)

        if tool.classification != classification:
            return True

        if not self.filters:
            return False

        for filter_string in self.filters:
            if filter_string.lower() in identifier.lower():
                return False

        return True

    def apply_filters(self, filter_items, classification):
        self.filters = filter_items

        for item in self._tool_items:
            item.setHidden(
                self.is_tool_filtered_out(
                    item.text(0),
                    classification,
                ),
            )

        self.hide_empty_categories()

    def hide_empty_categories(self):
        for idx in reversed([n for n in range(self.topLevelItemCount())]):
            item = self.topLevelItem(idx)

            item.setHidden(self._are_children_hidden(item))

    def _are_children_hidden(self, item):
        for idx in range(item.childCount()):
            if not item.child(idx).isHidden():
                return False
        return True


class ToolWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(ToolWindow, self).__init__(parent=parent)

        self.setCentralWidget(ToolWidget(self))
        self.setWindowTitle("Aniseed Toolkit")
        self.setWindowIcon(
            QtGui.QIcon(resources.get("icon.png"))
        )

def launch():

    q_app = qtility.app.get()

    w = ToolWindow(parent=qtility.windows.application())
    w.show()
    q_app.exec()