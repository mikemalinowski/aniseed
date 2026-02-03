import typing
import functools
import qtility
from Qt import QtWidgets, QtGui, QtCore

from . import resources
from . import options
from . import config
from . import tree
from . import settings
from . import runner


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class AppWidget(QtWidgets.QWidget):
    """
    This is the main widget that brings together the tree view and the options
    view

    Args:
        app_config: This is a class that inherits from xstack_app.AppConfig. You can
            use this to tailor how this application presents information and terminology
    """

    build_started = QtCore.Signal()
    build_complete = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, app_config=None, allow_threading=True, parent: QtWidgets.QWidget = None, storage_identifier="xstack"):
        super(AppWidget, self).__init__(parent=parent)

        self.settings_id = "xstack_app"

        # -- Store the stack
        self.stack = None
        self.allow_threading = allow_threading
        self.run_thread = None

        # -- Store the app config
        self.app_config = app_config or config.AppConfig

        # -- These are properties used in full mode
        self.tree_widget = None
        self.editor_widget = None
        self.splitter = None

        # -- These are for our menu system
        self.menu_bar = None
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)

        # -- Set the layout
        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )

        # -- Add the splash widget whilst we're not seeing any rigs
        self.add_splash()

        # -- Construct the menu on startup
        self.build_menu()

        self.build_started.connect(self.on_build_started)
        self.build_complete.connect(self.on_build_complete)

    def build(self, build_below=None, validate_only=False):
        """
        This will trigger a threaded build of the stack

        Args:
            build_below: This will trigger a build of only components within this
                component and below
            validate_only: This will trigger a validation pass only
        """
        self.build_started.emit()
        if self.allow_threading:
            self.run_thread = runner.ThreadedRun(
                stack=self.stack,
                build_below=build_below,
                validate_only=validate_only,
            )
            self.run_thread.build_progressed.connect(self.update_progressbar)
            self.run_thread.finished.connect(self.build_complete.emit)
            self.run_thread.start()

        else:
            self.stack.build_progressed.connect(self.update_progressbar)
            self.stack.build(
                build_below=build_below,
                validate_only=validate_only,
            )
            self.build_complete.emit()

    def update_progressbar(self, percentage):
        """
        This will update the progress bar value with the given percentage

        Args:
            percentage: The percentage value to update
        """
        self.progress_bar.setValue(percentage)
        self.progress_bar.setFormat(f"Running : {int(percentage)}%")

    def on_build_started(self):
        """
        This event is called with the build of the stack is initiated.
        """
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.menu_bar.setEnabled(False)
        self.editor_widget.setVisible(False)

    def on_build_complete(self):
        """
        This event is called when the build is complete
        """
        self.progress_bar.setVisible(False)
        self.menu_bar.setEnabled(True)
        self.editor_widget.setVisible(True)

    # ----------------------------------------------------------------------------------
    def add_splash(self):
        """
        Adds a splash widget into the layout
        """
        # -- Add the splash image to the background whilst its blank
        splash = QtWidgets.QLabel(parent=self)
        self.layout().addWidget(splash)
        splash.setPixmap(
            QtGui.QPixmap(
                self.app_config.icon,
            ),
        )
        splash.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter )
        return splash

    # ----------------------------------------------------------------------------------
    def additional_menus(self) -> typing.List:
        """
        This function may be re-implemented when subclassing to request the addition
        of further menu items

        When re-implementing you should return a list of QMenu's you want to add
        to the app widgets titlebar
        :return:
        """
        return list()
    
    # ----------------------------------------------------------------------------------
    def set_active_stack(self, stack: "xstack.Stack" or None):
        """
        This function will rebuild the layout of the tool based on the stack we expect
        to be showing as the currently active stack
        """
        # -- Empty the current layout
        qtility.layouts.empty(
            self.layout(),
        )

        # -- If we have not been given a stack, we clear the layout and
        # -- rebuild the menu
        if not stack:


            self.tree_widget = None
            self.editor_widget = None
            self.splitter = None

            self.add_splash()
            self.build_menu()

            return

        # -- We have been given a stack, so set the stack instance and rebuild
        # -- the layout.
        self.stack = stack
        self.build_layout()

    # ----------------------------------------------------------------------------------
    def build_menu(self):
        """
        This will regenerate the tool menu
        """
        # -- We do not hard code the term "stack" into the App. This is because the
        # -- stack library will be used for many purposes, and in most cases the user
        # -- will want to tailor the terminology. Therefore we get the label from
        # -- the app configuration class.
        stack_label = self.app_config.label

        # -- Create a new menu bar
        self.menu_bar = QtWidgets.QMenuBar(parent=self)

        # -- Add the stacks menu to the menu
        stacks_menu = QtWidgets.QMenu("File", parent=self)

        # -- We always expose the new stack option regardless of what is in the scene
        new_stack_action = stacks_menu.addAction(
            QtGui.QIcon(self.app_config.icon),
            f"New {stack_label}",
       )

        new_stack_action.triggered.connect(
            functools.partial(
                self.create_new_stack,
            )
        )
        stacks_menu.addSeparator()

        import_stack_action = stacks_menu.addAction(
            QtGui.QIcon(self.app_config.open_icon),
            f"Open {stack_label} File",
        )

        import_stack_action.triggered.connect(
            functools.partial(
                self.import_stack,
            )
        )

        export_stack_action = stacks_menu.addAction(
            QtGui.QIcon(self.app_config.save_icon),
            f"Save {stack_label} File",
        )
        export_stack_action.triggered.connect(
            functools.partial(
                self.export_stack,
            )
        )
        stacks_menu.addSeparator()

        self.menu_bar.addMenu(stacks_menu)

        # -- Create the settings menu
        settings_menu = QtWidgets.QMenu("Edit", parent=self)

        settings_editor_action = settings_menu.addAction(f"Preferences")
        settings_editor_action.triggered.connect(
            functools.partial(
                settings.show_settings,
                self.app_config,
            ),
        )
        self.menu_bar.addMenu(settings_menu)

        for additional_menu in self.additional_menus():
            self.menu_bar.addMenu(additional_menu)
            
        # -- Finally, apply the menu bar
        self.layout().setMenuBar(self.menu_bar)


        # -- If we're asked not to show the menu then lets immediately
        # -- exit.
        self.menu_bar.setVisible(self.app_config.show_menu_bar)

    # ----------------------------------------------------------------------------------
    def build_layout(self):
        """
        This will build the overall content of the tool
        """
        # -- Empty the current layout
        qtility.layouts.empty(
            self.layout(),
        )

        self.flexible_layout = QtWidgets.QVBoxLayout()
        self.layout().addLayout(self.flexible_layout)

        self.splitter = QtWidgets.QSplitter()
        self.flexible_layout.addWidget(self.splitter)

        self.tree_widget = tree.BuildTreeWidget(self.stack, self.app_config, app=self)
        self.splitter.addWidget(self.tree_widget)
        self.tree_widget.currentItemChanged.connect(self.propogate_component_selection)

        self.editor_widget = options.ComponentEditor(parent=self)
        self.splitter.addWidget(self.editor_widget)

        self.flexible_layout.setStretch(0, 1)
        self.flexible_layout.setStretch(1, 0)

        self.set_layout_orientation()

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.layout().addWidget(self.progress_bar)

        if self.app_config.splitter_bias is not None:
            orientation = self.splitter.orientation()

            if orientation == QtCore.Qt.Vertical:
                scope = self.height()
            else:
                scope = self.width()

            tree_size = scope * self.app_config.splitter_bias
            option_size = scope - tree_size

            self.splitter.setSizes([tree_size, option_size])

    # ----------------------------------------------------------------------------------
    def set_layout_orientation(self):
        """
        We adjust the layout of the tool based on whether its wide or tall - as
        different users like to work in different states.
        """

        if not self.tree_widget:
            return

        force_vertical = False
        force_horizontal = False

        if not self.app_config.get_setting("auto_adjust_orientiation"):

            if self.app_config.get_setting("use_vertical_alignment"):
                force_vertical = True

            else:
                force_horizontal = True

        if self.app_config.forced_orientation == "vertical":
            force_vertical = True
            force_horizontal = False

        if self.app_config.forced_orientation == "horizontal":
            force_vertical = False
            force_horizontal = True

        widget_is_wide = self.rect().width() > self.rect().height()
        use_horizontal_alignment = widget_is_wide

        if force_horizontal:
            use_horizontal_alignment = True

        if force_vertical:
            use_horizontal_alignment = False

        if use_horizontal_alignment:
            self.flexible_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
            self.splitter.setOrientation(QtCore.Qt.Horizontal)
        else:
            self.flexible_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
            self.splitter.setOrientation(QtCore.Qt.Vertical)

    # ----------------------------------------------------------------------------------
    def create_new_stack(self):
        """
        This will take the user through the flow of generating a new stack

        :return:
        """
        stack_label = self.app_config.label
        
        name = qtility.request.text(
            title=f"New {stack_label}",
            message=f"Please provide a name for the {stack_label}",
            parent=self,
        )

        if not name:
            return

        new_stack = self.app_config.stack_class(
            label=name,
            component_paths=self.app_config.component_paths,
        )

        self.set_active_stack(new_stack)
        self.build_menu()

        return new_stack

    # ----------------------------------------------------------------------------------
    def import_stack(self, filepath=None, silent=False):
        """
        This defines the user flow for importing stack data
        """

        stack_label = self.app_config.label

        if not silent:
            confirmation = qtility.request.confirmation(
                title=f"Import {stack_label}",
                message=(
                    f"Importing a {stack_label} will clear any current {stack_label} data. "
                    "Are you sure you want to continue?"
                ),
                parent=self,
            )

            if not confirmation:
                return

        if not filepath:
            filepath = qtility.request.filepath(
                title=f"Import {stack_label}",
                filter_="*.json (*.json)",
                parent=self,
                save=False,
            )

        new_stack = self.app_config.stack_class.load(
            data=filepath,
            component_paths=self.app_config.component_paths,
        )

        self.set_active_stack(new_stack)

        return filepath

    # ----------------------------------------------------------------------------------
    def export_stack(self, additional_data=None):
        """
        Exports the current stack to a stack file
        """
        stack_label = self.app_config.label

        filepath = qtility.request.filepath(
            title=f"Export {stack_label}",
            filter_="*.json (*.json)",
            save=True,
            parent=self,
        )

        self.stack.save(
            filepath,
            additional_data=additional_data,
        )

    # ----------------------------------------------------------------------------------
    def propogate_component_selection(self, *args, **kwargs):
        """
        We use this as a pass-through mechanism, so that when a component is selected
        in the tree view we call the set_component in the editor panel.
        """
        component = self.tree_widget.current_component()

        if not component:
            return
        self.editor_widget.set_component(component)

    # ----------------------------------------------------------------------------------
    # noinspection PyPep8Naming
    def resizeEvent(self, event):
        """
        Wen the window is resized check out layout orientation
        """
        super(AppWidget, self).resizeEvent(event)
        self.set_layout_orientation()


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class AppWindow(qtility.windows.MemorableWindow):

    def __init__(self, app_config=None, allow_threading=True, storage_identifier="xstack", *args, **kwargs):
        super(AppWindow, self).__init__(storage_identifier=storage_identifier, *args, **kwargs)

        self.app_config = app_config or config.AppConfig

        # -- Set the window properties
        self.setObjectName(self.app_config.label)
        self.setWindowTitle(self.app_config.label)

        if self.app_config.icon:
            self.setWindowIcon(
                QtGui.QIcon(
                    self.app_config.icon,
                ),
            )

        custom_overrides = {
            "_ITEMHIGHLIGHT_": ",".join(
                [
                    str(n)
                    for n in self.app_config.item_highlight_color
                ]
            )
        }

        # # -- Apply our styling, defining some differences
        qtility.styling.apply(
            [
                resources.get('space'),
                resources.get("style.css")
            ],
            self,
            **custom_overrides
        )

        widget = self.app_config.app_widget or AppWidget
        self.core = widget(
            app_config=app_config,
            allow_threading=allow_threading,
            parent=self,
        )
        self.setCentralWidget(self.core)


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnusedLocal
def launch(app_config=None, blocking: bool = True, load_file: str = None, run_on_launch: bool = False, allow_threading=True, active_stack=None, storage_identifier="xstack", *args, **kwargs):
    """
    This function should be called to invoke the app ui
    """
    q_app = qtility.app.get()

    w = AppWindow(app_config=app_config, allow_threading=allow_threading, storage_identifier=storage_identifier, *args, **kwargs)
    w.show()

    if load_file:
        w.core.import_stack(filepath=load_file, silent=True)

    if active_stack:
        w.core.set_active_stack(active_stack)

    if run_on_launch and self.core.stack:
        w.core.build()

    if blocking:
        q_app.exec_()

    return w
