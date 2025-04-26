from . import host


def initialize():
    """
    This should be called when aniseed is registered in an application, as it
    gives chance for the the application implementation to bind into the app.
    """
    host_app = host.get()
    host_app.environment_initialization()
