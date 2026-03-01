import os
import factories


class EmbeddedHost:
    """
    An embedded host can be used to override what happens when launching the app
    and managing how aniseed should be initialised within the application.
    """
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


class EmbeddedHosts(factories.Factory):
    """
    This stores all the host plugins. Typically only one will ever be
    valid at any given time.
    """
    _INSTANCE = None
    _HOST = None

    def __init__(self):
        super(EmbeddedHosts, self).__init__(
            abstract=EmbeddedHost,
            paths=[
                os.path.join(
                    os.path.dirname(__file__),
                    "hosts",
                ),
            ],
        )

    @classmethod
    def as_singleton(cls):
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    @classmethod
    def get_host(cls):
        if cls._HOST is None:
            for plugin in sorted(cls.as_singleton().plugins(), key=lambda p: p.priority):
                cls._HOST = plugin()
                break
        return cls._HOST


def get() -> EmbeddedHost:
    return EmbeddedHosts().as_singleton().get_host()
