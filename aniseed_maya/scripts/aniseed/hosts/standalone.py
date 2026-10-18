import aniseed


class StandaloneHost(aniseed.EmbeddedHost):

    name = "standalone"

    # -- The lowest priority value wins, so this high value makes the
    # -- standalone host a fallback used only when no application host loads
    priority = 100

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
