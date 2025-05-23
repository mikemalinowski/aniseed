import os
import aniseed


# --------------------------------------------------------------------------------------
class OrganiserComponent(aniseed.RigComponent):

    identifier = "Stack : Organiser"
    icon = os.path.join(
        os.path.dirname(__file__),
        "organiser.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(OrganiserComponent, self).__init__(*args, **kwargs)

    # ----------------------------------------------------------------------------------
    def is_valid(self):
        return True

    # ----------------------------------------------------------------------------------
    def run(self):
        return True
