"""
The Packages window, opened from Edit > Packages in the aniseed app. It lists
every aniseed package available in this host, and lets the user turn each one
on or off. Choices are saved for the user (see packages.set_enabled), and take
effect straight away.
"""
import os
import sys
import logging
import subprocess

from Qt import QtWidgets, QtCore

from . import packages

log = logging.getLogger(__name__)

# -- The window, kept so a second request shows the same one
_WINDOW = None


# --------------------------------------------------------------------------------------
def show(app_widget=None, parent=None) -> "PackageManager":
    """
    Shows the Packages window, creating it if needed.

    Args:
        app_widget: The aniseed AppWidget to refresh when a package is turned
            on or off, so it picks up the change.
        parent: The Qt parent of the window.
    """
    global _WINDOW

    try:
        if _WINDOW is not None and _WINDOW.isVisible():
            _WINDOW.raise_()
            _WINDOW.activateWindow()
            return _WINDOW

    except RuntimeError:
        # -- Qt has already deleted the previous window
        pass

    _WINDOW = PackageManager(app_widget=app_widget, parent=parent)
    _WINDOW.show()
    return _WINDOW


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class PackageManager(QtWidgets.QDialog):
    """
    Lists the available aniseed packages, with a check box to turn each on or
    off.
    """

    COLUMNS = ["Package", "Status", "Version", "Default", "Requires", "Description"]

    # ----------------------------------------------------------------------------------
    def __init__(self, app_widget=None, parent=None):
        super().__init__(parent=parent)

        self._app_widget = app_widget

        self.setWindowTitle("Aniseed Packages")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
        self.resize(900, 400)

        self.setLayout(QtWidgets.QVBoxLayout())

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(self.COLUMNS)
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemChanged.connect(self._item_changed)
        self.tree.itemDoubleClicked.connect(self._open_folder)
        self.layout().addWidget(self.tree)

        note = QtWidgets.QLabel(
            "Turning a package off removes its components from the component library. Rigs "
            "which already use them keep all their data, but those components cannot be built "
            "until the package is turned on again. Packages which provide a host are always on. "
            "Tools from aniseed_toolkit update after a Reload. Double click a package to open its "
            "folder."
        )
        note.setWordWrap(True)
        self.layout().addWidget(note)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()

        reset_button = QtWidgets.QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset)
        buttons.addWidget(reset_button)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.close)
        buttons.addWidget(close_button)

        self.layout().addLayout(buttons)

        self.populate()

    # ----------------------------------------------------------------------------------
    def populate(self):
        """
        Fills the list from the current state of the packages.
        """
        # -- Setting the check boxes would otherwise look like the user
        # -- changing them
        self.tree.blockSignals(True)
        self.tree.clear()

        for package in sorted(packages.available(), key=lambda each: each.name):
            item = QtWidgets.QTreeWidgetItem(
                [
                    package.name,
                    self._status(package),
                    package.version or "",
                    "On" if package.enabled_by_default else "Off",
                    ", ".join(package.requires),
                    package.description,
                ],
            )

            item.setData(0, QtCore.Qt.UserRole, package.name)
            item.setToolTip(0, package.root)
            item.setToolTip(5, package.description)

            # -- Packages which provide a host are always on, so their row is
            # -- greyed out and the check box cannot be changed
            if package.can_disable():
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)

            else:
                item.setFlags(QtCore.Qt.ItemIsSelectable)
                item.setToolTip(1, "This package provides the host for this application, so it is always on")
            item.setCheckState(0, QtCore.Qt.Checked if packages.is_chosen(package) else QtCore.Qt.Unchecked)

            self.tree.addTopLevelItem(item)

        for column in range(len(self.COLUMNS) - 1):
            self.tree.resizeColumnToContents(column)

        self.tree.blockSignals(False)

    # ----------------------------------------------------------------------------------
    @staticmethod
    def _status(package) -> str:
        """
        Returns a short description of whether the package is active, and why.
        """
        if not package.can_disable():
            return "Always on (provides a host)"

        if not packages.is_chosen(package):
            return "Off"

        blocking = packages.blocking_requirements(package)
        if blocking:
            return f"Off: needs {', '.join(blocking)}"

        return "On"

    # ----------------------------------------------------------------------------------
    def _item_changed(self, item, column):
        """
        Saves the change when a check box is clicked, and applies it.
        """
        if column != 0:
            return

        name = item.data(0, QtCore.Qt.UserRole)
        enabled = item.checkState(0) == QtCore.Qt.Checked

        try:
            packages.set_enabled(name, enabled)

        except ValueError as error:
            log.warning(str(error))

        self._apply()

    # ----------------------------------------------------------------------------------
    def _reset(self):
        """
        Puts every package back to its default.
        """
        packages.reset()
        self._apply()

    # ----------------------------------------------------------------------------------
    def _apply(self):
        """
        Makes the change take effect: the component library is rebuilt from
        the active packages, and the rigs are released so they are recreated
        with it. The app is then pointed at the scene's rig again.
        """
        # -- Imported here, as rig imports a great deal of aniseed
        from .rig import Rig

        Rig.clear_factory_cache()
        Rig.clear_registry()

        if self._app_widget is not None:
            try:
                self._app_widget.switch_rig()

            except RuntimeError:
                # -- The app has been closed
                self._app_widget = None

        # -- Turning a package on may have turned on the packages it needs
        self.populate()

    # ----------------------------------------------------------------------------------
    @staticmethod
    def _open_folder(item, _column):
        """
        Opens the package's folder in the file browser.
        """
        package = packages.get(item.data(0, QtCore.Qt.UserRole))

        if package is None or not os.path.isdir(package.root):
            return

        if sys.platform == "win32":
            os.startfile(package.root)

        elif sys.platform == "darwin":
            subprocess.Popen(["open", package.root])

        else:
            subprocess.Popen(["xdg-open", package.root])
