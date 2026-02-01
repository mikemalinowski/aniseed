import sys
import qtility
import blackout
import webbrowser
import aniseed
import aniseed_toolkit
from Qt import QtCore, QtWidgets, QtGui

import maya
import maya.cmds as mc
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class StandaloneHost(aniseed.EmbeddedHost):

    priority = 0

    def launch(self):
        """
        This is responsible for launching the application within the
        current host.
        """
        if DockableMayaApp.instance():
            DockableMayaApp.instance().show()
            return

        DockableMayaApp.remove_workspace_control(
            DockableMayaApp.OBJECT_NAME + "WorkspaceControl"
        )

        # -- Instance the tool
        window = DockableMayaApp(
            parent=qtility.windows.application(),
        )

        # -- Ensure its correctly docked in the ui
        window.show(
            dockable=True,
            area='right',
            floating=False,
            # retain=False,
        )

        mc.workspaceControl(
            f'{window.objectName()}WorkspaceControl',
            e=True,
            ttc=["AttributeEditor", -1],
            wp="preferred",
            mw=150,
        )
        return True


    def environment_initialization(self):
        """
        This should hold any functionality required to be triggered when
        aniseed is registered within an application
        """
        MenuBuilder.build()

    def on_rig_save(self, rig) -> dict:
        """
        This is called when a rig is being saved
        """

        nodes = []

        nodes.extend(
            mc.listRelatives(
                rig.label,
                allDescendents=True
            ) or list()
        )

        supported_types = aniseed_toolkit.run(
            "Get Joint Writer Supported Types",
        )

        nodes = [
            n
            for n in nodes
            if mc.nodeType(n) in supported_types
        ]

        return dict(
            hierarchy=aniseed_toolkit.run(
                "Serialise Nodes To Dict",
                nodes=nodes,
            ),
        )

    def on_rig_load(self, rig, file_data: dict) -> None:
        """
        Called when a rig has been loaded
        """
        additional_data = file_data.get("additional_data", dict())

        if "hierarchy" in additional_data:
            aniseed_toolkit.run(
                "Deserialise Nodes From Dict",
                root_parent=rig.label,
                dataset=additional_data["hierarchy"],
            )


class MenuBuilder:

    MENU_NAME = "Aniseed"
    MENU_OBJ = "AniseedMenuRoot"

    CRITICAL_MODULES = [
        "aniseed",
        "aniseed_toolkit",
        "xstack",
        "xstack_app",
        "crosswalk",
    ]

    # noinspection PyUnresolvedReferences
    @classmethod
    def build(cls):
        """
        This will setup the menu and interface mechanisms for the Crab Rigging
        Tool.

        :return:
        """

        # -- If the menu already exists, we will delete it to allow
        # -- us to rebuild it
        if mc.menu(cls.MENU_OBJ, exists=True):
            mc.deleteUI(cls.MENU_OBJ)

        # -- Create the new menu for Crab
        new_menu = mc.menu(
            cls.MENU_OBJ,
            label=cls.MENU_NAME,
            tearOff=True,
            parent=maya.mel.eval('$temp=$gMainWindow'),
        )

        cls._add_menu_item(
            "Aniseed Builder",
            cls._launch_app,
            icon=aniseed.resources.get("icon.png"),
        )

        cls._add_menu_item(
            "Aniseed Toolkit",
            cls._launch_aniseed_toolkit,
            icon=aniseed_toolkit.resources.get("icon.png"),
        )

        mc.menuItem(divider=True, parent=new_menu)
        cls._add_menu_item(
            "Website",
            cls._menu_goto_website,
            icon=aniseed.resources.get("website.png"),
        )

        mc.menuItem(divider=True, parent=new_menu)
        cls._add_menu_item(
            "Reload",
            cls._menu_reload,
            icon=aniseed.resources.get("reload.png"),
        )

        mc.menuItem(divider=True, parent=new_menu)
        cls._add_menu_item(
            "About",
            cls._menu_show_version_data,
            icon=aniseed.resources.get("about.png"),
        )

        # -- We specifically only want this menu to be visibile
        # -- in the rigging menu
        cached_menu_set = mc.menuSet(query=True, currentMenuSet=True)
        rigging_menu_set = maya.mel.eval('findMenuSetFromLabel("Rigging")')

        # -- Set our menu to the rigging menu and add it to
        # -- the menu set
        mc.menuSet(currentMenuSet=rigging_menu_set)
        mc.menuSet(addMenu=new_menu)

        # -- Restore the users cached menu set
        mc.menuSet(currentMenuSet=cached_menu_set)


    # noinspection PyUnresolvedReferences
    @classmethod
    def _add_menu_item(cls, label, callable_func, icon=None, parent=None):
        parent = parent or cls.MENU_OBJ
        return mc.menuItem(
            cls.MENU_OBJ + label.replace(" ", "_"),
            label=label,
            command=callable_func,
            parent=parent,
            image=icon,
        )


    # noinspection PyUnresolvedReferences
    @classmethod
    def _launch_app(cls, *args, **kwargs):
        print("running launch app")
        mc.evalDeferred("import aniseed;print(aniseed.__file__);aniseed.app.launch()")


    # noinspection PyUnresolvedReferences
    @classmethod
    def _launch_aniseed_toolkit(cls, *args, **kwargs):
        mc.evalDeferred("import aniseed_toolkit;aniseed_toolkit.run('Launch Maya Toolkit')")


    # noinspection PyUnusedLocal
    @classmethod
    def _menu_goto_website(cls, *args, **kwargs):
        webbrowser.open(aniseed.constants.website)


    # noinspection PyUnresolvedReferences
    @classmethod
    def _menu_reload(cls, *args, **kwargs):


        for package in cls.CRITICAL_MODULES:
            blackout.drop(package)

        mc.evalDeferred("import aniseed;aniseed.app.launch()")

    @classmethod
    def _menu_show_version_data(cls, *args, **kwargs):

        version_data = []

        for package in cls.CRITICAL_MODULES:

            try:
                version = sys.modules.get(package).__version__
                label = f'{package} : {version}'
                version_data.append(label)

            except AttributeError:
                label = f"{package.rjust(15, ' ')} : No Version Data"

        version_data = "\n".join(version_data)

        author_data = (
            "Developed by Mike Malinowski\n"
            f"{aniseed.constants.website}\n"
        )

        qtility.request.message(
            title="About Aniseed",
            message=(
                "Aniseed Information\n\n"
                f"{version_data}\n\n"
                f"{author_data}"
            ),
        )


# noinspection PyUnresolvedReferences
class DockableMayaApp(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """
    This is the dockable window wrapper which defines the window and allows
    it to dock in maya
    """

    OBJECT_NAME = "AniseedBuilderWindow"

    def __init__(self, *args, **kwargs):
        super(DockableMayaApp, self).__init__(*args, **kwargs)

        # -- We update the ui based on various maya events. So we can correctly
        # -- unregister these, we store the event id's
        self.script_job_ids = list()

        # -- Set the window properties
        self.setObjectName(DockableMayaApp.OBJECT_NAME)
        self.setWindowTitle('Aniseed')
        self.setWindowIcon(
            QtGui.QIcon(
                aniseed.resources.get("icon.png"),
            ),
        )

        stlying_overrides = {
            "_ITEMHIGHLIGHT_": ",".join(
                [
                    str(n)
                    for n in aniseed.AppConfig.item_highlight_color
                ]
            )
        }

        qtility.styling.apply(
            [
                aniseed.resources.get("style.css"),
            ],
            apply_to=self,
            **stlying_overrides
        )

        self.app = aniseed.AppWidget(
            app_config=aniseed.AppConfig,
            allow_threading=False,
            parent=self,
        )
        self.setCentralWidget(
            self.app,
        )

        # -- Register into the maya events system
        self._register_script_jobs()

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
                        self.app.switch_rig,
                    ]
                )
            )

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

    # noinspection PyUnusedLocal
    def showEvent(self, event):
        """
        Maya re-uses UI's, so we regsiter our events whenever the ui
        is shown
        """
        self._register_script_jobs()
        self.app.switch_rig()

    # noinspection PyUnusedLocal
    def hideEvent(self, event):
        """
        Maya re-uses UI's, so we unregister the script job events whenever
        the ui is not visible.
        """
        self._unregister_script_jobs()

    @classmethod
    def instance(cls):
        import gc

        for obj in gc.get_objects():
            try:
                if isinstance(obj, DockableMayaApp):
                    return obj
            except:
                pass

    @classmethod
    def remove_workspace_control(cls, control):
        if mc.workspaceControl(control, q=True, exists=True):

            try:
                mc.workspaceControl(control, e=True, close=True)
            except:
                pass

            try:
                mc.deleteUI(control, control=True)
            except:
                pass

            return