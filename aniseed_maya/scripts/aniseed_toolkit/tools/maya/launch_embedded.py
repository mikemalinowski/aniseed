import qtility
import aniseed_toolkit
from aniseed_toolkit.ui.app import ToolWidget
from maya import cmds
from Qt import QtCore, QtWidgets, QtGui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

try:
    from shiboken6 import isValid
except ImportError:
    from shiboken2 import isValid


class LaunchMayaToolkit(aniseed_toolkit.Tool):
    
    identifier = 'Launch Maya Toolkit'
    classification = "Rigging"
    user_facing = False
    
    def run(self):

        if DockableAniseedToolkit.instance():
            DockableAniseedToolkit.instance().show()

            # -- Bring the existing tab to the front, as showing it does
            # -- not do so if it is behind another tab
            cmds.workspaceControl(
                DockableAniseedToolkit.OBJECT_NAME + "WorkspaceControl",
                e=True,
                restore=True,
            )
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

        cmds.workspaceControl(
            f'{window.objectName()}WorkspaceControl',
            e=True,
            ttc=["AttributeEditor", -1],
            wp="preferred",
            mw=150,
        )
        return True


# noinspection PyUnresolvedReferences
class DockableAniseedToolkit(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """
    The dockable window which hosts the aniseed toolkit in Maya.
    """
    OBJECT_NAME = "AniseedToolkit"

    # -- Every DockableAniseedToolkit made this session. instance() reads
    # -- this rather than scanning gc.get_objects(), which is slow and can
    # -- return a wrapper whose Qt widget Maya has already deleted
    _INSTANCES: list = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        DockableAniseedToolkit._INSTANCES.append(self)

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
        if cmds.workspaceControl(control, q=True, exists=True):

            # -- Either step can fail if Maya has already torn the control
            # -- down, which leaves nothing to remove
            try:
                cmds.workspaceControl(control, e=True, close=True)
            except RuntimeError:
                pass

            try:
                cmds.deleteUI(control, control=True)
            except RuntimeError:
                pass

            return

    @classmethod
    def instance(cls):
        """
        Returns the live toolkit window, or None if there is none.

        Maya can delete the Qt side of a dockable widget (scene open,
        workspace control rebuilds) while Python still holds the wrapper.
        Showing such a wrapper crashes Maya, so dead entries are dropped
        rather than returned.

        Returns:
            The DockableAniseedToolkit instance, or None.
        """
        # -- Iterate a copy so dead entries can be removed along the way
        for inst in list(cls._INSTANCES):
            if isValid(inst):
                return inst
            cls._INSTANCES.remove(inst)
        return None
