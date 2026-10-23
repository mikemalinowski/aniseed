import os
import sys
import logging
import qtility
import blackout
import contextlib
import webbrowser
import aniseed
import aniseed_toolkit
from Qt import QtCore, QtWidgets, QtGui

import maya
from maya import cmds
from maya.api import OpenMaya as om
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

try:
    from shiboken6 import isValid
except ImportError:
    from shiboken2 import isValid

log = logging.getLogger(__name__)

# -- The ids of the scene callbacks registered by MayaHost
_SCENE_CALLBACK_IDS = list()


class MayaHost(aniseed.EmbeddedHost):

    name = "maya"
    priority = 0

    def __init__(self):
        super().__init__()
        self._register_scene_callbacks()

    @staticmethod
    def _register_scene_callbacks():
        """
        Registers the scene callbacks which keep aniseed's shared rigs in step
        with the scene: outstanding recipe changes are written before a save,
        and the rigs are released before the scene is replaced. These need to
        run before the event, which only OpenMaya's scene messages offer.
        """
        if _SCENE_CALLBACK_IDS:
            om.MMessage.removeCallbacks(_SCENE_CALLBACK_IDS)
            _SCENE_CALLBACK_IDS.clear()

        try:
            _SCENE_CALLBACK_IDS.extend(
                [
                    om.MSceneMessage.addCallback(
                        om.MSceneMessage.kBeforeSave,
                        _flush_rigs,
                    ),
                    om.MSceneMessage.addCallback(
                        om.MSceneMessage.kBeforeNew,
                        _release_rigs,
                    ),
                    om.MSceneMessage.addCallback(
                        om.MSceneMessage.kBeforeOpen,
                        _release_rigs,
                    ),
                ]
            )

        except RuntimeError:
            log.warning(
                "Could not register the aniseed scene callbacks, so rigs will not "
                "be released when the scene changes"
            )

    def launch(self):
        """
        This is responsible for launching the application within the
        current host.
        """
        control = DockableMayaApp.OBJECT_NAME + "WorkspaceControl"

        if DockableMayaApp.instance():
            DockableMayaApp.instance().show()

            # -- Bring the existing tab to the front, as showing it does
            # -- not do so if it is behind another tab
            cmds.workspaceControl(control, e=True, restore=True)
            return True

        DockableMayaApp.remove_workspace_control(control)

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

        cmds.workspaceControl(
            control,
            e=True,
            ttc=["AttributeEditor", -1],
            wp="preferred",
            mw=150,
        )

        # -- Docking as a tab does not make it the current tab, so raise it
        cmds.workspaceControl(control, e=True, restore=True)
        return True

    def environment_initialization(self):
        """
        This should hold any functionality required to be triggered when
        aniseed is registered within an application
        """
        MenuBuilder.build()

    @contextlib.contextmanager
    def build_context(self, rig):
        """
        Runs the build as a single undo step, so one undo reverts the whole build
        """
        cmds.undoInfo(openChunk=True, chunkName=f"Aniseed Build : {rig.label}")

        try:
            yield

        finally:
            cmds.undoInfo(closeChunk=True)

    @contextlib.contextmanager
    def without_undo(self):
        """
        Suspends undo recording, without flushing the undo queue, so the
        changes made within it are not undo steps
        """
        undo_enabled = cmds.undoInfo(query=True, state=True)
        cmds.undoInfo(stateWithoutFlush=False)

        try:
            yield

        finally:
            cmds.undoInfo(stateWithoutFlush=undo_enabled)

    def on_rig_save(self, rig) -> dict:
        """
        This is called when a rig is being saved
        """

        nodes = []

        nodes.extend(
            cmds.listRelatives(
                rig.label,
                allDescendents=True
            ) or list()
        )

        supported_types = aniseed_toolkit.run(
            "Get Joint Writer Supported Types",
        )

        resolved_nodes = []

        for node in nodes:
            try:
                if cmds.nodeType(node) in supported_types:
                    resolved_nodes.append(node)
            except RuntimeError: pass

        return dict(
            hierarchy=aniseed_toolkit.run(
                "Serialise Nodes To Dict",
                nodes=resolved_nodes,
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

    def control_shapes(self) -> list:
        """
        Returns the names of the aniseed_toolkit control shapes
        """
        return [
            os.path.basename(shape).split(".")[0]
            for shape in aniseed_toolkit.run("Get Shape List") or list()
        ]

    def tools(self) -> dict:
        """
        Exposes the aniseed toolkit in the app's Tools menu
        """
        return {
            "Toolkit": aniseed_toolkit.launch,
        }


class MenuBuilder:

    MENU_NAME = "Aniseed"
    MENU_OBJ = "AniseedMenuRoot"

    CRITICAL_MODULES = [
        "aniseed",
        "aniseed_toolkit",
        "xstack",
        "xstack_app",
        "crosswalk",
        "mref",
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
        if cmds.menu(cls.MENU_OBJ, exists=True):
            cmds.deleteUI(cls.MENU_OBJ)

        # -- Create the new menu for Crab
        new_menu = cmds.menu(
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

        cmds.menuItem(divider=True, parent=new_menu)
        cls._add_menu_item(
            "Website",
            cls._menu_goto_website,
            icon=aniseed.resources.get("website.png"),
        )

        cmds.menuItem(divider=True, parent=new_menu)
        cls._add_menu_item(
            "Reload",
            cls._menu_reload,
            icon=aniseed.resources.get("reload.png"),
        )

        cmds.menuItem(divider=True, parent=new_menu)
        cls._add_menu_item(
            "About",
            cls._menu_show_version_data,
            icon=aniseed.resources.get("about.png"),
        )

        # -- We specifically only want this menu to be visibile
        # -- in the rigging menu
        cached_menu_set = cmds.menuSet(query=True, currentMenuSet=True)
        rigging_menu_set = maya.mel.eval('findMenuSetFromLabel("Rigging")')

        # -- Set our menu to the rigging menu and add it to
        # -- the menu set
        cmds.menuSet(currentMenuSet=rigging_menu_set)
        cmds.menuSet(addMenu=new_menu)

        # -- Restore the users cached menu set
        cmds.menuSet(currentMenuSet=cached_menu_set)


    # noinspection PyUnresolvedReferences
    @classmethod
    def _add_menu_item(cls, label, callable_func, icon=None, parent=None):
        parent = parent or cls.MENU_OBJ
        return cmds.menuItem(
            cls.MENU_OBJ + label.replace(" ", "_"),
            label=label,
            command=callable_func,
            parent=parent,
            image=icon,
        )

    # noinspection PyUnresolvedReferences
    @classmethod
    def _launch_app(cls, *args, **kwargs):
        cmds.evalDeferred("import aniseed;aniseed.app.launch()")


    # noinspection PyUnresolvedReferences
    @classmethod
    def _launch_aniseed_toolkit(cls, *args, **kwargs):
        cmds.evalDeferred("import aniseed_toolkit;aniseed_toolkit.run('Launch Maya Toolkit')")


    # noinspection PyUnusedLocal
    @classmethod
    def _menu_goto_website(cls, *args, **kwargs):
        webbrowser.open(aniseed.constants.website)


    # noinspection PyUnresolvedReferences
    @classmethod
    def _menu_reload(cls, *args, **kwargs):
        aniseed.Rig.clear_factory_cache()

        # -- The existing rigs hold the old component classes, so release them
        # -- and let them be created afresh from the reloaded modules
        aniseed.Rig.clear_registry()

        # -- Aniseed packages (and therefore their mixins and widgets) are
        # -- dropped too, so edits to them are picked up alongside the
        # -- components
        aniseed_packages = [package.name for package in aniseed.packages.discover()]

        for package in cls.CRITICAL_MODULES + aniseed_packages:
            blackout.drop(package)

    @classmethod
    def _menu_show_version_data(cls, *args, **kwargs):

        version_data = []

        for package in cls.CRITICAL_MODULES:

            try:
                version = sys.modules.get(package).__version__
                label = f'{package} : {version}'
                version_data.append(label)

            except AttributeError:
                label = f"{package} : No Version Data"
                version_data.append(label)

        version_data.append("\nAniseed Packages")
        for package in aniseed.packages.discover():
            version_data.append(f"{package.name} : {package.version or 'No Version Data'}")

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


class MayaAppWidget(aniseed.AppWidget):
    """
    This is a maya implementation of the Aniseed App Widget. It incorporates
    on screen display of events.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = dict(pos="botCenter", fade=True)

    def notify_component_added(self, *args, **kwargs):
        message = f"{args[0].label() if args else ''} Component Added"
        cmds.inViewMessage(amg=message, **self.options)

    def notify_component_removed(self, *args, **kwargs):
        message = f"{args[0].label() if args else ''} Component Removed"
        cmds.inViewMessage(amg=message, **self.options)

    def notify_build_started(self, *args, **kwargs):
        cmds.inViewMessage(amg="Build Started", **self.options)

    def notify_build_failed(self, component=None, details="", *args, **kwargs):
        failed_at = f" : {component.label()}" if component else ""
        cmds.inViewMessage(amg=f"Build Failed{failed_at}", **self.options)

    def notify_build_finished(self, successful=True, *args, **kwargs):
        if successful:
            cmds.inViewMessage(amg="Build Finished", **self.options)


# noinspection PyUnresolvedReferences
class DockableMayaApp(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """
    This is the dockable window wrapper which defines the window and allows
    it to dock in maya
    """

    OBJECT_NAME = "AniseedBuilderWindow"

    # -- Class-level registry of every DockableMayaApp constructed in
    # -- this session. Used by ``instance()`` instead of scanning
    # -- ``gc.get_objects()`` — the gc scan grows with the number of
    # -- Python objects in the interpreter and was the dominant cost
    # -- of repeated launches.
    _INSTANCES: list = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        DockableMayaApp._INSTANCES.append(self)

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

        self.app = MayaAppWidget(
            app_config=aniseed.AppConfig,
            allow_threading=False,
            parent=self,
        )
        self.setCentralWidget(
            self.app,
        )

        # -- Script jobs are registered in ``showEvent`` only, so the
        # -- workspace control exists by the time we register and we can
        # -- bind the jobs to it via ``parent=``.

    def _register_script_jobs(self):
        """
        Registers script jobs for maya events. If the events have already
        been registered they will not be re-registered.

        Where possible, the script jobs are bound to this widget's
        workspace control via ``parent=`` so they auto-clean when the
        control is destroyed. Without that binding, jobs survive a
        widget destruction and fire ``switch_rig`` on a dead self,
        which crashes Maya.
        """
        # -- Only register if they are not already registered
        if self.script_job_ids:
            return

        parent_control = f"{self.objectName()}WorkspaceControl"
        parent_exists = cmds.workspaceControl(
            parent_control,
            q=True,
            exists=True,
        )

        events = [
            "SceneOpened",
            "NewSceneOpened",
        ]

        for event in events:
            kwargs = dict(event=[event, self.app.switch_rig])
            if parent_exists:
                kwargs["parent"] = parent_control

            self.script_job_ids.append(
                cmds.scriptJob(**kwargs)
            )

    def _unregister_script_jobs(self):
        """
        This will unregster all the events tied with this UI. It will
        then clear any registered ID's stored within the class.
        """
        for job_id in self.script_job_ids:
            cmds.scriptJob(
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
        # -- Iterate a snapshot so we can safely mutate the registry to
        # -- evict sip-deleted shells we discover along the way. Maya
        # -- can destroy the C++ side of a dockable widget during scene
        # -- open / workspace-control rebuilds while Python still holds
        # -- the wrapper; ``isValid`` filters those out.
        for inst in list(cls._INSTANCES):
            if isValid(inst):
                return inst
            cls._INSTANCES.remove(inst)
        return None

    @classmethod
    def remove_workspace_control(cls, control):
        if cmds.workspaceControl(control, q=True, exists=True):

            # -- Either step can fail if Maya has already torn the control
            # -- down part way, which is what we want anyway
            try:
                cmds.workspaceControl(control, e=True, close=True)
            except RuntimeError:
                pass

            try:
                cmds.deleteUI(control, control=True)
            except RuntimeError:
                pass

            return


def _flush_rigs(*args):
    """
    Writes any outstanding recipe changes before the scene is saved
    """
    aniseed.Rig.flush_all()


def _release_rigs(*args):
    """
    Releases the shared rigs before the scene they belong to is replaced
    """
    aniseed.Rig.clear_registry()
