"""
Provides the "Rig Configuration : Standard" naming configuration, which
produces names in the form CLASSIFICATION_Description_##_LOCATION (for
example CTL_LeftArm_01_LF) and extracts each token back out of such names.
"""
import logging
import mref
import aniseed
from aniseed.config import NamingConventionError

log = logging.getLogger(__name__)


class StandardConfig(aniseed.RigConfiguration):
    """
    A naming configuration that produces names in the format

        ``[CLASSIFICATION]_[Description]_[##]_[LOCATION]``

    For example: ``CTL_LeftArm_01_LF``.

    Classification and location tokens are uppercase short codes
    defined as class attributes (``left``, ``right``, ``middle``,
    ``control``, ``joint``, etc.). The description is CamelCased on
    underscore boundaries by :meth:`generate_name`, so the final name
    always has the description in a single underscore-separated slot.
    """

    identifier = "Rig Configuration : Standard"

    # -- Locations
    left = "LF"
    right = "RT"
    middle = "MD"
    front = "FR"
    back = "BK"

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
        Generate a name in the format
        ``[CLASSIFICATION]_[Description]_[##]_[LOCATION]``.

        If ``location`` or ``classification`` matches the name of a
        class attribute (e.g. ``"left"`` or ``"control"``), the
        corresponding token is looked up on ``self``. The description
        is CamelCased on underscore boundaries, ignoring empty parts (from
        leading, trailing or doubled underscores). An empty description is
        replaced with ``Unnamed`` so the name keeps all four tokens.

        When ``unique`` is True, the counter is incremented until the
        resulting name does not exist in the current Maya scene.
        """
        if hasattr(self, location):
            location = getattr(self, location)

        if hasattr(self, classification):
            classification = getattr(self, classification)

        formatted_description = "".join(
            part[0].upper() + part[1:]
            for part in description.split("_")
            if part
        )

        if not formatted_description:
            log.warning(
                f"No description given for a {classification} name, using 'Unnamed'"
            )
            formatted_description = "Unnamed"

        while True:
            formatted_counter = str(counter).rjust(2, "0")
            name = f"{classification.upper()}_{formatted_description}_{formatted_counter}_{location.upper()}"
            if not unique or not mref.objExists(name):
                return name
            counter += 1

    def extract_location(self, name: str) -> str:
        """
        Returns the location token, which is the last underscore separated part
        of the name.

        Args:
            name: The name to extract from.
        """
        try:
            return name.split("_")[-1]
        except (IndexError, ValueError) as exc:
            raise NamingConventionError(
                f"Could not extract location from {name!r}"
            ) from exc

    def extract_classification(self, name: str) -> str:
        """
        Returns the classification token, which is the first underscore separated
        part of the name.

        Args:
            name: The name to extract from.
        """
        try:
            return name.split("_")[0]
        except (IndexError, ValueError) as exc:
            raise NamingConventionError(
                f"Could not extract classification from {name!r}"
            ) from exc

    def extract_description(self, name: str) -> str:
        """
        Returns the description token, which is the second underscore separated
        part of the name.

        Args:
            name: The name to extract from.

        Raises:
            NamingConventionError: If the name has no second part.
        """
        # -- generate_name CamelCases the description on underscore
        # -- boundaries, so the description always occupies a single
        # -- token in the produced name.
        try:
            return name.split("_")[1]
        except (IndexError, ValueError) as exc:
            raise NamingConventionError(
                f"Could not extract description from {name!r}"
            ) from exc

    def extract_counter(self, name: str) -> int:
        """
        Returns the counter, which is the second to last underscore separated
        part of the name, as an integer.

        Args:
            name: The name to extract from.

        Raises:
            NamingConventionError: If the part is missing or not an integer.
        """
        try:
            return int(name.split("_")[-2])
        except (IndexError, ValueError) as exc:
            raise NamingConventionError(
                f"Could not extract counter from {name!r}"
            ) from exc
