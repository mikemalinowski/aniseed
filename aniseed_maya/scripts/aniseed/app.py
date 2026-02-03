import os
import xstack
import typing
import qtility
import crosswalk
import functools
import aniseed_toolkit

from Qt import QtWidgets, QtCore, QtGui

from . import Rig
from . import host
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

    # -- Always add our own components folder to the component paths
    component_paths = [
        os.path.join(
            os.path.dirname(__file__),
            "components",
        ),
    ]

    # -- Override some of the colouring
    item_highlight_color = [100, 255, 100]

    # -- Add in settings specific to rigging.
    settings_id = "aniseed_settings"

    additional_settings = {
        "auto_generate_rig_config": True,
        "rig_config_to_generate": "Rig Configuration : Standard",
    }


# --------------------------------------------------------------------------------------
class AppWidget(xstack.app.AppWidget):
    """
    We subclass the app widget class as in the context of rigging we want to be
    able to switch rigs via the menu.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(AppWidget, self).__init__(*args, **kwargs)

        self._host = ""

        # -- Find all the rigs in the scene
        rigs = self.all_rigs()

        # -- If we have any rigs, use the first one as the active rig by default
        if rigs:
            self.switch_rig(rigs[0])

    # ----------------------------------------------------------------------------------
    def create_new_stack(self):
        """
        When a new stack is created through the ui we should check the users preferences
        on whether they want a configuration to be generated automatically.
        """
        stack = super(AppWidget, self).create_new_stack()

        # -- Attempt to add the default configuration if its a new rig
        if self.app_config.get_setting("auto_generate_rig_config"):

            stack.add_component(
                component_type=self.app_config.get_setting("rig_config_to_generate"),
                label=self.app_config.get_setting("rig_config_to_generate")
            )

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
        if not rig_host:
            try:
                rig_host = self.all_rigs()[0]
                if crosswalk.items.get_name(self._host) == crosswalk.items.get_name(rig_host):
                    # -- Last log before crash is here
                    return
            except IndexError:
                self.set_active_stack(stack=None)
                return

        rig: Rig = self.app_config.stack_class(
            host=rig_host,
            component_paths=self.app_config.component_paths,
        )

        self.set_active_stack(
            stack=rig
        )
        self._host = rig_host


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class AppWindow(QtWidgets.QMainWindow):
    """
    This is the dockable window wrapper which defines the window and allows
    it to dock in maya
    """

    OBJECT_NAME = "xstackBuilderWindow"

    def __init__(self, app_config=AppConfig, allow_threading=True, *args, **kwargs):
        super(AppWindow, self).__init__(*args, **kwargs)

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
def launch(app_config=None, blocking: bool = False, *args, **kwargs):
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
        parent=qtility.windows.application(),
        *args,
        **kwargs
    )
    w.show()

    if blocking:
        q_app.exec_()
