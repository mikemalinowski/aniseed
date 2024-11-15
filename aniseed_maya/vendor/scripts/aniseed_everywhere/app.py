import os
import typing
import functools

import qute
from .vendor import xstack_app
from crosswalk import app

from . import Rig
from . import resources




# --------------------------------------------------------------------------------------
class AppConfig(xstack_app.AppConfig):
    """
    We use the app config class to tailor the xstack app to be specific to the
    purpose of rigging.
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
class AppWidget(xstack_app.AppWidget):
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
        rigs_menu = qute.QMenu("Rigs")

        # -- Add the action to create a new rig
        new_rig_action = rigs_menu.addAction(f"New {self.app_config.label}")
        new_rig_action.triggered.connect(
            functools.partial(
                self.create_new_stack,
            )
        )
        rigs_menu.addSeparator()

        # -- Cycle all the rigs in the scene and add them into the menu too
        rigs = app.objects.all_objects_with_attribute(
            attribute_name="aniseed_rig",
        )

        for rig_host in rigs or list():
            switch_rig_action = rigs_menu.addAction(
                app.objects.get_name(rig_host)
            )
            switch_rig_action.triggered.connect(
                functools.partial(
                    self.switch_rig,
                    rig_host,
                )
            )
        rigs_menu.addSeparator()

        # -- Return a list of additional menus that should be added
        return [
            rigs_menu,
        ]

    # ----------------------------------------------------------------------------------
    def all_rigs(self):
        """
        This will return all the rigs in the scene
        Returns:

        """
        return app.objects.all_objects_with_attribute(
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

                if app.objects.get_name(self._host) == app.objects.get_name(rig_host):
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
class AppWindow(qute.QMainWindow):
    """
    This is the dockable window wrapper which defines the window and allows
    it to dock in maya
    """

    OBJECT_NAME = "xstackBuilderWindow"

    def __init__(self, app_config=AppConfig, *args, **kwargs):
        super(AppWindow, self).__init__(*args, **kwargs)

        self.app_config = app_config

        # -- Set the window properties
        self.setObjectName(self.app_config.label)
        self.setWindowTitle(self.app_config.label)

        if self.app_config.icon:
            self.setWindowIcon(
                qute.QIcon(
                    self.app_config.icon,
                ),
            )

        # # -- Apply our styling, defining some differences
        qute.applyStyle(
            [
                'space',
                resources.get("style.css"),
            ],
            self,
        )

        self.setCentralWidget(
            AppWidget(
                app_config=self.app_config,
                parent=self,
            ),
        )


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnusedLocal
def launch(app_config=None, blocking: bool = False, *args, **kwargs):
    """
    This function should be called to invoke the app ui in maya
    """

    q_app = qute.qApp()

    w = AppWindow(
        app_config=app_config or AppConfig,
        parent=qute.mainWindow(),
        *args,
        **kwargs
    )
    w.show()

    if blocking:
        q_app.exec_()
