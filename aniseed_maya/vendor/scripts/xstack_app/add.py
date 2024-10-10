import qute

from . import options


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class AddComponentWidget(qute.QDialog):
    """
    This widget is used to present a user with a list of components currently
    available to them.

    If that component has any pre-exposed options or requirements they will also
    be displayed.
    """

    # -- This signal is used to track when a component is added to the stack
    component_added = qute.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, stack, component_parent, app_config, parent=None):
        super(AddComponentWidget, self).__init__(parent)

        # -- We track the currently selected component in a variable, as we
        # -- want to reflect changes in options/requirements of a component
        self.active_component = None

        # -- We store a reference to the parent we are being asked to add a component
        # -- under. This is to ensure we can inherit values correctly.
        self.component_parent = component_parent

        # -- The app config is critical to ensuring we provide the user with a
        # -- consistent and contextually relevant experience.
        self.app_config = app_config

        # -- Store the stack that we're adding to
        self.stack = stack

        # -- Now we can start building our ui
        self.setLayout(qute.QVBoxLayout())

        # -- The search filter allows the user to restrict
        # -- what they see in the list
        self.search_filter = qute.QLineEdit()
        self.search_filter.setPlaceholderText("Search Filter")

        # -- This is the widget where we will show the user all the
        # -- available components
        self.component_list = qute.QListWidget()

        # -- The help info is where we show the user any information
        # -- the component can give us
        self.help_info = qute.QLabel()

        # -- The option panel where we will show options adn requirements
        self.options_widget = options.OptionsWidget(pre_expose_only=True)

        # -- Our logical buttons
        self.add_button = qute.QPushButton('Add')
        self.cancel_button = qute.QPushButton('Cancel')

        # -- Add our items to our layout
        self.layout().addWidget(self.search_filter)
        self.layout().addWidget(self.component_list)
        self.layout().addWidget(self.help_info)
        self.layout().addWidget(self.options_widget)

        # -- Add a horizontal layout for the buttons
        h_layout = qute.QHBoxLayout()
        h_layout.addWidget(self.add_button)
        h_layout.addWidget(self.cancel_button)
        self.layout().addLayout(h_layout)

        # -- Pre-populate the list
        self.populate()

        # -- Ensure that we re-populate whenever the user
        # -- updates the search filter
        self.search_filter.textChanged.connect(self.populate)
        self.add_button.clicked.connect(self.add_component)
        self.cancel_button.clicked.connect(self.cancel)
        self.component_list.itemClicked.connect(self.set_component)

        # -- Set modality
        self.setWindowModality(qute.Qt.WindowModal)

        # -- Set our window branding
        self.setWindowTitle(f"Add {self.app_config.component_label}")

        self.setWindowIcon(
            qute.QIcon(
                self.app_config.icon,
            ),
        )

    # ----------------------------------------------------------------------------------
    def set_component(self):
        """
        This will set the active component (the selected component).

        When this happens, we display any options and requirements which are flagged
        as should pre-expose themselves.

        Note: This does NOT add the component to the stack.
        """

        # -- Get the current item
        item = self.component_list.currentItem()

        # -- Reset the help text
        self.help_info.setText("")

        # -- If there is no item, clear the options and do nothing else.
        if not item:
            self.options_widget.set_component(None)
            return

        # -- Get a component instance, so we cna populate the options for it
        component = self.stack.component_library.get(item.text())(
            label="",
            stack=self.stack,
        )

        # -- If we have a component parent, we should check for any attributes
        # -- we expect to have their values inherit from the parent
        if self.component_parent:
            for option in component.options():
                if option.should_inherit() and self.component_parent.option(option.name()):
                    option.set(self.component_parent.option(option.name()).get())

            for requirement in component.requirements():
                if requirement.should_inherit() and self.component_parent.requirement(requirement.name()):
                    requirement.set(self.component_parent.requirement(requirement.name()).get())

        # -- Ask the option widget to update itself for this component
        self.options_widget.set_component(component)

        # -- If there is a doc string for this component, show that as help text
        if component.__doc__:
            self.help_info.setText(component.__doc__.strip())

        # -- Finally we mark this component as being the active component
        self.active_component = component

    # ----------------------------------------------------------------------------------
    def populate(self):
        """
        This will re-populate the list of components available to the user
        """
        # -- Clear the current list
        self.component_list.clear()

        # -- We allow the user to filter the list, so get their current filter text
        search_text = self.search_filter.text().lower()

        # -- Cycle all the components available
        for component_type in sorted(self.stack.component_library.names()):

            # -- If we're given a filter, and this does not match, then
            # -- skip it
            if search_text and search_text not in component_type.lower():
                continue

            # -- Request the component
            component = self.stack.component_library.get(component_type)

            # -- Add a widget item which also shows the icon
            item = qute.QListWidgetItem(
                qute.QIcon(
                    component.icon or self.app_config.component_icon,
                ),
                component_type,
            )

            # -- Add the item
            self.component_list.addItem(item)


    # ----------------------------------------------------------------------------------
    def add_component(self):
        """
        This is the user commiting to adding the component to the stack.

        Note that we do not directly add the instanced component, but we read the data
        from it and ask the stack to add a component with all the same data.
        """
        # -- Get the identifier for the component
        component_type = self.component_list.currentItem().text()

        # -- If that is not valid, do nothing
        if not component_type:
            print("no component type found")
            return

        # -- Ask the user to provide a label for the component
        label = qute.utilities.request.text(
            title=f"Add {self.app_config.component_label}",
            label=f"Please give a label for your {self.app_config.component_label}",
            text=self.active_component.suggested_label(),
            parent=self,
        )

        # -- If the user cancelled, do nothing more
        if not label:
            print("no label provided")
            return

        # -- We need to extract any option and requirement data that the user
        # -- predefined
        user_set_options = dict()

        if self.active_component:
            for option in self.active_component.options():
                user_set_options[option.name()] = option.get()

        user_set_requirements = dict()

        if self.active_component:
            for requirement in self.active_component.requirements():
                user_set_requirements[requirement.name()] = requirement.get()

        # -- Ask the stack to add a new component to the stack with those options
        # -- and requirements.
        self.stack.add_component(
            component_type=component_type,
            label=label,
            parent=self.component_parent,
            options=user_set_options,
            requirements=user_set_requirements,
        )
        print(f"added component to {self.stack}")
        self.component_added.emit()

        # -- Close this window as the process is complete
        self.window().close()

    # ----------------------------------------------------------------------------------
    def cancel(self):
        """
        Triggered when the user cancels
        """
        self.window().close()
