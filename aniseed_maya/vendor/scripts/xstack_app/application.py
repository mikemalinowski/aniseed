import qute
import xstack
import typing
import functools

from . import resources
from . import options
from . import config
from . import tree
from . import settings


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class AppWidget(qute.QWidget):
    """
    This is the main widget that brings together the tree view and the options
    view

    Args:
        app_config: This is a class that inherits from xstack_app.AppConfig. You can
            use this to tailor how this application presents information and terminology
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, app_config=None, parent: qute.QWidget = None):
        super(AppWidget, self).__init__(parent=parent)

        self.settings_id = "xstack_app"

        # -- Store the stack
        self.stack = None

        # -- Store the app config
        self.app_config = app_config or config.AppConfig

        # -- These are properties used in full mode
        self.tree_widget = None
        self.editor_widget = None
        self.splitter = None

        # -- These are for our menu system
        self.menu_bar = None

        # -- Set the layout
        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )

        # -- Add the splash widget whilst we're not seeing any rigs
        self.add_splash()

        # -- Construct the menu on startup
        self.build_menu()

    # ----------------------------------------------------------------------------------
    def add_splash(self):
        """
        Adds a splash widget into the layout
        """
        # -- Add the splash image to the background whilst its blank
        splash = qute.QLabel()
        splash.setPixmap(
            qute.QPixmap(
                self.app_config.icon,
            ),
        )
        splash.setAlignment(qute.Qt.AlignVCenter  | qute.Qt.AlignHCenter )
        self.layout().addWidget(splash)

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
    def set_active_stack(self, stack: xstack.Stack or None):
        """
        This function will rebuild the layout of the tool based on the stack we expect
        to be showing as the currently active stack
        """
        # -- If we have not been given a stack, we clear the layout and
        # -- rebuild the menu
        if not stack:

            # -- Empty the current layout
            qute.utilities.layouts.empty(
                self.layout(),
            )

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
        self.menu_bar = qute.QMenuBar(parent=self)

        # -- Add the stacks menu to the menu
        stacks_menu = qute.QMenu("File", parent=self)

        # -- We always expose the new stack option regardless of what is in the scene
        new_stack_action = stacks_menu.addAction(
            qute.QIcon(self.app_config.icon),
            f"New {stack_label}",
       )

        new_stack_action.triggered.connect(
            functools.partial(
                self.create_new_stack,
            )
        )
        stacks_menu.addSeparator()

        import_stack_action = stacks_menu.addAction(
            qute.QIcon(self.app_config.open_icon),
            f"Open {stack_label} File",
        )

        import_stack_action.triggered.connect(
            functools.partial(
                self.import_stack,
            )
        )

        export_stack_action = stacks_menu.addAction(
            qute.QIcon(self.app_config.save_icon),
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
        settings_menu = qute.QMenu("Edit", parent=self)

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

    # ----------------------------------------------------------------------------------
    def build_layout(self):
        """
        This will build the overall content of the tool
        """
        # -- Empty the current layout
        qute.utilities.layouts.empty(
            self.layout(),
        )

        self.splitter = qute.QSplitter()
        self.layout().addWidget(self.splitter)

        self.tree_widget = tree.BuildTreeWidget(self.stack, self.app_config, parent=self)
        self.splitter.addWidget(self.tree_widget)
        self.tree_widget.currentItemChanged.connect(self.propogate_component_selection)

        self.editor_widget = options.ComponentEditor(parent=self)
        self.splitter.addWidget(self.editor_widget)

        self.layout().setStretch(0, 1)
        self.layout().setStretch(1, 0)

        self.set_layout_orientation()

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

        widget_is_wide = self.rect().width() > self.rect().height()
        use_horizontal_alignment = widget_is_wide

        if force_horizontal:
            use_horizontal_alignment = True

        if force_vertical:
            use_horizontal_alignment = False

        if use_horizontal_alignment:
            self.layout().setDirection(qute.QBoxLayout.LeftToRight)
            self.splitter.setOrientation(qute.Qt.Horizontal)
        else:
            self.layout().setDirection(qute.QBoxLayout.TopToBottom)
            self.splitter.setOrientation(qute.Qt.Vertical)

    # ----------------------------------------------------------------------------------
    def create_new_stack(self):
        """
        This will take the user through the flow of generating a new stack

        :return:
        """
        stack_label = self.app_config.label
        
        name = qute.utilities.request.text(
            title=f"New {stack_label}",
            label=f"Please provide a name for the {stack_label}",
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
    def import_stack(self):
        """
        This defines the user flow for importing stack data
        """

        stack_label = self.app_config.label

        confirmation = qute.utilities.request.confirmation(
            title=f"Import {stack_label}",
            label=(
                f"Importing a {stack_label} will clear any current {stack_label} data. "
                "Are you sure you want to continue?"
            ),
            parent=self,
        )

        if not confirmation:
            return

        filepath = qute.utilities.request.filepath(
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

        filepath = qute.utilities.request.filepath(
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
class AppWindow(qute.QMainWindow):

    def __init__(self, app_config=None, *args, **kwargs):
        super(AppWindow, self).__init__(*args, **kwargs)

        self.app_config = app_config or config.AppConfig

        # -- Set the window properties
        self.setObjectName(self.app_config.label)
        self.setWindowTitle(self.app_config.label)

        if self.app_config.icon:
            self.setWindowIcon(
                qute.QIcon(
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
        qute.applyStyle(
            [
                'space',
                resources.get("style.css")
            ],
            self,
            **custom_overrides
        )

        widget = self.app_config.app_widget or AppWidget

        self.setCentralWidget(
            widget(
                app_config=app_config,
                parent=self,
            ),
        )


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnusedLocal
def launch(app_config=None, blocking: bool = True, *args, **kwargs):
    """
    This function should be called to invoke the app ui
    """
    q_app = qute.qApp()

    w = AppWindow(app_config=app_config, *args, **kwargs)
    w.show()

    if blocking:
        q_app.exec_()
