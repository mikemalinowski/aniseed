import os
import contextlib
import factories

from . import packages


class EmbeddedHost:
    """
    An embedded host can be used to override what happens when launching the app
    and managing how aniseed should be initialised within the application.

    The name is matched against the "hosts" listed in an aniseed package's
    marker file, to determine which packages are used within this host.
    """
    name = ""
    priority = 0

    def launch(self) -> bool:
        """
        This is responsible for launching the application within the
        current host.

        If the launch was managed by the host plugin, return True.
        """
        return False

    def environment_initialization(self):
        """
        This should hold any functionality required to be triggered when
        aniseed is registered within an application
        """
        pass

    def on_rig_save(self, rig) -> dict:
        """
        This is called when a rig is being saved
        """
        return dict()

    def on_rig_load(self, rig, file_data: dict) -> None:
        """
        Called when a rig has been loaded
        """
        return None

    @contextlib.contextmanager
    def build_context(self, rig):
        """
        Context manager that every build of a rig runs within. Re-implement it
        to wrap a build in host behaviour, such as a single undo step. By
        default it does nothing.

        Args:
            rig: The rig being built
        """
        yield

    @contextlib.contextmanager
    def without_undo(self):
        """
        Context manager for scene changes the user should not be able to undo,
        such as aniseed writing a rig's recipe to its host. By default it does
        nothing.
        """
        yield

    def control_shapes(self) -> list:
        """
        Returns the names of the control shapes available in this host, as
        offered by the shape selector widget.
        """
        return list()

    def tools(self) -> dict:
        """
        Returns the host specific tools to expose in the app's Tools menu, as
        a mapping of menu label to callable.
        """
        return dict()


class EmbeddedHosts(factories.Factory):
    """
    This stores all the host plugins. Typically only one will ever be
    valid at any given time.
    """
    _INSTANCE = None
    _HOST = None

    def __init__(self):
        super().__init__(
            abstract=EmbeddedHost,
            paths=[
                os.path.join(
                    os.path.dirname(__file__),
                    "hosts",
                ),
            ] + packages.host_paths(),
        )

    @classmethod
    def as_singleton(cls):
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    @classmethod
    def get_host(cls):
        if cls._HOST is None:
            plugins = cls.as_singleton().plugins()
            if plugins:
                plugin = min(plugins, key=lambda p: p.priority)
                cls._HOST = plugin()
        return cls._HOST


def get() -> EmbeddedHost:
    return EmbeddedHosts.as_singleton().get_host()
