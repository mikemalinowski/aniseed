import traceback
import qtility
from Qt import QtWidgets, QtCore, QtGui

from . import dialogs
from . import delegate
from . import menu


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class BuildTreeWidget(QtWidgets.QTreeWidget):
    """
    The tree view is the heart of the stacking tool - exposing the build order to the
    user and allowing the user to add, remove and move components.
    """
    is_updated = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, stack: "xstack.Stack", app_config, app: QtWidgets.QWidget = None):
        super(BuildTreeWidget, self).__init__(parent=app)

        self.app = app
        self.app_config = app_config
        self.add_component_window = None
        self.switch_component_window = None
        self.allow_interaction = True

        # -- Declare the settings to allow us to correctly handle drag and
        # -- drop events
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        # -- Ensure we dont sort, as the order of the items is specifically
        # -- important
        self.setSortingEnabled(False)

        # -- We turn on mouse tracking so we can deal with hover events
        self.setMouseTracking(True)

        # -- We're not using columns, so we dont need a header
        self.setHeaderHidden(True)

        # -- We use a custom delegate to draw our items to allow us complete
        # -- control over how our items are visualised.
        self.setItemDelegateForColumn(
            0,
            delegate.ComponentItemDelegate(stack, self.app_config),
        )

        # -- Store a reference to the stack
        self.stack: "xstack.Stack" = stack

        # -- Store a reference to the root item
        self._root_item = None
        #
        # # -- This is where we store a mapping of uuid's to widgetitems
        # self._item_lookup = dict()

        # -- Tracker for if we're building
        self.is_building = False

        if self.app_config.stack_background:

            path = self.app_config.stack_background.replace("\\", "/")

            self.setStyleSheet(
                (
                    "QTreeView {"
                    f"background-image: url({path});"
                    "background-position: center;"
                    "background-repeat: no-repeat;"
                    "}"
                ),
            )

        # -- Now we're done, lets populate the tree
        self.populate()

        self.stack.hierarchy_changed.connect(self.populate)
        self.stack.component_added.connect(self.populate)
        self.stack.component_removed.connect(self.populate)
        self.app.build_started.connect(self.disable_interaction)
        self.app.build_complete.connect(self.enable_interaction)
        self.stack.build_progressed.connect(self.on_build_updated)

    # ----------------------------------------------------------------------------------
    def describe(self):
        for component in self.stack.components():
            print("-" * 100)
            component.describe()

    # ----------------------------------------------------------------------------------
    def disable_interaction(self):
        self.allow_interaction = False

    def enable_interaction(self):
        self.allow_interaction = True

    def on_build_updated(self, *args, **kwargs):
        self.viewport().update()

    # ----------------------------------------------------------------------------------
    def populate(self, *args, **kwargs):
        """
        This will clear out the tree and rebuild it
        """
        # -- Clear the current entries
        self.clear()

        # -- If we do not have a stack then there is nothing else we need
        # -- to do
        if not self.stack:
            return

        label = self.app_config.header_label or self.app_config.label

        # -- Declare the root item
        if self.app_config.show_tree_header:
            self._root_item = QtWidgets.QTreeWidgetItem(
                [label],
            )
        else:
            self._root_item = self.invisibleRootItem()

        self.insertTopLevelItems(0, [self._root_item])

        for root_component in self.stack.root_components:
            root_item = self._create_item(root_component)
            self._root_item.addChild(root_item)
            self.generate_child_items(root_item)
            root_item.setExpanded(True)
        self._root_item.setExpanded(True)

    def generate_child_items(self, item):
        for child_component in item.component.children:
            child_item = self._create_item(child_component)
            item.addChild(child_item)
            self.generate_child_items(child_item)
        item.setExpanded(True)

    # ----------------------------------------------------------------------------------
    def current_component(self) -> "xstack.Component" or None:
        """
        Returns the component for the currently active item
        """
        selected_item = self.currentItem()

        if not selected_item:
            return None

        if not hasattr(selected_item, "component"):
            print(f"{selected_item} has no component")
            return None

        return selected_item.component

    # ----------------------------------------------------------------------------------
    @classmethod
    def _create_item(cls, component: "xstack.Component") -> QtWidgets.QTreeWidgetItem:
        """
        This is a convenience function for create a consistent item in the tree view
        """

        if not component:
            return None

        # -- Build the item
        item = QtWidgets.QTreeWidgetItem(
            [f"{component.label()} ({component.identifier})"],
        )
        item.component = component

        # -- If we have an icon, apply it
        if component.icon:
            item.setIcon(0, QtGui.QIcon(component.icon))

        item.setData(
            0,
            QtCore.Qt.DisplayRole,
            component.uuid(),
        )

        return item

    # ----------------------------------------------------------------------------------
    def dropEvent(self, event: QtCore.QEvent):
        """
        Triggered on a drop event, this is where we check if we want to accept it and
        allow the item to be reparented.
        """
        # -- We only want to allow events from within ourselves
        if not isinstance(event.source(), self.__class__):
            return

        # -- Get the item that is dropped, and the item its being dropped on to
        item_being_dropped = self.currentItem()

        super(BuildTreeWidget, self).dropEvent(event)

        new_parent_item = item_being_dropped.parent()

        # -- Get the corresponding components for these
        child_component = item_being_dropped.component

        if hasattr(new_parent_item, "component"):
            parent_component = new_parent_item.component

        else:
            parent_component = None

        if parent_component:
            index = new_parent_item.indexOfChild(item_being_dropped)

        else:
            index = None
        former_parent = child_component.parent
        child_component.set_parent(parent_component, child_index=index)
        self.populate()

    # ----------------------------------------------------------------------------------
    def mousePressEvent(self, event: QtCore.QEvent):
        """
        Tstackgered when a mouse is clicked in the view. This allows the users to edit
        and manipulate the components
        """
        super(BuildTreeWidget, self).mousePressEvent(event)

        if not self.allow_interaction:
            return
        if event.button() != QtCore.Qt.RightButton:
            return

        selected_item = self.itemAt(event.pos())

        context_menu = menu.TreeMenu(
            item=selected_item,
            app_config=self.app_config,
            app=self.app,
            parent=self,
        )
        context_menu.exec(QtGui.QCursor().pos())

    # ----------------------------------------------------------------------------------
    def save_component_settings(self, item):

        component = item.component

        filepath = qtility.request.filepath(
            title="Save Config Settings",
            filter_="*.json (*.json)",
            save=True,
        )

        if not filepath:
            return

        component.save_settings(filepath)

    # ----------------------------------------------------------------------------------
    def load_component_settings(self, item):

        component = item.component

        filepath = qtility.request.filepath(
            title="Load Config Settings",
            filter_="*.json (*.json)",
            save=False,
        )

        if not filepath:
            return

        component.load_settings(filepath=filepath)

    # ----------------------------------------------------------------------------------
    def toggle_enable(self, item):
        component = item.component
        component.set_enabled(not component.is_enabled())

    # ----------------------------------------------------------------------------------
    def duplicate_component(self, item):
        item.component.duplicate()

    # ----------------------------------------------------------------------------------
    def help_for_component(self, item):
        item.component.help()

    # ----------------------------------------------------------------------------------
    @staticmethod
    def _run_user_function(func):

        # -- At this point, we're executing third party code, so we
        # -- wrap this in a broad exception
        try:
            return func()

        except:
            print(f"Function failed to execute : {func}")
            print(traceback.print_exc())

    # ----------------------------------------------------------------------------------
    def remove_component(self, item: QtWidgets.QListWidgetItem):
        """
        Removes a component from the stack
        """
        # -- Get the component
        component = item.component

        confirmation = qtility.request.confirmation(
            title=f"Remove {self.app_config.component_label}",
            message=f"Are you sure you want to remove {component.label()}",
            parent=self,
        )

        if not confirmation:
            return

        # -- Remove the reference to it
        item.component = None
        self.stack.remove_component(component)

        try:
            item.parent().removeChild(item)

        except RuntimeError:
            pass

    # ----------------------------------------------------------------------------------
    def add_component(self, parent):
        """
        Adds the component with the given uuid to the stack
        """
        self.add_component_window = dialogs.AddComponentWidget(
            stack=self.stack,
            component_parent=parent,
            app_config=self.app_config,
            parent=self,
        )
        self.add_component_window.component_added.connect(self.populate)
        self.add_component_window.show()

    # ----------------------------------------------------------------------------------
    def rename_component(self, item: QtWidgets.QListWidgetItem):

        component = item.component

        label = qtility.request.text(
            title=f"New {self.app_config.component_label} Label",
            message=f"Please provide a new label for this {self.app_config.component_label}",
            text=component.label(),
            parent=self
        )

        if not label or label == component.label():
            return

        component.set_label(label)

        self.populate()

    def switch_component_type(self, item: QtWidgets.QListWidgetItem):

        self.switch_component_window = dialogs.SwitchComponentTypeDialog(
            component=item.component,
            app_config=self.app_config,
            parent=self,
        )
        self.switch_component_window.component_switched.connect(self.populate)
        self.switch_component_window.show()
