import os
import uuid
import aniseed_toolkit

from importlib.machinery import SourceFileLoader
from . import host


def _evaluate_module(filepath):
    filename = os.path.basename(filepath)
    module_name = filename + str(uuid.uuid4())
    return SourceFileLoader(
        module_name,
        filepath,
    ).load_module()



def initialize():
    """
    This should be called when aniseed is registered in an application, as it
    gives chance for the the application implementation to bind into the app.
    """
    host_app = host.get()
    host_app.environment_initialization()

    # -- Register any aniseed tools
    components_root = os.path.join(
        os.path.dirname(__file__),
        "components",
    )
    print("runningi intia")
    for root, _, files in os.walk(components_root):
        for filename in files:
            if filename.lower() == "toolkit_plugin.py":
                _evaluate_module(
                    os.path.join(
                        root,
                        filename,
                    ),
                )
                print("Loaded Toolkit Plugin : %s" % filename)
