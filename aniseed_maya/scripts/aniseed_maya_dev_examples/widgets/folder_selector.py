"""
Provides FolderSelector, a line edit with a browse button for choosing a
folder. It is used by the publishing examples in components/08_publish.

aniseed.widgets.FilepathSelector is built for choosing an fbx file to save
to, so this widget exists for options which need a folder instead.
"""
from Qt import QtWidgets, QtCore


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class FolderSelector(QtWidgets.QWidget):
    """
    A line edit holding a folder path, with a button that opens a folder
    browser.
    """

    # -- See slider_spin_box.py for why every option widget needs this
    changed = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, title="Choose Folder", parent=None):
        """
        Args:
            title: The title of the folder browser.
            parent: The Qt parent of the widget.
        """
        super().__init__(parent=parent)

        self._title = title

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.line_edit = QtWidgets.QLineEdit()
        self.layout().addWidget(self.line_edit)

        self.browse_button = QtWidgets.QPushButton("...")
        self.browse_button.setFixedWidth(30)
        self.layout().addWidget(self.browse_button)

        # -- Typing a path by hand is just as valid as browsing for one.
        # -- textChanged passes the new text, but changed takes no arguments,
        # -- so it cannot be connected to changed.emit directly.
        self.line_edit.textChanged.connect(self._text_changed)
        self.browse_button.clicked.connect(self._browse)

    # ----------------------------------------------------------------------------------
    def get_value(self) -> str:
        """
        Returns the folder path.
        """
        return self.line_edit.text()

    # ----------------------------------------------------------------------------------
    def set_value(self, value) -> None:
        """
        Shows the given folder path.

        Args:
            value: The folder path to show.
        """
        # -- setText emits textChanged, which emits changed
        self.line_edit.setText(value or "")

    # ----------------------------------------------------------------------------------
    def _text_changed(self, _text: str) -> None:
        """
        Emits changed whenever the text changes.
        """
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def _browse(self) -> None:
        """
        Opens a folder browser, starting at the current folder, and shows the
        chosen folder. Cancelling leaves the value as it was.
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self._title,
            self.get_value(),
        )

        if folder:
            self.set_value(folder)
