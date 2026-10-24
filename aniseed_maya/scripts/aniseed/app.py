import json
import xstack
import typing
import logging
import qtility
import crosswalk
import functools

from Qt import QtWidgets, QtCore, QtGui

from . import Rig
from . import host
from . import config
from . import resources

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
class AppConfig(xstack.app.AppConfig):
    """
    The AppConfig class allows us to tailor how the xstack app is represented. It
    gives us the opportunity to tailor certain wording and branding to align with the
    end use cases.

    It also allows us to define component paths as well as the stack class we
    want to use.
    """

    # -- These allow applications to tailor their appearance and
    # -- terminology
    label = "Rig"
    execute_label = "Build"
    component_label = "Component"

    # -- Override some of the icons to be specific to aniseed
    icon = resources.get("icon.png")
    component_icon = resources.get("component.png")
    stack_background = resources.get("stack_background.png")

    # -- Ensure we declare the Rig class as being the base class for our
    # -- stacks. The Rig class inherits from xstack.Stack but adds in some
    # -- rig and application specific layers
    stack_class = Rig

    # -- Colouring
    default_text_color = [255, 255, 255]

    # -- Note: the aniseed/components path is added inside Rig.__init__
    # -- itself, so AppConfig does not need to redeclare it here. Add
    # -- extra paths to ``component_paths`` only for project-specific
    # -- overrides.

    # -- Override some of the colouring
    item_highlight_color = [100, 255, 100]

    # -- The log tab always shows records from these loggers, as well as
    # -- everything logged or printed during a build
    log_logger_names = [
        "xstack",
        "aniseed",
        "aniseed_toolkit",
        "aniseed_maya_standard",
    ]

    # -- Add in settings specific to rigging.
    settings_id = "aniseed_settings"

    additional_settings = {
        "auto_generate_rig_config": True,
        "default_rig_config": "Rig Configuration : Standard",
    }


# --------------------------------------------------------------------------------------
class AppWidget(xstack.app.AppWidget):
    """
    We subclass the app widget class as in the context of rigging we want to be
    able to switch rigs via the menu.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        self.buttons = None
        super().__init__(*args, **kwargs)

        self._host = ""

        # -- Find all the rigs in the scene
        rigs = self.all_rigs()

        # -- If we have any rigs, use the first one as the active rig by default
        if rigs:
            self.switch_rig(rigs[0])

    # ----------------------------------------------------------------------------------
    def set_active_stack(self, stack: typing.Optional["xstack.Stack"]):
        super().set_active_stack(stack)

        # -- We dynamically show a button for each execution block component
        # -- in the stack.
        self.create_buttons()

    # ----------------------------------------------------------------------------------
    def create_buttons(self):
        """
        This creates a button widget which shows a button for each execution component
        in the stack
        """
        if self.buttons is not None:
            try:
                self.buttons.setParent(None)
                self.buttons.deleteLater()
            except RuntimeError:
                # -- C++ side was already deleted by qtility.layouts.empty's
                # -- deleteLater pump catching up. The Python wrapper is
                # -- the only thing left; we just drop it.
                pass
            self.buttons = None

        if not self.stack:
            return

        # -- Add the button layout
        self.buttons = ButtonWidget(app_widget=self)
        self.stack.changed.connect(self.buttons.populate)
        self.stack_layout().addWidget(self.buttons)
        self.stack_layout().setStretch(0, 1)

    # ----------------------------------------------------------------------------------
    def create_new_stack(self):
        """
        Takes the user through creating a new rig: asking for its name and the
        rig configuration to use. Nothing is left in the scene if the user
        cancels either prompt, or if there is no configuration to use.

        Returns the new rig, or None if no rig was created.
        """
        stack_label = self.app_config.label

        name = qtility.request.text(
            title=f"New {stack_label}",
            message=f"Please provide a name for the {stack_label}",
            parent=self,
        )

        if not name:
            return None

        rig = self.app_config.stack_class(
            label=name,
            component_paths=self.app_config.component_paths,
        )

        configuration = self._request_configuration(rig)

        if not configuration:

            # -- Do not leave an empty rig behind for a rig the user abandoned
            rig_host = rig.host()
            rig.dispose()
            crosswalk.items.delete(rig_host)
            return None

        rig.add_component(
            component_type=configuration,
            label="Configuration",
        )
        self.app_config.store_setting("default_rig_config", configuration)

        self.switch_stack(rig)
        self.build_menu()

        return rig

    # ----------------------------------------------------------------------------------
    def _request_configuration(self, rig: Rig) -> typing.Optional[str]:
        """
        Asks the user which rig configuration to use, starting on the one they
        last used. Returns None if they cancel or there are none available.
        """
        available_configs = [
            configuration.identifier
            for configuration in rig.component_library.plugins()
            if "Rig Configuration" in configuration.identifier
            and configuration.identifier != "Rig Configuration"
        ]

        if not available_configs:
            log.warning("No rig configurations are available, so a rig cannot be created")
            return None

        # -- The configuration used last time may no longer be available
        default_config = self.app_config.get_setting(
            "default_rig_config",
        )

        current = 0
        if default_config in available_configs:
            current = available_configs.index(default_config)

        return qtility.request.item(
            items=available_configs,
            current=current,
            title="Select Rig Configuration",
            message="Select a configuration to use",
            editable=False,
            parent=self,
        )

    # ----------------------------------------------------------------------------------
    def switch_stack(self, stack: "xstack.Stack"):
        """
        Both the new rig and open rig file flows come through here, so they
        switch rig in the same way as choosing a rig from the Rigs menu.
        """
        self.switch_rig(stack.host())

    # ----------------------------------------------------------------------------------
    def load_stack_file(self, filepath: str) -> typing.Optional["xstack.Stack"]:
        """
        Loads the rig file into the rig being shown, replacing its recipe, as
        the open flow warns it will. If no rig is being shown, a new rig is
        created from the file.
        """
        if not self.stack:
            return super().load_stack_file(filepath)

        # -- Read the file before touching the rig, so a file which cannot be
        # -- read leaves everything as it was
        with open(filepath, "r") as f:
            data = json.load(f)

        # -- Stop the ui reacting to every component as it loads. It is
        # -- rebuilt when the rig is switched to afterwards.
        self._teardown_stack()

        self.stack.deserialize(data)
        return self.stack

    # ----------------------------------------------------------------------------------
    def additional_menus(self) -> typing.List:
        """
        We override this function so that we can expose our rigs menu, allowing the
        user to quickly jump between rigs in the scene
        """
        # -- Add the rigs menu
        rigs_menu = QtWidgets.QMenu("Rigs")

        # -- Add the action to create a new rig
        new_rig_action = rigs_menu.addAction(f"New {self.app_config.label}")
        new_rig_action.triggered.connect(
            functools.partial(
                self.create_new_stack,
            )
        )
        rigs_menu.addSeparator()

        # -- Cycle all the rigs in the scene and add them into the menu too
        rigs = crosswalk.items.all_items_with_attribute(
            attribute_name="aniseed_rig",
        )

        for rig_host in rigs or list():
            switch_rig_action = rigs_menu.addAction(
                crosswalk.items.get_name(rig_host)
            )
            switch_rig_action.triggered.connect(
                functools.partial(
                    self.switch_rig,
                    rig_host,
                )
            )
        rigs_menu.addSeparator()

        menus = [rigs_menu]

        # -- Add any tools the host application provides
        host_app = host.get()
        tools = host_app.tools() if host_app else dict()

        if tools:
            tools_menu = QtWidgets.QMenu("Tools")

            for label, tool in tools.items():
                tool_action = tools_menu.addAction(label)
                tool_action.triggered.connect(
                    functools.partial(
                        tool,
                    )
                )

            menus.append(tools_menu)

        # -- Return a list of additional menus that should be added
        return menus

    # ----------------------------------------------------------------------------------
    def edit_menu_actions(self) -> typing.Dict[str, typing.Callable]:
        """
        Adds the Packages window to the Edit menu
        """
        return {
            "Packages...": self.show_package_manager,
        }

    # ----------------------------------------------------------------------------------
    def show_package_manager(self):
        """
        Shows the window for turning aniseed packages on and off
        """
        # -- Imported here, as it is only needed when the window is opened
        from . import package_manager

        package_manager.show(app_widget=self, parent=self)

    # ----------------------------------------------------------------------------------
    def all_rigs(self):
        """
        This will return the hosts of all the rigs in the scene
        """
        return crosswalk.items.all_items_with_attribute(
            attribute_name="aniseed_rig",
        )

    # ----------------------------------------------------------------------------------
    def switch_rig(self, rig_host=None):
        """
        This will update the active stack to represent the rig the user
        has selected. If no rig host is given, the first rig in the scene is
        shown, or nothing if there are none.

        The Rig shown is the shared instance for the host (see Rig.for_host), so
        scripts working on the same rig see the same data.
        """
        if not rig_host:
            try:
                rig_host = self.all_rigs()[0]
            except IndexError:
                # -- New scene has no rigs; tear the current stack down
                # -- cleanly so we don't leave OLD rig signals wired up
                # -- to widgets that are about to be ``deleteLater``'d.
                self._teardown_stack()
                self.set_active_stack(stack=None)
                self._host = ""
                return

        # -- Drop the previous rig's connections to this ui before we
        # -- replace it.
        self._teardown_stack()

        rig: Rig = self.app_config.stack_class.for_host(
            rig_host,
            component_paths=self.app_config.component_paths,
        )

        self.set_active_stack(
            stack=rig
        )
        self._host = crosswalk.items.get_name(rig_host)

        # -- Hook up signals and slots for implementation notifiers
        self.stack.component_added.connect(self.notify_component_added)
        self.stack.component_removed.connect(self.notify_component_removed)
        self.stack.build_started.connect(self.notify_build_started)
        self.stack.build_failed.connect(self.notify_build_failed)
        self.stack.build_finished.connect(self.notify_build_finished)

    # ----------------------------------------------------------------------------------
    def _teardown_stack(self):
        """
        Disconnects this ui (and its widgets) from the current rig. Used when
        switching to a different rig or to an empty scene. The rig itself
        is shared, so it is left working; if its scene has gone, it was already
        disposed of when the scene changed.
        """
        if not self.stack:
            return

        self.stack.detach_listeners()

    # ----------------------------------------------------------------------------------
    # Override hooks. The base implementations are intentionally no-ops;
    # subclasses may override these to surface stack events to the user
    # (status bars, toasts, viewport messages, etc.). See the maya host's
    # ``MayaAppWidget`` for an example that pipes them into
    # ``cmds.inViewMessage``.
    # ----------------------------------------------------------------------------------
    def notify_component_added(self, *args, **kwargs):
        """
        Called when a component is added to the active stack.

        Args:
            component: The Component that was added (passed as
                ``args[0]`` by ``stack.component_added``).
        """
        pass

    def notify_component_removed(self, *args, **kwargs):
        """
        Called when a component is removed from the active stack. The
        ``stack.component_removed`` signal currently passes no arguments.
        """
        pass

    def notify_build_started(self, *args, **kwargs):
        """
        Called when a stack build begins. No arguments are passed.
        """
        pass

    def notify_build_failed(self, component=None, details: str = "", *args, **kwargs):
        """
        Called when a build fails, just before notify_build_finished.

        Args:
            component: The component which failed or was invalid, or None if
                the build could not start (such as there being no
                configuration component).
            details: Why it failed. This is the traceback when the component
                raised an exception.
        """
        pass

    def notify_build_finished(self, successful: bool = True, *args, **kwargs):
        """
        Called whenever a build ends, whether it succeeded or failed.

        Args:
            successful: Whether the build succeeded
        """
        pass


class ButtonWidget(QtWidgets.QWidget):

    def __init__(self, app_widget, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app_widget = app_widget

        self.setLayout(QtWidgets.QHBoxLayout())

        self.populate()

    def populate(self):
        qtility.layouts.empty(self.layout())

        if not self.app_widget.stack:
            return
        execution_blocks = self.app_widget.stack.components(
            of_type="Stack : Execution Block")

        for execution_block in execution_blocks:
            button = QtWidgets.QPushButton(execution_block.label())
            button.clicked.connect(
                functools.partial(
                    self.app_widget.build,
                    build_below=execution_block,
                ),
            )
            self.layout().addWidget(button)

# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class AppWindow(qtility.windows.MemorableWindow):
    """
    This is the dockable window wrapper which defines the window and allows
    it to dock in maya
    """

    def __init__(self, app_config=AppConfig, allow_threading=True, *args, **kwargs):
        super().__init__(storage_identifier=f"aniseed_{qtility.windows.host()}", *args, **kwargs)

        self.app_config = app_config

        # -- Set the window properties
        self.setObjectName(self.app_config.label)
        self.setWindowTitle(self.app_config.label)

        if self.app_config.icon:
            self.setWindowIcon(
                QtGui.QIcon(
                    self.app_config.icon,
                ),
            )

        # # -- Apply our styling, defining some differences
        qtility.styling.apply(
            [
                # resources.get("space.css"),
                resources.get("style.css"),
            ],
            self,
        )

        self.setCentralWidget(
            AppWidget(
                app_config=self.app_config,
                allow_threading=allow_threading,
                parent=self,
            ),
        )


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnusedLocal
def launch(app_config=None, blocking: bool = False, parent=None, *args, **kwargs):
    """
    This function should be called to invoke the app ui in maya
    """
    # -- Check if the host needs to manage the launching of the application.
    # -- this can be required in some embedded applications because of specific
    # -- application requirements.
    host_app = host.get()
    if host_app.launch():
        return

    q_app = qtility.app.get()
    w = AppWindow(
        app_config=app_config or AppConfig,
        allow_threading=False,
        parent=parent if parent is not None else qtility.windows.application(),
        *args,
        **kwargs
    )
    w.show()

    if blocking:
        q_app.exec_()
