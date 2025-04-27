import qtility
import functools
import maya.cmds as mc
from Qt import QtWidgets, QtCore, QtGui

from .. import core
from . import resources


# noinspection PyPep8Naming
class SnapList(QtWidgets.QTreeWidget):
    """
    This widget is the main interaction widget for the snapping structure. It 
    presents snap groups as top level items and snap members as children of 
    those groups.
    """
    
    def __init__(self, parent=None):
        super(SnapList, self).__init__(parent)

        # -- We update the ui based on various maya events. So we can correctly
        # -- unregister these, we store the event id's
        self.script_job_ids = list()
        
        # -- We will use these two icons a lot, so we cache them
        self._group_icon = QtGui.QIcon(
            resources.get("group.png"),
        )
        self._snap_icon = QtGui.QIcon(
            resources.get("snap.png"),
        )
        
        # -- Set the visual properties of the window
        self.setIconSize(
            QtCore.QSize(45, 45)
        )
        self.setHeaderHidden(True)
        
        # -- Populate the tree
        self.populate()

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
                        self.populate,
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

    # noinspection PyUnusedLocal
    def hideEvent(self, event):
        """
        Maya re-uses UI's, so we unregister the script job events whenever
        the ui is not visible.
        """
        self._unregister_script_jobs()

    def populate(self):
        """
        This will rebuild the tree - creating all the group elements 
        and snap members
        """
        # -- Start by clearing what is there before we add anything else
        self.clear()
        
        for group in core.groups():
            
            # -- Create an item to represent the group
            group_item = self.create_group_item(group)
            
            # -- Then create an item for each member of that group
            for snap_node in core.members(group):
                self.create_snap_item(
                    snap_node,
                    group,
                    parent_item=group_item,
                )

    def create_group_item(self, group: str) -> QtWidgets.QTreeWidgetItem:
        """
        We stamp our items with specific properties depending on what that
        item represents.
        This function stamps the item with properties specific to groups.

        Args:
            group (str): The name of the group

        Returns:
            QtWidgets.QTreeWidgetItem: The group item
        """
        # -- Create the item
        group_item = QtWidgets.QTreeWidgetItem([group])

        # -- Apply the required properties
        group_item.snap_group = group
        group_item.is_snap_group = True
        group_item.setIcon(0, self._group_icon)

        # -- Add the item and return it
        self.addTopLevelItem(group_item)
        return group_item

    def create_snap_item(
        self,
        snap_node: str,
        group: str,
        parent_item: QtWidgets.QTreeWidgetItem,
    ) -> QtWidgets.QTreeWidgetItem:
        """
        We stamp our items with specific properties depending on what that
        item represents.
        This function stamps the item with properties specific to a snap node.

        Args:
            snap_node (str): The name of the snap node
            group (str): The name of the group
            parent_item (QtWidgets.QTreeWidgetItem): The parent item

        Returns:
            QtWidgets.QTreeWidgetItem: The group item
        """

        # -- Get the node we're snapping and the target from the
        # -- snap node
        node_to_snap = core.get_node_to_snap(
            snap_node,
            group,
        )
        node_to_snap_to = core.get_node_to_snap_to(
            snap_node,
            group,
        )

        # -- Create the item
        item = QtWidgets.QTreeWidgetItem(
            [f"{node_to_snap} (Snaps To: {node_to_snap_to})"],
        )

        # -- Apply the properties to the item
        item.snap_group = group
        item.snap_node = snap_node
        item.snap_member = node_to_snap
        item.snap_target = node_to_snap_to
        item.is_snap_item = True
        item.setIcon(0, self._snap_icon)

        # -- Add the item as a child of the parent
        parent_item.addChild(item)

    def mousePressEvent(self, event):
        """
        Within this function we specifically handle the creation of the
        different context menu's
        """
        # -- Ensure we call the parent class function
        super(SnapList, self).mousePressEvent(event)

        # -- We only want to act if we're specifically a right click
        if event.button() != QtCore.Qt.RightButton:
            return

        # -- Get the item which is being clicked
        item = self.itemAt(event.pos())

        # -- Create the menu which is to be populated
        menu = QtWidgets.QMenu("", parent=self)

        # -- We now need to start testing the menu and building
        # -- the menu based on what it is
        if not item:
            self.create_new_group_menu(menu)

        elif hasattr(item, "is_snap_group"):
            self.create_group_item_menu(
                item.snap_group,
                menu,
                item,
            )

        elif hasattr(item, "is_snap_item"):
            self.create_snap_menu(
                item.snap_node,
                item.snap_group,
                menu,
                item,
            )

        # -- Finally we show the menu
        menu.popup(QtGui.QCursor().pos())

    def create_new_group_menu(self, menu: QtWidgets.QMenu):
        """
        This will populate the menu based on this being for the
        creation of new snap groups

        Args:
            menu (QtWidgets.QMenu): The menu to add actions to
        """
        action = menu.addAction(
            self._get_icon("add"),
            "Create Snap Group",
        )
        action.triggered.connect(
            functools.partial(
                self._create_new_group,
            ),
        )

    def create_group_item_menu(
        self,
        group: str,
        menu: QtWidgets.QMenu,
        item: QtWidgets.QTreeWidgetItem,
    ):
        """
        This will populate the menu based on the user selecting a group item

        Args:
            group (str): The name of the group
            menu (QtWidgets.QMenu): The menu to add actions to
            item (QtWidgets.QTreeWidgetItem): The group item being clicked
        """

        action = menu.addAction(self._get_icon("snap"), "Snap!")
        action.triggered.connect(
            functools.partial(
                self._snap_group,
                group,
                item,
            ),
        )

        action = menu.addAction(self._get_icon("add"), "Add Snap Member")
        action.triggered.connect(
            functools.partial(
                self._add_snap_member,
                group,
                item,
            ),
        )

        action = menu.addAction(self._get_icon("delete"), "Delete Snap Group")
        action.triggered.connect(
            functools.partial(
                self._delete_snap_group,
                group,
                item,
            ),
        )

    def create_snap_menu(
        self,
        snap_node: str,
        group: str,
        menu: QtWidgets.QMenu,
        item: QtWidgets.QTreeWidgetItem,
    ):
        """
        This will populate the menu based on the user selecting a snap item

        Args:
            snap_node (str): The name of the snap node
            group (str): The name of the group
            menu (QtWidgets.QMenu): The menu to add actions to
            item (QtWidgets.QTreeWidgetItem): The group item being clicked
        """
        action = menu.addAction(self._get_icon("delete"), "Remove Snap")
        action.triggered.connect(
            functools.partial(
                self._remove_snap,
                snap_node,
                group,
                item,
            ),
        )

        action = menu.addAction(self._get_icon("update"), "Update Snap Offset")
        action.triggered.connect(
            functools.partial(
                self._update_offset,
                snap_node,
                group,
                item,
            ),
        )

    def _create_new_group(self):
        """
        Called when the user wants to create a completely new group
        """

        # -- When creating a new group we need a node to snap, and a node
        # -- to snap to. If we have more or less than this amount of nodes
        # -- selected we raise an error.
        if len(mc.ls(sl=True)) != 2:
            qtility.request.message(
                title="Error",
                message="You must select a node to snap, and a node it should snap to",
                parent=self,
            )
            return

        # -- Ask for a name for the snap group. If one is not provided we
        # -- assume the user has cancelled.
        group = qtility.request.text(
            title="New Snap Group",
            parent=self,
        )
        if not group:
            return

        # -- Create a group item to represent the new group
        group_item = self.create_group_item(group)

        # -- We can now call the default add function which will perform the
        # -- adding of an item to a group.
        self._add_snap_member(group, group_item)

    def _add_snap_member(self, group, item):

        if len(mc.ls(sl=True)) != 2:
            qtility.request.message(
                title="Error",
                message="You must select a node to snap, and a node it should snap to",
                parent=self,
            )
            return

        node_to_snap = mc.ls(sl=True)[0]
        snap_target = mc.ls(sl=True)[1]

        snap_node = core.new(
            node=node_to_snap,
            target=snap_target,
            group=group,
        )

        self.create_snap_item(
            snap_node,
            group,
            item,
        )

    def _delete_snap_group(self, group, item):

        for member in core.members(group):
            core.remove(member, group)

        self.takeTopLevelItem(
            self.indexOfTopLevelItem(item),
        )

    def _snap_group(self, group, item):
        core.snap(group=group)

    def _remove_snap(self, snap_node, group, item):
        core.remove(snap_node, group)

        parent = item.parent()
        parent.removeChild(item)

        if parent.childCount() == 0:
            self.takeTopLevelItem(
                self.indexOfTopLevelItem(parent),
            )

    def _update_offset(self, snap_node, group, item):
        core.update_offset(
            core.get_node_to_snap(
                snap_node,
                group,
            ),
            core.get_node_to_snap_to(
                snap_node,
                group,
            ),
        )

    @classmethod
    def _get_icon(cls, icon_name):
        return QtGui.QIcon(
            resources.get(
                icon_name + ".png",
            ),
        )


class SnapWindow(QtWidgets.QMainWindow):
    """
    This is the main window which is visibly. In of itself it does not
    do much, but it hosts the main snap list widget
    """
    
    def __init__(self, parent=None):
        super(SnapWindow, self).__init__(parent=parent)
        
        # -- Instance the snap list and add it as the main
        # -- widget.
        self.snap_list = SnapList()
        self.setCentralWidget(self.snap_list)

        # -- Brand the window
        self.setWindowTitle("Snappy")
        self.setWindowIcon(
            QtGui.QIcon(
                resources.get("snap.png"),
            ),
        )

def launch():
    """
    This will launch the snappy application which allows the user 
    to create, modify and interact with snappy settings.
    """
    tool = SnapWindow(parent=qtility.windows.application())
    tool.show()
