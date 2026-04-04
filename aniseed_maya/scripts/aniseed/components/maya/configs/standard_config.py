import aniseed
from maya import cmds


class StandardConfig(aniseed.RigConfiguration):
    identifier = "Rig Configuration : Standard"

    # -- Locations
    left = "LF"
    right = "RT"
    middle = "MD"

    # -- Base Types
    organisational = "ORG"
    control = "CTL"
    joint = "JNT"
    zero = "ZRO"
    offset = "OFF"
    mechanical = "MECH"

    def generate_name(
            self,
            classification: str,
            description: str,
            location: str,
            counter: int = 1,
            unique: bool = True,
    ) -> str:
        """
        This function will generate a name based on the rules defined in the config.

        If unique is True then the counter will be incremented until a name is found
        that is unique to the scene.
        """
        if hasattr(self, location):
            location = getattr(self, location)

        if hasattr(self, classification):
            classification = getattr(self, classification)

        while True:
            formatted_counter = str(counter).rjust(2, "0")
            formatted_description = "".join(
                [
                    part[0].upper() + part[1:]
                    for part in description.split("_")
                ],
            )

            name = f"{classification.upper()}_{formatted_description}_{formatted_counter}_{location.upper()}"
            if not unique or not cmds.objExists(name):
                return name
            counter += 1

    def extract_location(self, name: str) -> str:
        return name.split("_")[-1]

    def extract_classification(self, name: str) -> str:
        return name.split("_")[0]

    def extract_description(self, name: str) -> str:
        return name.split("_")[2]

    def extract_counter(self, name: str) -> int:
        return int(name.split("_")[-2])
