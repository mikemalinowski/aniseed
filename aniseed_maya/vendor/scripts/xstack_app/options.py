import qute
import xstack
import string
import weakref
import functools

from . import resources


# ----------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ComponentEditor(qute.QWidget):
    """
    The component editor shows the tabs for both the requirements and the options
    of a component.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(ComponentEditor, self).__init__(parent=parent)

        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )

        # -- Now start populating the content
        self.tab_widget = qute.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        self.options_widget = OptionsWidget()
        self.requirements_widget = RequirementsWidget(parent=self)
        self.outputs_widget = OutputsWidget(parent=self)

        self.tab_widget.addTab(
            self.requirements_widget, #requirement_scroll_area,
            "Requirements",
        )

        self.tab_widget.addTab(
            self.options_widget, #,  #self.options_widget, #option_scroll_area,
            "Options"
        )

        self.tab_widget.addTab(
            self.outputs_widget, #,  #self.options_widget, #option_scroll_area,
            "Outputs"
        )

        for i in range(3):
            self.tab_widget.setTabVisible(i, False)

    # ----------------------------------------------------------------------------------
    def set_component(self, component: xstack.Component):
        """
        Applies the component to the options and the requirements widgets
        """

        requirements_visibility = True if (component and len(component.requirements()) > 0) else False
        options_visibility = True if (component and len(component.options()) > 0) else False
        outputs_visibility = True if (component and len(component.outputs()) > 0) else False

        self.tab_widget.setTabVisible(0, requirements_visibility)
        self.tab_widget.setTabVisible(1, options_visibility)
        self.tab_widget.setTabVisible(2, outputs_visibility)

        self.options_widget.set_component(component)
        self.requirements_widget.set_component(component)
        self.outputs_widget.set_component(component)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,DuplicatedCode
class OptionsWidget(qute.QWidget):
    """
    This widget manages the display of the options
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, pre_expose_only=False, parent: qute.QWidget = None):
        super(OptionsWidget, self).__init__(parent=parent)

        # -- This determines if we show all options, or only options that
        # -- are marked as pre-expsure
        self._pre_expose_only = pre_expose_only

        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )

        self.option_layout = qute.QVBoxLayout()
        self.option_layout.setContentsMargins(10, 10, 10, 10)

        self.layout().addLayout(self.option_layout)

    # ----------------------------------------------------------------------------------
    # noinspection PyUnresolvedReferences
    def set_component(self, component: xstack.Component or None):
        """
        This sets the target component for the widget and populates the widget
        with all the options.
        """
        # -- Clear the current layout of options
        qute.utilities.layouts.empty(self.option_layout)

        # -- If we do not have a component we dont need to populate anything
        if not component:
            return

        group_layouts = dict()

        for option in component.options():

            if self._pre_expose_only and not option.should_pre_expose():
                continue

            # -- Get the option object
            option_widget = component.option_widget(option.name())

            # -- If this option is flagged as not needing a ui implementation
            # -- then we dont need to do anything
            if option_widget == component.IGNORE_OPTION_FOR_UI:
                continue

            # -- Get the raw value, as we want to see the address
            # -- if its an address
            option_value = option.get(resolved=False)

            # -- If we were not given a widget, then as qute to derive one
            # -- for us
            if not option_widget:
                option_widget = qute.utilities.derive.deriveWidget(
                    option_value,
                )

            if not option_widget:
                print(f"Could not resolve a widget for : {option.name()}")
                continue

            option_widget.setToolTip(
                option.description(),
            )

            # -- Set the value of the widget
            qute.utilities.derive.setBlindValue(
                option_widget,
                option_value,
            )

            # -- Hook up a connection such that when this option ui changes we
            # -- reflect that change into the component
            qute.utilities.derive.connectBlind(
                option_widget,
                functools.partial(
                    self.reflect_option_change,
                    option_widget,
                    option.name(),
                    component,
                ),
            )

            layout_to_add_into = self.option_layout

            if option.group():
                if option.group() in group_layouts:
                    layout_to_add_into = group_layouts[option.group()]

                else:
                    # -- Create the new layout
                    layout = qute.QVBoxLayout()

                    # -- Create the group box
                    group_box = qute.QGroupBox(option.group())
                    group_box.setLayout(layout)

                    # -- Add the group box to the main layout
                    self.option_layout.addWidget(group_box)

                    # -- Store this so that we only create one instance of it
                    # -- and mark this as the layout to add the widget into
                    layout_to_add_into = layout
                    group_layouts[option.group()] = layout

            # # -- Add the widget into the ui
            if hasattr(option_widget, "dont_label") and option_widget.dont_label:
                layout_to_add_into.addWidget(option_widget)

            else:
                layout_to_add_into.addLayout(
                    qute.utilities.widgets.addLabel(
                        option_widget,
                        string.capwords(option.name().replace('_', ' ')),
                        150,
                        slim=False,
                    ),
                )

        # -- Always add in a spacer to push all the widgets up to the top
        self.option_layout.addSpacerItem(
            qute.QSpacerItem(
                10,
                0,
                qute.QSizePolicy.Expanding,
                qute.QSizePolicy.Expanding,
            ),
        )

    # ----------------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    @classmethod
    def reflect_option_change(cls, widget, option_name, component, *args, **kwargs):
        """
        This is called whenever an option ui element is changed. Within this function
        we must push the changed value back into the component

        Args:
            widget: Widget to read the value from
            option_name: Name of the option to update
            component: xstack.Component instance to update
            *args:
            **kwargs:

        Returns:
            None
        """
        component.option(option_name).set(
            qute.utilities.derive.deriveValue(
                widget,
            ),
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class RequirementsWidget(qute.QWidget):
    """
    This widget manages the display of the requirements of a component.

    Note: This is currently largely a copy of the Options Widget, however both
    serve a unique purpose and will likely branch in the future, so they are each
    getting their own classes.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, pre_expose_only=False, parent: qute.QWidget = None):
        super(RequirementsWidget, self).__init__(parent=parent)

        # -- This determines if we show all requirements, or only requirements that
        # -- are marked as pre-expsure
        self._pre_expose_only = pre_expose_only

        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )

        self.requirement_layout = qute.QVBoxLayout()
        self.requirement_layout.setContentsMargins(10, 10, 10, 10)

        self.layout().addLayout(self.requirement_layout)

    # ----------------------------------------------------------------------------------
    # noinspection DuplicatedCode
    def set_component(self, component: xstack.Component):
        """
        This sets the target component for the widget and populates the widget
        with all hte requirements.
        """
        # -- Clear the current layout of options
        qute.utilities.layouts.empty(self.requirement_layout)

        # -- If we do not have a component we dont need to populate anything
        if not component:
            return

        group_layouts = dict()

        for requirement in component.requirements():

            if self._pre_expose_only and not requirement.should_pre_expose():
                continue

            # -- Get the requirement object
            requirement_widget = component.requirement_widget(requirement.name())


            # -- If this requirement is flagged as not needing a ui implementation
            # -- then we dont need to do anything
            if requirement_widget == component.IGNORE_OPTION_FOR_UI:
                continue

            # -- If we were not given a widget, then as qute to derive one
            # -- for us
            if not requirement_widget:
                requirement_widget = qute.utilities.derive.deriveWidget(
                    requirement.get()
                )

            if not requirement_widget:
                print(f"Could not resolve a widget for : {requirement.name()}")
                continue

            requirement_widget.setToolTip(
                requirement.description(),
            )

            # -- Get the raw value. If its an address, we want to specifically
            # -- get the address back and not the resolved value
            requirement_value = requirement.get(resolved=False)

            # -- Set the value of the widget
            qute.utilities.derive.setBlindValue(
                requirement_widget,
                requirement_value,
            )

            # -- Hook up a connection such that when this requirement ui changes we
            # -- reflect that change into the component
            qute.utilities.derive.connectBlind(
                requirement_widget,
                functools.partial(
                    self.reflect_requirement_change,
                    requirement_widget,
                    requirement.name(),
                    component,
                ),
            )

            layout_to_add_into = self.requirement_layout

            if requirement.group():
                if requirement.group() in group_layouts:
                    layout_to_add_into = group_layouts[requirement.group()]

                else:
                    # -- Create the new layout
                    layout = qute.QVBoxLayout()

                    # -- Create the group box
                    group_box = qute.QGroupBox(requirement.group())
                    group_box.setLayout(layout)

                    # -- Add the group box to the main layout
                    self.requirement_layout.addWidget(group_box)

                    # -- Store this so that we only create one instance of it
                    # -- and mark this as the layout to add the widget into
                    layout_to_add_into = layout
                    group_layouts[requirement.group()] = layout

            if hasattr(requirement_widget, "HIDE_LABEL") and requirement_widget.HIDE_LABEL:
                # # -- Add the widget into the ui
                layout_to_add_into.addWidget(
                    requirement_widget,
                )

            else:
                # # -- Add the widget into the ui
                layout_to_add_into.addLayout(
                    qute.utilities.widgets.addLabel(
                        requirement_widget,
                        string.capwords(requirement.name().replace('_', ' ')),
                        150,
                        slim=False,
                    ),
                )

        self.requirement_layout.addSpacerItem(
            qute.QSpacerItem(
                10,
                0,
                qute.QSizePolicy.Expanding,
                qute.QSizePolicy.Expanding,
            ),
        )

    # ----------------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    @classmethod
    def reflect_requirement_change(cls, widget, option_name, component, *args, **kwargs):
        """
        This is called whenever an option ui element is changed. Within this function
        we must push the changed value back into the component

        Args:
            widget: Widget to read the value from
            option_name: Name of the option to update
            component: xstack.Component instance to update
            *args:
            **kwargs:

        Returns:
            None
        """
        component.requirement(option_name).set(
            qute.utilities.derive.deriveValue(
                widget,
            ),
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class OutputWidget(qute.QWidget):

    changed = qute.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, output, parent: qute.QWidget = None):
        super(OutputWidget, self).__init__(parent=parent)

        self._output_attribute = output

        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QHBoxLayout(),
            ),
        )

        self.field = qute.QLineEdit()
        self.field.setReadOnly(True)
        self.field.setMinimumHeight(30)
        self.copy_button = qute.QPushButton()
        self.copy_button.setIcon(
            qute.QIcon(
                resources.get(
                    "address.png",
                ),
            ),
        )
        self.copy_button.setIconSize(
            qute.QSize(
                20,
                20,
            ),
        )

        self.layout().addWidget(self.field)
        self.layout().addWidget(self.copy_button)

        self.copy_button.clicked.connect(self.copy_link)

    # ----------------------------------------------------------------------------------
    def set_value(self, value):
        self.field.setText(value)

    # ----------------------------------------------------------------------------------
    def get_value(self):
        return self.field.text()

    # ----------------------------------------------------------------------------------
    def copy_link(self):
        qute.qApp().clipboard().setText(
            self._output_attribute.address()
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,DuplicatedCode
class OutputsWidget(qute.QWidget):
    """
    This widget manages the display of the options
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, parent: qute.QWidget = None):
        super(OutputsWidget, self).__init__(parent=parent)

        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )

        self.output_layout = qute.QVBoxLayout()
        self.output_layout.setContentsMargins(10, 10, 10, 10)

        self.layout().addLayout(self.output_layout)

    # ----------------------------------------------------------------------------------
    def reflect_output_change(self, widget, output):
        if widget():
            widget().set_value(output.get())

    # ----------------------------------------------------------------------------------
    # noinspection PyUnresolvedReferences
    def set_component(self, component: xstack.Component):
        """
        This sets the target component for the widget and populates the widget
        with all the options.
        """

        # -- Clear the current layout of options
        qute.utilities.layouts.empty(self.output_layout)

        # -- If we do not have a component we dont need to populate anything
        if not component:
            return

        group_layouts = dict()

        for output in component.outputs():

            # -- Get the option object
            output_widget = OutputWidget(output=output, parent=self)

            output_widget.setToolTip(
                output.description(),
            )
            
            output_widget.set_value(output.get())

            # -- Hook up a connection such that when this option ui changes we
            # -- reflect that change into the component
            output.value_changed.connect(
                functools.partial(
                    self.reflect_output_change,
                    weakref.ref(output_widget),
                    output,
                )
            )

            layout_to_add_into = self.output_layout

            if output.group():
                if output.group() in group_layouts:
                    layout_to_add_into = group_layouts[output.group()]

                else:
                    # -- Create the new layout
                    layout = qute.QVBoxLayout()

                    # -- Create the group box
                    group_box = qute.QGroupBox(output.group())
                    group_box.setLayout(layout)

                    # -- Add the group box to the main layout
                    self.output_layout.addWidget(group_box)

                    # -- Store this so that we only create one instance of it
                    # -- and mark this as the layout to add the widget into
                    layout_to_add_into = layout
                    group_layouts[output.group()] = layout

            layout_to_add_into.addLayout(
                qute.utilities.widgets.addLabel(
                    output_widget,
                    string.capwords(output.name().replace('_', ' ')),
                    150,
                    slim=False,
                ),
            )

        # -- Always add in a spacer to push all the widgets up to the top
        self.output_layout.addSpacerItem(
            qute.QSpacerItem(
                10,
                0,
                qute.QSizePolicy.Expanding,
                qute.QSizePolicy.Expanding,
            ),
        )

    # ----------------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    @classmethod
    def reflect_option_change(cls, widget, option_name, component, *args, **kwargs):
        """
        This is called whenever an option ui element is changed. Within this function
        we must push the changed value back into the component

        Args:
            widget: Widget to read the value from
            option_name: Name of the option to update
            component: xstack.Component instance to update
            *args:
            **kwargs:

        Returns:
            None
        """
        component.option(option_name).set(
            qute.utilities.derive.deriveValue(
                widget,
            ),
        )

