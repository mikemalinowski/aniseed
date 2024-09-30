import qute
import bony
import shapeshift
import aniseed_everywhere

from . import rig
from . import resources

import maya.cmds as mc
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


# --------------------------------------------------------------------------------------
class MayaAppConfig(aniseed_everywhere.app.AppConfig):
    """
    When in maya we inherit the maya rig stack
    """
    stack_class = rig.MayaRig


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class MayaAppWidget(aniseed_everywhere.app.AppWidget):
    """
    This is the main widget that brings together the tree view and the options. We are
    only subclassing this so that we can tie into the maya script jobs and update the
    ui based on application specific events.
    """

    def __init__(self, *args, **kwargs):
        super(MayaAppWidget, self).__init__(*args, **kwargs)

        # -- We update the ui based on various maya events. So we can correctly
        # -- unregister these, we store the event id's
        self.script_job_ids = list()

        # -- Register into the maya events system
        self._register_script_jobs()

    # ----------------------------------------------------------------------------------
    def additional_menus(self):
        menus = super(MayaAppWidget, self).additional_menus()

        # -- Add the bones
        bones_menu = bony.ui.menu.create()
        menus.append(bones_menu)

        # -- Add a general tools menu
        tools_menu = qute.QMenu("Tools")
        tools_menu.addMenu(shapeshift.ui.menu.create())
        menus.append(tools_menu)

        return menus

    # --------------------------------------------------------------------------
    def _register_script_jobs(self):
        """
        Registers script jobs for maya events. If the events have already
        been registered they will not be re-registered.
        """
        # -- Only register if they are not already registered
        if self.script_job_ids:
            return

        # -- Define the list of events we will register a refresh
        # -- with
        events = [
            "SceneOpened",
            "NewSceneOpened",
        ]

        for event in events:
            self.script_job_ids.append(
                mc.scriptJob(
                    event=[
                        event,
                        self.switch_rig,
                    ]
                )
            )

    # ----------------------------------------------------------------------------------
    def _unregister_script_jobs(self):
        """
        This will unregster all the events tied with this UI. It will
        then clear any registered ID's stored within the class.
        """
        for job_id in self.script_job_ids:
            mc.scriptJob(
                kill=job_id,
                force=True,
            )

        # -- Clear all our job ids
        self.script_job_ids = list()

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def showEvent(self, event):
        """
        Maya re-uses UI's, so we regsiter our events whenever the ui
        is shown
        """
        self._register_script_jobs()
        self.switch_rig()
        
    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def hideEvent(self, event):
        """
        Maya re-uses UI's, so we unregister the script job events whenever
        the ui is not visible.
        """
        self._unregister_script_jobs()


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class DockableApp(MayaQWidgetDockableMixin, qute.QMainWindow):
    """
    This is the dockable window wrapper which defines the window and allows
    it to dock in maya
    """

    OBJECT_NAME = "AniseedBuilderWindow"

    def __init__(self, *args, **kwargs):
        super(DockableApp, self).__init__(*args, **kwargs)

        # -- Set the window properties
        self.setObjectName(self.OBJECT_NAME)
        self.setWindowTitle('Aniseed')
        self.setWindowIcon(
            qute.QIcon(
                resources.get("icon.png"),
            ),
        )

        stlying_overrides = {
            "_ITEMHIGHLIGHT_": ",".join(
                [
                    str(n)
                    for n in MayaAppConfig.item_highlight_color
                ]
            )
        }

        qute.utilities.styling.apply(
            [
                aniseed_everywhere.resources.get("style.css"),
            ],
            apply_to=self,
            **stlying_overrides
        )

        self.setCentralWidget(
            MayaAppWidget(
                app_config=MayaAppConfig,
                parent=self,
            ),
        )


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnusedLocal
def launch(*args, **kwargs):
    """
    This function should be called to invoke the app ui in maya
    """
    # -- Clear out any pre-existing window
    if mc.window(DockableApp.OBJECT_NAME, exists=True):
        mc.deleteUI(DockableApp.OBJECT_NAME)
        try:
            mc.deleteUI(f"{DockableApp.OBJECT_NAME}WorkspaceControl")

        except:
            pass

    # -- Instance the tool
    window = DockableApp(
        parent=qute.utilities.windows.mainWindow(),
    )

    # -- Ensure its correctly docked in the ui
    window.show(
        dockable=True,
        area='right',
        floating=False,
    )

    mc.workspaceControl(
        f'{DockableApp.OBJECT_NAME}WorkspaceControl',
        e=True,
        ttc=["AttributeEditor", -1],
        wp="preferred",
        mw=150,
    )
