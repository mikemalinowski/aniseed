import qute
import string
import functools

from . import resources



# --------------------------------------------------------------------------------------
class SettingsWidget(qute.QWidget):

    # ----------------------------------------------------------------------------------
    def __init__(self, app_config, parent=None):
        super(SettingsWidget, self).__init__(parent=parent)

        self.app_config = app_config

        self.setLayout(
            qute.QVBoxLayout(),
        )

        for setting_name, setting_value in self.app_config.all_settings().items():

            widget = qute.utilities.derive.deriveWidget(
                value=setting_value,
            )

            # -- Hook up a connection such that when this option ui changes we
            # -- reflect that change into the component
            qute.utilities.derive.connectBlind(
                widget,
                functools.partial(
                    self.store_setting_change,
                    widget,
                    setting_name,
                ),
            )
            self.layout().addLayout(
                qute.utilities.widgets.addLabel(
                    widget,
                    string.capwords(setting_name.replace('_', ' ')),
                    150,
                    slim=False,
                ),
            )

        # -- Always add in a spacer to push all the widgets up to the top
        self.layout().addSpacerItem(
            qute.QSpacerItem(
                10,
                0,
                qute.QSizePolicy.Expanding,
                qute.QSizePolicy.Expanding,
            ),
        )

    # ----------------------------------------------------------------------------------
    def store_setting_change(self, widget, option_name, *args, **kwargs):
        self.app_config.store_setting(
            option_name,
            qute.utilities.derive.deriveValue(widget),
        )


# --------------------------------------------------------------------------------------
class SettingsWindow(qute.QMainWindow):

    def __init__(self, app_config, parent=None):
        super(SettingsWindow, self).__init__(parent=parent)

        self.setWindowTitle("Aniseed Preferences")
        self.setWindowIcon(
            qute.QIcon(
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
    window = SettingsWindow(app_config, parent=qute.mainWindow())
    window.show()
