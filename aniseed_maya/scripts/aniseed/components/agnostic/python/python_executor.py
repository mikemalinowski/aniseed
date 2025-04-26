from Qt import QtWidgets, QtCore, QtGui
import aniseed


# --------------------------------------------------------------------------------------
class PythonExecutionComponent(aniseed.RigComponent):

    identifier = "Utility : Execute Python"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(PythonExecutionComponent, self).__init__(*args, **kwargs)

        self.declare_option(
            name="Code",
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


# --------------------------------------------------------------------------------------
class CodeEditor(QtWidgets.QTextEdit):

    changed = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(CodeEditor, self).__init__(*args, **kwargs)

        self.textChanged.connect(self.changed.emit)
        
    # ----------------------------------------------------------------------------------
    def set_value(self, value):
        self.document().setPlainText(value)
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def get_value(self):
        return self.document().toPlainText()
