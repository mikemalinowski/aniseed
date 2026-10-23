"""
Provides the "Utility : Execute Python" component, which runs arbitrary Python
code stored in its "Code" option during the build, along with the CodeEditor
widget used to edit that code. The code is executed with no sandboxing.
"""
from Qt import QtWidgets, QtCore, QtGui
import aniseed


# --------------------------------------------------------------------------------------
class PythonExecutionComponent(aniseed.RigComponent):
    """
    Executes a block of arbitrary Python code during the rig build.

    The code runs inside ``run()`` and has access to ``self`` (the
    component), ``rig`` (the active Rig, also ``self.rig``), ``aniseed`` and
    Qt's ``QtWidgets``, ``QtCore`` and ``QtGui``. Anything else must be
    imported by the code. Use with caution — there is no sandboxing.
    """

    identifier = "Utility : Execute Python"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """
        Declares the "Code" option, which holds the Python source executed
        during the build.
        """
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Code",
            description=(
                "Python source code to execute during the build. The "
                "code runs with access to ``self`` (the component) and "
                "``rig`` (the rig)."
            ),
            value="",
            group="Behaviour",
        )

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str):
        """
        Returns a CodeEditor for the "Code" option.

        Args:
            option_name: The name of the option to return a widget for.
        """
        if option_name == "Code":
            return CodeEditor()

    # ----------------------------------------------------------------------------------
    def run(self):
        """
        Executes the "Code" option with exec, in its own namespace holding
        ``self`` (this component), ``rig`` (the active Rig), ``aniseed`` and Qt's
        ``QtWidgets``, ``QtCore`` and ``QtGui``. As there is a single namespace,
        functions and comprehensions defined in the code can use any name
        defined at its top level.

        The code is compiled with this component's label as its filename, so
        tracebacks name the component. Any exception raised by the code
        propagates to the build.
        """
        namespace = {
            "__name__": "__aniseed_python__",
            "self": self,
            "rig": self.rig,
            "aniseed": aniseed,
            "QtWidgets": QtWidgets,
            "QtCore": QtCore,
            "QtGui": QtGui,
        }

        exec(
            compile(
                self.option("Code").get(),
                f"<{self.label()}>",
                "exec",
            ),
            namespace,
        )
        return True


# --------------------------------------------------------------------------------------
class CodeEditor(QtWidgets.QTextEdit):

    changed = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """
        Configures the text edit for writing Python: a monospace font, a tab
        width of four spaces, plain-text pasting only and no line wrapping. Text
        changes are re-emitted through the changed signal.
        """
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
        """
        Replaces the editor contents with the given source and emits changed.

        Args:
            value: The Python source to display.
        """
        self.document().setPlainText(value)
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def get_value(self):
        """
        Returns the editor contents as plain text.
        """
        return self.document().toPlainText()
