import typing
import logging
import qtility
from Qt import QtWidgets, QtCore, QtGui

from . import dialogs
from . import delegate
from . import menu

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class BuildTreeWidget(QtWidgets.QTreeWidget):
    """
    The tree view is the heart of the stacking tool - exposing the build order to the
    user and allowing the user to add, remove and move components.
    """
    is_updated = QtCore.Signal()

    # -- The context menu class. Subclasses can replace it to tailor the menu
    menu_class = menu.TreeMenu

    # ----------------------------------------------------------------------------------
    def __init__(self, stack: "xstack.Stack", app_config, app: QtWidgets.QWidget = None):
        super().__init__(parent=app)

        self.app = app
        self.app_config = app_config
        self.add_component_window = None
        self.switch_component_window = None
        self.allow_interaction = True

        # -- Declare the settings to allow us to correctly handle drag and
        # -- drop events. A read only structure cannot be re-ordered.
        if self.app_config.read_only_structure:
            self.setAcceptDrops(False)
            self.setDragEnabled(False)
            self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)

        else:
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

        # -- Double clicking an item renames it, so we dont want it to
        # -- also expand/collapse the item
        self.setExpandsOnDoubleClick(False)

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
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

    # ----------------------------------------------------------------------------------
    def describe(self):
        for component in self.stack.components():
            component.describe()

    # ----------------------------------------------------------------------------------
    def disable_interaction(self):
        self.allow_interaction = False

    def enable_interaction(self):
        self.allow_interaction = True

    def on_build_updated(self, *args, **kwargs):
        self.viewport().update()

    # ----------------------------------------------------------------------------------
    def populate(self, *args, remember_collapse_state: bool = True, **kwargs):
        """
        This will clear out the tree and rebuild it. The current component (if any)
        is selected again once the tree has been rebuilt.

        Args:
            remember_collapse_state: If True, any component items which were collapsed
                before the rebuild are collapsed again afterwards. New items are
                always expanded.
        """
        # -- Remember what was selected so we can restore it after the rebuild
        current_component = self.current_component()

        # -- Remember which items were collapsed, as re-ordering or adding components
        # -- triggers a rebuild and we do not want to lose the users layout
        collapsed_uuids = set()

        if remember_collapse_state:
            collapsed_uuids = self._collapsed_component_uuids()

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

        # -- Restore the collapse state of any items which existed before the rebuild
        for item in self._all_items():
            item_component = getattr(item, "component", None)

            if item_component and item_component.uuid() in collapsed_uuids:
                item.setExpanded(False)

        if current_component:
            self.select_component(current_component)

    # ----------------------------------------------------------------------------------
    def select_component(self, component: "xstack.Component"):
        """
        Makes the item representing the given component the current item
        """
        if not component:
            return

        for item in self._all_items():
            item_component = getattr(item, "component", None)

            if item_component and item_component.uuid() == component.uuid():
                self.setCurrentItem(item)
                self.scrollToItem(item)
                return

    # ----------------------------------------------------------------------------------
    def _all_items(self) -> list:
        """
        Returns every item in the tree, breadth first.

        We walk the items directly rather than using a QTreeWidgetItemIterator,
        as PySide can leave an iterator registered with the tree after we are
        done with it, and Qt then crashes updating it when items are moved
        """
        all_items = list()

        items = [
            self.topLevelItem(i)
            for i in range(self.topLevelItemCount())
        ]

        while items:
            item = items.pop(0)
            all_items.append(item)

            items.extend(
                item.child(i)
                for i in range(item.childCount())
            )

        return all_items

    # ----------------------------------------------------------------------------------
    def _collapsed_component_uuids(self) -> set:
        """
        Returns the uuids of all the components whose items are currently collapsed
        """
        return {
            item.component.uuid()
            for item in self._all_items()
            if getattr(item, "component", None) and not item.isExpanded()
        }

    def generate_child_items(self, item):
        for child_component in item.component.children:
            child_item = self._create_item(child_component)
            item.addChild(child_item)
            self.generate_child_items(child_item)
        item.setExpanded(True)

    # ----------------------------------------------------------------------------------
    def current_component(self) -> typing.Optional["xstack.Component"]:
        """
        Returns the component for the currently active item
        """
        selected_item = self.currentItem()

        if not selected_item:
            return None

        if not hasattr(selected_item, "component"):
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
        # -- We only want to allow events from within ourselves, and never
        # -- when the structure is read only
        if not isinstance(event.source(), self.__class__) or self.app_config.read_only_structure:
            event.ignore()
            return

        # -- Get the item that is dropped, and the item its being dropped on to
        item_being_dropped = self.currentItem()

        super().dropEvent(event)

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

        child_component.set_parent(parent_component, child_index=index)
        self.populate()

    # ----------------------------------------------------------------------------------
    def mousePressEvent(self, event: QtCore.QEvent):
        """
        Tstackgered when a mouse is clicked in the view. This allows the users to edit
        and manipulate the components
        """
        super().mousePressEvent(event)

        if not self.allow_interaction:
            return
        if event.button() != QtCore.Qt.RightButton:
            return

        selected_item = self.itemAt(event.pos())

        context_menu = self.menu_class(
            item=selected_item,
            app_config=self.app_config,
            app=self.app,
            parent=self,
        )

        # -- An app may leave nothing to offer, such as on empty space when
        # -- the structure is read only
        if context_menu.isEmpty():
            return

        if hasattr(context_menu, "exec_"):
            context_menu.exec_(QtGui.QCursor().pos())
        else:
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
    def import_subtree(self, item):
        """
        Load a JSON file and add its contents as children of the
        right-clicked component. Regenerates UUIDs on load.
        """
        component = item.component

        filepath = qtility.request.filepath(
            title="Import as Children",
            filter_="*.json (*.json)",
            save=False,
        )

        if not filepath:
            return

        component.import_subtree(filepath=filepath)

    # ----------------------------------------------------------------------------------
    def toggle_enable(self, item):
        component = item.component
        component.set_enabled(not component.is_enabled())

    # ----------------------------------------------------------------------------------
    def duplicate_component(self, item):

        component = item.component

        dialog = dialogs.DuplicateComponentDialog(
            component=component,
            app_config=self.app_config,
            parent=self,
        )

        result = dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()

        if not result:
            return

        # -- Only search and replace when a search was given. An empty
        # -- replace is allowed, and removes the matched text.
        search_for = dialog.search_for() or None
        replace_with = dialog.replace_with() if search_for else None

        new_component = component.duplicate(
            search_for=search_for,
            replace_with=replace_with,
        )

        if not new_component:
            return

        # -- An explicitly entered name takes priority over the label the
        # -- search and replace produced
        if dialog.label() and dialog.label() != component.label():
            new_component.set_label(dialog.label())

        self.populate()

        # -- Select the duplicate so the editor shows its inputs, options and outputs
        self.select_component(new_component)

    # ----------------------------------------------------------------------------------
    def search_and_replace_component(self, item):

        search_for = qtility.request.text(
            title="Search For",
            message=(
                "Give the text you want to search for. Note that this will be converted "
                "to a regular expression."
            ),
            text="",
        )

        if not search_for:
            return None

        replace_with = qtility.request.text(
            title="Replace With",
            message=(
                "Give the text you want to replace with."
            ),
            text="",
        )

        if not replace_with:
            return None

        item.component.search_and_replace(
            search_for=search_for,
            replace_with=replace_with,
        )

    # ----------------------------------------------------------------------------------
    def help_for_component(self, item):
        item.component.help()

    # ----------------------------------------------------------------------------------
    @staticmethod
    def _run_user_function(func):

        # -- At this point, we're executing third party code, so we
        # -- wrap this in a broad exception
        # noinspection PyBroadException
        try:
            return func()

        except Exception:
            log.exception(f"Function failed to execute : {func}")

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

        # -- Removing the component repopulates the tree, which may already
        # -- have deleted this item
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
    def on_item_double_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int):
        """
        Double clicking a component item starts the rename flow, unless the
        structure is read only. Subclasses can re-implement this to give double
        clicking another meaning.
        """
        if not self.allow_interaction:
            return

        if not getattr(item, "component", None):
            return

        if self.app_config.read_only_structure:
            return

        self.rename_component(item)

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
