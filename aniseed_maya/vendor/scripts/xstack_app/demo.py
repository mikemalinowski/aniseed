import os
import qtility
import xstack

from Qt import QtWidgets

from .config import AppConfig
from .application import AppWindow


# --------------------------------------------------------------------------------------
class DemoAppConfig(AppConfig):

    label = "Stack Demo"

    component_paths = [
        os.path.join(
            os.path.dirname(xstack.__file__),
            "test",
        )
    ]

    stack_class = xstack.Stack

# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnusedLocal
def launch_demo(blocking: bool = True):
    """
    This function should be called to invoke the app ui in demonstration
    mode, which exposes all the components used by xstacks unit tests.
    """
    q_app = qtility.app.get()

    w = AppWindow(app_config=DemoAppConfig)
    w.show()

    if blocking:
        q_app.exec_()
