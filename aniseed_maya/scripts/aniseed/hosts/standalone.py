import aniseed


class StandaloneHost(aniseed.EmbeddedHost):

    priority = 0

    def launch(self):
        """
        This is responsible for launching the application within the
        current host.
        """
        return None

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
