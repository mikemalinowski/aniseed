import string
import functools
import qtility
from Qt import QtWidgets, QtGui

from . import resources



# --------------------------------------------------------------------------------------
class SettingsWidget(QtWidgets.QWidget):

    # ----------------------------------------------------------------------------------
    def __init__(self, app_config, parent=None):
        super(SettingsWidget, self).__init__(parent=parent)

        self.app_config = app_config

        self.setLayout(
            QtWidgets.QVBoxLayout(),
        )

        for setting_name, setting_value in self.app_config.all_settings().items():

            widget = qtility.derive.qwidget(
                value=setting_value,
            )

            # -- Hook up a connection such that when this option ui changes we
            # -- reflect that change into the component
            qtility.derive.connect(
                widget,
                functools.partial(
                    self.store_setting_change,
                    widget,
                    setting_name,
                ),
            )
            self.layout().addLayout(
                qtility.widgets.addLabel(
                    widget,
                    string.capwords(setting_name.replace('_', ' ')),
                    150,
                    slim=False,
                ),
            )

        # -- Always add in a spacer to push all the widgets up to the top
        self.layout().addSpacerItem(
            QtWidgets.QSpacerItem(
                10,
                0,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            ),
        )

    # ----------------------------------------------------------------------------------
    def store_setting_change(self, widget, option_name, *args, **kwargs):
        self.app_config.store_setting(
            option_name,
            qtility.derive.value(widget),
        )


# --------------------------------------------------------------------------------------
class SettingsWindow(QtWidgets.QMainWindow):

    def __init__(self, app_config, parent=None):
        super(SettingsWindow, self).__init__(parent=parent)

        self.setWindowTitle("Aniseed Preferences")
        self.setWindowIcon(
            QtGui.QIcon(
                resources.get("icon.png")
            )
        )
        self.setCentralWidget(
            SettingsWidget(
                app_config=app_config,
                parent=parent,
            ),
        )


# --------------------------------------------------------------------------------------
def show_settings(app_config):
    window = SettingsWindow(app_config, parent=qtility.windows.application())
    window.show()
