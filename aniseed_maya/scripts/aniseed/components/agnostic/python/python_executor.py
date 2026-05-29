from Qt import QtWidgets, QtCore, QtGui
import aniseed


# --------------------------------------------------------------------------------------
class PythonExecutionComponent(aniseed.RigComponent):
    """
    Executes a block of arbitrary Python code during the rig build.

    The code runs inside ``run()`` and has access to ``self`` (the
    component), ``self.rig`` (the active Rig), and any modules
    imported by the calling environment. Use with caution — there is
    no sandboxing.
    """

    identifier = "Utility : Execute Python"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Code",
            description=(
                "Python source code to execute during the build. The "
                "code runs with access to ``self`` (the component) and "
                "``self.rig``."
            ),
            value="",
            group="Behaviour",
        )

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):
        if option_name == "Code":
            return CodeEditor()

    # ----------------------------------------------------------------------------------
    def run(self):
        exec(
            self.option("Code").get(),
        )
        return True


# --------------------------------------------------------------------------------------
class CodeEditor(QtWidgets.QTextEdit):

    changed = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # -- Editor styling: monospace font, real tab width, no
        # -- rich-text paste, no soft-wrap. Makes the widget actually
        # -- usable for writing Python.
        font = QtGui.QFont("Consolas")
        font.setStyleHint(QtGui.QFont.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)

        metrics = QtGui.QFontMetrics(font)
        self.setTabStopDistance(4 * metrics.horizontalAdvance(" "))
        self.setAcceptRichText(False)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        self.textChanged.connect(self.changed.emit)

    # ----------------------------------------------------------------------------------
    def set_value(self, value):
        self.document().setPlainText(value)
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def get_value(self):
        return self.document().toPlainText()
