from .vendor import qute
import typing
import traceback
import collections

from . import add
from . import delegate
from . import tree_menu


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class BuildTreeWidget(qute.QTreeWidget):
    """
    The tree view is the heart of the stacking tool - exposing the build order to the
    user and allowing the user to add, remove and move components.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, stack: "xstack.Stack", app_config, parent: qute.QWidget = None):
        super(BuildTreeWidget, self).__init__(parent=parent)

        self.app_config = app_config
        self.add_component_window = None

        # -- Declare the settings to allow us to correctly handle drag and
        # -- drop events
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(qute.QAbstractItemView.InternalMove)

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

        # -- This is where we store a mapping of uuid's to widgetitems
        self._item_lookup = dict()

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

        self.stack.changed.connect(
            self.populate,
        )

    # ----------------------------------------------------------------------------------
    def populate(self):
        """
        This will clear out the tree and rebuild it
        """
        # -- Clear the current entries
        self.clear()

        # -- If we do not have a stack then there is nothing else we need
        # -- to do
        if not self.stack:
            return

        label = self.app_config.label

        # -- Declare the root item
        self._root_item = qute.QTreeWidgetItem(
            [label],
        )
        self.insertTopLevelItems(0, [self._root_item])

        # -- Add the children, and get any warnings back
        warnings = self._add_child_components(
            parent_item=self._root_item,
            build_pass_data=self.stack.build_order(),
        )

        # -- If we were given warnings, we should show them to the user
        if warnings:
            for warning in warnings:
                print(f"Warning: {warning}")

            qute.utilities.request.message(
                title="Initialisation Warning",
                label="Not all components could be made. Please see the script editor",
                parent=self
            )

    # ----------------------------------------------------------------------------------
    def current_component(self) -> "xstack.Component" or None:
        """
        Returns the component for the currently active item
        """
        selected_item = self.currentItem()

        if not selected_item:
            return None

        if not hasattr(selected_item, "uuid_"):
            return None

        uuid_ = selected_item.uuid_
        return self.stack.component(uuid_)

    # ----------------------------------------------------------------------------------
    def _add_child_components(
            self,
            parent_item: qute.QTreeWidgetItem,
            build_pass_data: typing.List
    ):
        """
        This will add all child components to the parent and is recursive.
        """
        warnings = list()

        for component_data in build_pass_data:

            uuid_ = component_data["uuid"]
            children = component_data["children"]

            item_widget = self._create_item(
                self.stack.component(uuid_)
            )

            if not item_widget:
                label = component_data["label"]
                warnings.append(f"Could not add {label} ({uuid_})")
                continue

            # -- Store the uuid on the widget
            item_widget.uuid_ = uuid_

            parent_item.addChild(item_widget)
            self._item_lookup[uuid_] = item_widget

            warnings.extend(
                self._add_child_components(
                    parent_item=item_widget,
                    build_pass_data=children,
                ),
            )

            # -- Ensure we're showing an expanded tree
            parent_item.setExpanded(True)

        return warnings

    # ----------------------------------------------------------------------------------
    @classmethod
    def _create_item(cls, component: "xstack.Component") -> qute.QTreeWidgetItem:
        """
        This is a convenience function for create a consistent item in the tree view
        """

        if not component:
            return None

        # -- Build the item
        item = qute.QTreeWidgetItem(
            [f"{component.label()} ({component.identifier})"],
        )

        # -- If we have an icon, apply it
        if component.icon:
            item.setIcon(0, qute.QIcon(component.icon))

        item.setData(
            0,
            qute.Qt.DisplayRole,
            component.uuid(),
        )

        return item

    # ----------------------------------------------------------------------------------
    def dropEvent(self, event: qute.QEvent):
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
        child_component = self.stack.component(item_being_dropped.uuid_)

        if hasattr(new_parent_item, "uuid_"):
            parent_component = self.stack.component(new_parent_item.uuid_)

        else:
            parent_component = None

        if parent_component:
            index = new_parent_item.indexOfChild(item_being_dropped)

        else:
            index = None

        self.stack.set_build_position(
            component=child_component,
            parent=parent_component,
            index=index,
        )

    # ----------------------------------------------------------------------------------
    def mousePressEvent(self, event: qute.QEvent):
        """
        Tstackgered when a mouse is clicked in the view. This allows the users to edit
        and manipulate the components
        """
        super(BuildTreeWidget, self).mousePressEvent(event)

        if event.button() != qute.Qt.RightButton:
            return

        selected_item = self.currentItem()

        menu_dict = collections.OrderedDict()
        icon_dict = collections.OrderedDict()

        tree_menu.construct(
            menu_dict,
            icon_dict,
            selected_item,
            self.app_config,
            self.stack,
        )

        menu = qute.utilities.menus.menuFromDictionary(
            menu_dict,
            icon_map=icon_dict,
            parent=self,
        )

        menu.popup(qute.QCursor().pos())

    # ----------------------------------------------------------------------------------
    def save_component_settings(self, item):

        component = self.stack.component(item.uuid_)

        filepath = qute.utilities.request.filepath(
            title="Save Config Settings",
            filter_="*.json (*.json)",
            save=True,
        )

        if not filepath:
            return

        component.save_settings(filepath)

    # ----------------------------------------------------------------------------------
    def load_component_settings(self, item):

        component = self.stack.component(item.uuid_)

        filepath = qute.utilities.request.filepath(
            title="Load Config Settings",
            filter_="*.json (*.json)",
            save=False,
        )

        if not filepath:
            return

        component.load_settings(filepath=filepath)

    # ----------------------------------------------------------------------------------
    def switch_version(self, item, version):
        component = self.stack.component(item.uuid_)

        self.stack.switch_component_version(
            component,
            version,
        )

        self.populate()

    # ----------------------------------------------------------------------------------
    def toggle_enable(self, item):
        component = self.stack.component(item.uuid_)
        component.set_enabled(not component.is_enabled())

    # ----------------------------------------------------------------------------------
    def duplicate_component(self, item):
        self.stack.component(item.uuid_).duplicate()

    # ----------------------------------------------------------------------------------
    def help_for_component(self, item):
        component = self.stack.component(item.uuid_)
        component.help()

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
    def remove_component(self, item: qute.QListWidgetItem):
        """
        Removes a component from the stack
        """
        component = self.stack.component(item.uuid_)

        confirmation = qute.utilities.request.confirmation(
            title=f"Remove {self.app_config.component_label}",
            label=f"Are you sure you want to remove {component.label()}",
            parent=self,
        )

        if not confirmation:
            return

        self.stack.remove_component(component)

        try:
            item.parent().removeChild(item)

        except RuntimeError:
            pass

    # ----------------------------------------------------------------------------------
    def add_component(self, parent_uuid: str):
        """
        Adds the component with the given uuid to the stack
        """
        self.add_component_window = add.AddComponentWidget(
            stack=self.stack,
            component_parent=self.stack.component(parent_uuid),
            app_config=self.app_config,
            parent=self,
        )
        self.add_component_window.component_added.connect(self.populate)

        self.add_component_window.show()

    # ----------------------------------------------------------------------------------
    def rename_component(self, item: qute.QListWidgetItem):

        component = self.stack.component(item.uuid_)

        label = qute.utilities.request.text(
            title=f"New {self.app_config.component_label} Label",
            label=f"Please provide a new label for this {self.app_config.component_label}",
            text=component.label(),
            parent=self
        )

        if not label or label == component.label():
            return

        component.set_label(label)

        self.populate()
