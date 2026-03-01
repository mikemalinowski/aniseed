import functools
from Qt import QtWidgets, QtGui, QtCore


def show(item, app_config, app, parent):
    menu = TreeMenu(
        item=item,
        app_config=app_config,
        app=app,
        parent=parent,
    )
    menu.popup(QtGui.QCursor().pos())


class TreeMenu(QtWidgets.QMenu):

    def __init__(self, item=None, app_config=None, app=None, parent=None):
        super(TreeMenu, self).__init__("ASD", parent=parent)

        # -- Store our inputs
        self._parent = parent
        self.app = app
        self.item = item
        self.component = getattr(item, "component", None)
        self.app_config = app_config

        # -- Determine our labels
        self.component_label = self.app_config.component_label
        self.execute_label = self.app_config.execute_label
        self.validate_label = "validate"

        # -- Determine some icons up front
        self.execute_icon = QtGui.QIcon(self.app_config.execute_icon)
        self.validate_icon = QtGui.QIcon(self.app_config.validate_icon)

        if self.component:
            self.populate_component_menu()
        else:
            self.populate_unfocused_menu()

    def populate_component_menu(self):
        # -- Start by adding our build and validation menus
        self.add_build_menu()
        self.add_validate_menu()

        # -- Add the items which allow a user to edit/alter a component
        self.add_component_interaction_items()

        # -- Add any actions the component provides
        self.add_component_user_actions()

        # -- Add the menu which exposes the lesser used
        # -- items
        self.add_additional_actions()

        # -- Finally we add the help menu item
        help_action = QtWidgets.QAction(f"Help", self._parent)
        help_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.help_for_component,
                item=self.item,
            ),
        )
        self.addAction(help_action)

    def add_additional_actions(self):

        # -- Add the rename, wrapped in a separator
        self.addSeparator()

        # -- Build menu
        actions_menu = QtWidgets.QMenu("Actions")

        # -- Action to enable/disable a component
        enable_disable_action = QtWidgets.QAction(f"Enable/Disable", self._parent)
        enable_disable_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.toggle_enable,
                item=self.item,
            ),
        )
        actions_menu.addAction(enable_disable_action)

        # -- Action to export settings
        export_action = QtWidgets.QAction(f"Export Settings", self._parent)
        export_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.save_component_settings,
                item=self.item,
            ),
        )
        actions_menu.addAction(export_action)

        # -- Action to Import settings
        import_action = QtWidgets.QAction(f"Export Settings", self._parent)
        import_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.load_component_settings,
                item=self.item,
            ),
        )
        actions_menu.addAction(import_action)

        # -- Finally we add the menu
        self.addMenu(actions_menu)

    def add_component_user_actions(self):

        # -- If we have no user facing actions we can skip this
        user_functions = self.component.user_functions()
        if not user_functions:
            return

        # -- Start with a separator
        self.addSeparator()

        # -- Cycle the user functions, adding each one
        for label, func_ in user_functions.items():
            action = QtWidgets.QAction(label, self)
            action.triggered.connect(func_)
            self.addAction(action)

    def add_component_interaction_items(self):

        # -- Add the rename, wrapped in a separator
        self.addSeparator()
        rename_action = QtWidgets.QAction(f"Rename {self.app_config.component_label}", self._parent)
        rename_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.rename_component,
                item=self.item,
            ),
        )
        self.addAction(rename_action)
        self.addSeparator()

        # -- Add
        add_action = QtWidgets.QAction(f"Add {self.app_config.component_label}", self._parent)
        add_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.add_component,
                parent=self.component,
            ),
        )
        self.addAction(add_action)

        # -- Remove
        remove_action = QtWidgets.QAction(f"Remove {self.app_config.component_label}", self._parent)
        remove_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.remove_component,
                item=self.item,
            ),
        )
        self.addAction(remove_action)

        # -- Duplicate
        duplicate_action = QtWidgets.QAction(f"Duplicate {self.app_config.component_label}", self._parent)
        duplicate_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.duplicate_component,
                item=self.item,
            ),
        )
        self.addAction(duplicate_action)

        # -- Switch Component
        switch_action = QtWidgets.QAction(f"Change {self.app_config.component_label} Type", self._parent)
        switch_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.switch_component_type,
                item=self.item,
            ),
        )
        self.addAction(switch_action)

    def add_build_menu(self):
        """
        Creates the menu for building the given component
        """
        # -- Build menu
        build_menu = QtWidgets.QMenu(self.execute_label, self)

        # -- Build Below (default)
        build_section = QtWidgets.QAction(f"{self.execute_label} Section", self._parent)
        build_section.triggered.connect(
            functools.partial(
                self.app.build,
                build_below=self.component,
            ),
        )
        build_menu.addAction(build_section)

        # -- All other build actions are less used, so lets add a separator
        build_menu.addSeparator()

        # -- Build Up To
        build_up_to = QtWidgets.QAction(f"{self.execute_label} Up To This", self._parent)
        build_up_to.triggered.connect(
            functools.partial(
                self.app.build,
                build_up_to=self.component,
            ),
        )
        build_menu.addAction(build_up_to)

        # -- Build Only.
        build_just_this = QtWidgets.QAction(f"{self.execute_label} Just This", self._parent)
        build_just_this.triggered.connect(
            functools.partial(
                self.app.build,
                build_up_to=self.component,
            ),
        )
        build_menu.addAction(build_just_this)
        
        # -- Add the build menu
        self.addMenu(build_menu)

    def add_validate_menu(self):
        """
        Creates the menu for building the given component
        """
        # -- validate menu
        validate_menu = QtWidgets.QMenu(self.validate_label, self)

        # -- validate Below (default)
        validate_section = QtWidgets.QAction(f"{self.validate_label} Section", self._parent)
        validate_section.triggered.connect(
            functools.partial(
                self.app.build,
                validate_below=self.component,
                validate_only=True,
            ),
        )
        validate_menu.addAction(validate_section)

        # -- All other validate actions are less used, so lets add a separator
        validate_menu.addSeparator()

        # -- validate Up To
        validate_up_to = QtWidgets.QAction(f"{self.validate_label} Up To This", self._parent)
        validate_up_to.triggered.connect(
            functools.partial(
                self.app.build,
                build_up_to=self.component,
                validate_only=True,
            ),
        )
        validate_menu.addAction(validate_up_to)

        # -- validate Only.
        validate_just_this = QtWidgets.QAction(f"{self.validate_label} Just This", self._parent)
        validate_just_this.triggered.connect(
            functools.partial(
                self.app.build,
                build_up_to=self.component,
                validate_only=True,
            ),
        )
        validate_menu.addAction(validate_just_this)

        # -- Add the validate menu
        self.addMenu(validate_menu)

    def populate_unfocused_menu(self):

        # -- Item to instigate an execution of the stag
        label = f"{self.execute_label} {self.app_config.label}"
        build_action = QtWidgets.QAction(self.execute_icon, label, self._parent)
        build_action.triggered.connect(functools.partial(self.app.build))
        self.addAction(build_action)

        # -- This item will allow a user to validate the stack
        label = f"{self.validate_label} {self.app_config.label}"
        validate_action = QtWidgets.QAction(self.validate_icon, label, self._parent)
        validate_action.triggered.connect(
            functools.partial(
                self.app.build,
                None,
                True, # -- Validate Only
            ),
        )
        self.addAction(validate_action)

        # -- Add a separator to visually distinguish the execution
        # -- items
        self.addSeparator()

        # -- Now add the functionality to add a component
        label = f"Add {self.component_label}"
        add_action = QtWidgets.QAction(self.execute_icon, label, self._parent)
        add_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.add_component,
                parent=None,
            ),
        )
        self.addAction(add_action)

        # -- Add a separator to visually distinguish the execution
        # -- items
        self.addSeparator()

        # -- Now add the functionality to add a component
        label = f"Describe"
        add_action = QtWidgets.QAction("Describe", self._parent)
        add_action.triggered.connect(
            functools.partial(
                self.app.tree_widget.describe,
            ),
        )
        self.addAction(add_action)