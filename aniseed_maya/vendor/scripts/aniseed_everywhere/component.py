import xstack
import webbrowser


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class RigComponent(xstack.Component):
    """
    Aniseed components should all inherit from this Rig Component. The only
    difference between a RigComponent and a xstack Component is that the rig
    is always accessible via .rig and the configuration component is always
    accessible from the .config property.
    """
    help_url = ""

    # ----------------------------------------------------------------------------------
    @property
    def rig(self) -> "aniseed_everywhere.Rig":
        """
        Returns the Rig Instance this component belongs to

        :return:
        """
        return self.stack

    # ----------------------------------------------------------------------------------
    @property
    def config(self):
        """
        Returns the configuration component that is defined in the stack

        :return:
        """
        return self.rig.config()

    # ----------------------------------------------------------------------------------
    def help(self):
        """
        The default rig config behaviour is to open a help url. But any config can
        freely re-implement this function to implement any method of help they require
        """
        if self.help_url:
            webbrowser.open(self.help_url)

    # ----------------------------------------------------------------------------------
    def suggested_label(self):

        label = self.identifier.title().split(":")[-1].strip()

        if self.option("Location") and self.config:

            location = self.option("Location").get()
            print(location)
            print(self.config.middle)
            print(location == self.config.middle)

            if location and location != self.config.middle:
                label = f"{label} {location.upper()}"

        return label
