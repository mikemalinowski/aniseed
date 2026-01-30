import qtility
import aniseed_toolkit
from aniseed_toolkit.app.widgets import ToolWidget
import maya.cmds as mc
from Qt import QtCore, QtWidgets, QtGui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class LaunchMayaToolkit(aniseed_toolkit.Tool):
    
    identifier = 'Launch Maya Toolkit'
    classification = "Rigging"
    user_facing = False
    
    def run(self):

        if DockableAniseedToolkit.instance():
            DockableAniseedToolkit.instance().show()
            return

        DockableAniseedToolkit.remove_workspace_control(
            DockableAniseedToolkit.OBJECT_NAME + "WorkspaceControl"
        )

        # -- Instance the tool
        window = DockableAniseedToolkit(
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


# noinspection PyUnresolvedReferences
class DockableAniseedToolkit(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    OBJECT_NAME = "AniseedToolkit"
    
    def __init__(self, *args, **kwargs):
        super(DockableAniseedToolkit, self).__init__(*args, **kwargs)

        self.setObjectName(DockableAniseedToolkit.OBJECT_NAME)
        self.setWindowTitle('AniseedToolkit')
        self.setWindowIcon(
            QtGui.QIcon(
                aniseed_toolkit.resources.get("icon.png"),
            ),
        )

        self.setCentralWidget(
            ToolWidget(),
        )
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

    @classmethod
    def instance(cls):
        import gc

        for obj in gc.get_objects():
            if isinstance(obj, DockableAniseedToolkit):
                return obj
