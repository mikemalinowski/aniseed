import string
import weakref
import qtility
import functools
from Qt import QtWidgets, QtCore, QtGui

from . import resources


# ----------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ComponentEditor(QtWidgets.QWidget):
    """
    The component editor shows the tabs for both the requirements and the options
    of a component.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(ComponentEditor, self).__init__(parent=parent)

        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )
        self.component = None

        # -- Now start populating the content
        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        self.options_widget = OptionsWidget()
        self.inputs_widget = InputsWidget(parent=self)
        self.outputs_widget = OutputsWidget(parent=self)

        self.tab_widget.addTab(
            self.inputs_widget,
            "Inputs",
        )

        self.tab_widget.addTab(
            self.options_widget,
            "Options"
        )

        self.tab_widget.addTab(
            self.outputs_widget,
            "Outputs"
        )

        for i in range(3):
            self.tab_widget.setTabVisible(i, False)

    # ----------------------------------------------------------------------------------
    def set_component(self, component: "xstack.Component"):
        """
        Applies the component to the options and the inputs widgets
        """

        inputs_visibility = True if (component and len(component.inputs()) > 0) else False
        options_visibility = True if (component and len(component.options()) > 0) else False
        outputs_visibility = True if (component and len(component.outputs()) > 0) else False

        self.tab_widget.setTabVisible(0, inputs_visibility)
        self.tab_widget.setTabVisible(1, options_visibility)
        self.tab_widget.setTabVisible(2, outputs_visibility)

        self.options_widget.set_component(component)
        self.inputs_widget.set_component(component)
        self.outputs_widget.set_component(component)

        self.component = weakref.ref(component)

    # ----------------------------------------------------------------------------------
    def redraw(self):
        if self.component():
            self.set_component(self.component())

# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,DuplicatedCode
class OptionsWidget(QtWidgets.QWidget):
    """
    This widget manages the display of the options
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, pre_expose_only=False, parent: QtWidgets.QWidget = None):
        super(OptionsWidget, self).__init__(parent=parent)

        # -- This determines if we show all options, or only options that
        # -- are marked as pre-expsure
        self._pre_expose_only = pre_expose_only

        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )

        self.option_layout = QtWidgets.QVBoxLayout()
        self.option_layout.setContentsMargins(10, 10, 10, 10)

        self.help_text = QtWidgets.QLabel()
        self.help_text.setWordWrap(True)

        self.layout().addWidget(self.help_text)
        self.layout().addLayout(self.option_layout)

    # ----------------------------------------------------------------------------------
    # noinspection PyUnresolvedReferences
    def set_component(self, component: "xstack.Component" or None):
        """
        This sets the target component for the widget and populates the widget
        with all the options.
        """
        # -- Clear the current layout of options
        qtility.layouts.empty(self.option_layout)

        # -- If we do not have a component we dont need to populate anything
        if not component:
            self.help_text.setText("")
            return

        # -- Update the help text
        self.help_text.setText(component.documentation())

        group_layouts = dict()

        for option in component.options():

            if option.hidden():
                continue

            if self._pre_expose_only and not option.should_pre_expose():
                continue

            # -- Get the option object
            option_widget = component.option_widget(option.name())

            # -- Get the raw value, as we want to see the address
            # -- if its an address
            option_value = option.get(resolved=False)

            # -- If we were not given a widget, then as qute to derive one
            # -- for us
            if not option_widget:
                option_widget = qtility.derive.qwidget(
                    option_value,
                )

            if not option_widget:
                print(f"Could not resolve a widget for : {option.name()}")
                continue

            option_widget.setToolTip(
                option.description(),
            )

            # -- Set the value of the widget
            qtility.derive.apply(
                option_widget,
                option_value,
            )

            # -- Hook up a connection such that when this option ui changes we
            # -- reflect that change into the component
            qtility.derive.connect(
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
                    layout = QtWidgets.QVBoxLayout()

                    # -- Create the group box
                    group_box = QtWidgets.QGroupBox(option.group())
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
                    qtility.widgets.addLabel(
                        option_widget,
                        string.capwords(option.name().replace('_', ' ')),
                        150,
                        slim=False,
                    ),
                )

        # -- Always add in a spacer to push all the widgets up to the top
        self.option_layout.addSpacerItem(
            QtWidgets.QSpacerItem(
                10,
                0,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
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
            qtility.derive.value(
                widget,
            ),
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class InputsWidget(QtWidgets.QWidget):
    """
    This widget manages the display of the inputs of a component.

    Note: This is currently largely a copy of the Options Widget, however both
    serve a unique purpose and will likely branch in the future, so they are each
    getting their own classes.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, pre_expose_only=False, parent: QtWidgets.QWidget = None):
        super(InputsWidget, self).__init__(parent=parent)

        # -- This determines if we show all inputs, or only inputs that
        # -- are marked as pre-expsure
        self._pre_expose_only = pre_expose_only

        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )

        self.inputs_layout = QtWidgets.QVBoxLayout()
        self.inputs_layout.setContentsMargins(10, 10, 10, 10)

        self.help_text = QtWidgets.QLabel()
        self.help_text.setWordWrap(True)

        self.layout().addWidget(self.help_text)
        self.layout().addLayout(self.inputs_layout)

    # ----------------------------------------------------------------------------------
    # noinspection DuplicatedCode
    def set_component(self, component: "xstack.Component"):
        """
        This sets the target component for the widget and populates the widget
        with all hte inputs.
        """
        # -- Clear the current layout of options
        qtility.layouts.empty(self.inputs_layout)

        # -- If we do not have a component we dont need to populate anything
        if not component:
            self.help_text.setText("")
            return

        # -- Update the help text
        self.help_text.setText(component.documentation())

        group_layouts = dict()

        for input_ in component.inputs():

            if input_.hidden():
                continue

            if self._pre_expose_only and not input_.should_pre_expose():
                continue

            # -- Get the input widget
            input_widget = component.input_widget(input_.name())

            # -- If we were not given a widget, then as qute to derive one
            # -- for us
            if not input_widget:
                input_widget = qtility.derive.qwidget(
                    input_.get()
                )

            if not input_widget:
                print(f"Could not resolve a widget for : {input_.name()}, {input_.get()}")
                continue

            input_widget.setToolTip(
                input_.description(),
            )

            # -- Get the raw value. If its an address, we want to specifically
            # -- get the address back and not the resolved value
            input_value = input_.get(resolved=False)

            # -- Set the value of the widget
            qtility.derive.apply(
                input_widget,
                input_value,
            )

            # -- Hook up a connection such that when this input ui changes we
            # -- reflect that change into the component
            qtility.derive.connect(
                input_widget,
                functools.partial(
                    self.reflect_input_change,
                    input_widget,
                    input_.name(),
                    component,
                ),
            )

            layout_to_add_into = self.inputs_layout

            if input_.group():
                if input_.group() in group_layouts:
                    layout_to_add_into = group_layouts[input_.group()]

                else:
                    # -- Create the new layout
                    layout = QtWidgets.QVBoxLayout()

                    # -- Create the group box
                    group_box = QtWidgets.QGroupBox(input_.group())
                    group_box.setLayout(layout)

                    # -- Add the group box to the main layout
                    self.inputs_layout.addWidget(group_box)

                    # -- Store this so that we only create one instance of it
                    # -- and mark this as the layout to add the widget into
                    layout_to_add_into = layout
                    group_layouts[input_.group()] = layout

            if hasattr(input_widget, "HIDE_LABEL") and input_widget.HIDE_LABEL:
                # # -- Add the widget into the ui
                layout_to_add_into.addWidget(
                    input_widget,
                )

            else:
                # # -- Add the widget into the ui
                layout_to_add_into.addLayout(
                    qtility.widgets.addLabel(
                        input_widget,
                        string.capwords(input_.name().replace('_', ' ')),
                        150,
                        slim=False,
                    ),
                )

        self.inputs_layout.addSpacerItem(
            QtWidgets.QSpacerItem(
                10,
                0,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            ),
        )

    # ----------------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    @classmethod
    def reflect_input_change(cls, widget, option_name, component, *args, **kwargs):
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
        component.input(option_name).set(
            qtility.derive.value(
                widget,
            ),
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class OutputWidget(QtWidgets.QWidget):

    changed = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, output, parent: QtWidgets.QWidget = None):
        super(OutputWidget, self).__init__(parent=parent)

        self._output_attribute = output

        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QHBoxLayout(),
            ),
        )

        self.field = QtWidgets.QLineEdit()
        self.field.setReadOnly(True)
        self.field.setMinimumHeight(30)
        self.copy_button = QtWidgets.QPushButton()
        self.copy_button.setIcon(
            QtGui.QIcon(
                resources.get(
                    "address.png",
                ),
            ),
        )
        self.copy_button.setIconSize(
            QtCore.QSize(
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
        QtWidgets.qApp().clipboard().setText(
            self._output_attribute.address()
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,DuplicatedCode
class OutputsWidget(QtWidgets.QWidget):
    """
    This widget manages the display of the options
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, parent: QtWidgets.QWidget = None):
        super(OutputsWidget, self).__init__(parent=parent)

        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )

        self.output_layout = QtWidgets.QVBoxLayout()
        self.output_layout.setContentsMargins(10, 10, 10, 10)

        self.help_text = QtWidgets.QLabel()
        self.help_text.setWordWrap(True)

        self.layout().addWidget(self.help_text)
        self.layout().addLayout(self.output_layout)

    # ----------------------------------------------------------------------------------
    def reflect_output_change(self, widget, output):
        if widget():
            widget().set_value(output.get())

    # ----------------------------------------------------------------------------------
    # noinspection PyUnresolvedReferences
    def set_component(self, component: "xstack.Component"):
        """
        This sets the target component for the widget and populates the widget
        with all the options.
        """

        # -- Clear the current layout of options
        qtility.layouts.empty(self.output_layout)

        # -- If we do not have a component we dont need to populate anything
        if not component:
            self.help_text.setText("")
            return

        # -- Update the help text
        self.help_text.setText(component.documentation())

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
                    layout = QtWidgets.QVBoxLayout()

                    # -- Create the group box
                    group_box = QtWidgets.QGroupBox(output.group())
                    group_box.setLayout(layout)

                    # -- Add the group box to the main layout
                    self.output_layout.addWidget(group_box)

                    # -- Store this so that we only create one instance of it
                    # -- and mark this as the layout to add the widget into
                    layout_to_add_into = layout
                    group_layouts[output.group()] = layout

            layout_to_add_into.addLayout(
                qtility.widgets.addLabel(
                    output_widget,
                    string.capwords(output.name().replace('_', ' ')),
                    150,
                    slim=False,
                ),
            )

        # -- Always add in a spacer to push all the widgets up to the top
        self.output_layout.addSpacerItem(
            QtWidgets.QSpacerItem(
                10,
                0,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
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
            qtility.derive.value(
                widget,
            ),
        )

