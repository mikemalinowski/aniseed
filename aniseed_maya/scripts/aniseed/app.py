import xstack
import typing
import qtility
import crosswalk
import functools
import aniseed_toolkit

from Qt import QtWidgets, QtCore, QtGui

from . import Rig
from . import host
from . import config
from . import resources


# --------------------------------------------------------------------------------------
class AppConfig(xstack.app.AppConfig):
    """
    The AppConfig class allows us to tailor how the xstack app is represented. It
    gives us the oppotunity to tailor certain wording and branding to align with the
    end use cases.

    It also allolws us to define component paths as well as the stack class we
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
    def set_active_stack(self, stack: "xstack.Stack" or None):
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
        self.layout().insertWidget(2, self.buttons)
        self.layout().setStretch(0, 1)
        self.layout().setStretch(2, 0)
    #
    # ----------------------------------------------------------------------------------
    def create_new_stack(self):
        """
        When a new stack is created through the ui we should check the users preferences
        on whether they want a configuration to be generated automatically.
        """
        stack = super().create_new_stack()

        default_config = self.app_config.get_setting(
            "default_rig_config",
        )

        available_configs = [
            configuration.identifier
            for configuration in stack.component_library.plugins()
            if "Rig Configuration" in configuration.identifier and configuration.identifier != "Rig Configuration"
        ]

        configuration = qtility.request.item(
            items=available_configs,
            current=available_configs.index(default_config),
            title="Select Rig Configuration",
            message="Select a configuration to use",
            editable=False,
            parent=self,
        )

        if not configuration:
            return

        stack.add_component(
            component_type=configuration,
            label="Configuration",
        )
        self.app_config.store_setting("default_rig_config", configuration)

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

        tools_menu = QtWidgets.QMenu("Tools")

        # -- Add the aniseed toolkit
        toolkit_action = tools_menu.addAction("Toolkit")
        toolkit_action.triggered.connect(
            functools.partial(
                aniseed_toolkit.launch,
            )
        )

        # -- Return a list of additional menus that should be added
        return [
            rigs_menu,
            tools_menu,
        ]

    # ----------------------------------------------------------------------------------
    def all_rigs(self):
        """
        This will return all the rigs in the scene
        Returns:

        """
        return crosswalk.items.all_items_with_attribute(
            attribute_name="aniseed_rig",
        )

    # ----------------------------------------------------------------------------------
    def switch_rig(self, rig_host=None):
        """
        This will update the active stack to represent the rig the user
        has selected
        """
        import time
        s = time.time()
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

            # -- Compare by name string. self._host stores the name of the
            # -- previous rig host; comparing names avoids touching any
            # -- stale MObject from a now-closed scene, which is undefined
            # -- behaviour in the Maya API and crashes after a few scene
            # -- changes.
            if self._host == crosswalk.items.get_name(rig_host):
                return

        # -- Drop signal connections + host reference on the previous
        # -- stack before we replace it.
        self._teardown_stack()

        rig: Rig = self.app_config.stack_class(
            host=rig_host,
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
        self.stack.build_completed.connect(self.notify_build_finished)

        e = time.time()
        print("Time to switch rig : %s" % (e-s))

    # ----------------------------------------------------------------------------------
    def _teardown_stack(self):
        """
        Drop ``notify_*`` signals from the current stack and ask the
        stack to dispose of any host references it holds. Used when
        switching to a different rig or to an empty scene so the old
        rig's signal chain can't fire ``serialise`` on a stale Maya
        host MObject.
        """
        if not self.stack:
            return

        try:
            self.stack.component_added.disconnect(self.notify_component_added)
            self.stack.component_removed.disconnect(self.notify_component_removed)
            self.stack.build_started.disconnect(self.notify_build_started)
            self.stack.build_completed.disconnect(self.notify_build_finished)
        except Exception:
            pass

        dispose = getattr(self.stack, "dispose", None)
        if callable(dispose):
            try:
                dispose()
            except Exception:
                pass

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

    def notify_build_finished(self, *args, **kwargs):
        """
        Called when a stack build completes. No arguments are passed.
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
