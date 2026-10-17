import typing

import aniseed_toolkit

if typing.TYPE_CHECKING:
    import aniseed

# -- The builder lives in the rigging layer. The name is kept here so that
# -- anything which referenced it from this module still finds it.
TwistSetup = aniseed_toolkit.rigging.twist.TwistSetup


class CreateTwist(aniseed_toolkit.Tool):

    identifier = "Create Twist Setup"
    classification = "Rigging"
    user_facing = True

    categories = [
        "Rigging",
    ]

    def run(
        self,
        twist_count: int = 3,
        description: str = "",
        location: str = "",
        config: "aniseed.RigConfiguration" = None,
    ) -> "TwistSetup":
        """
        This will create a twister setup - this provides two end points which
        can be accessed via twistSetup.root() and twistSetup.tip(). You can also
        access the root org of the twist setup using twistSetup.org()

        All controls can be accessed via twistSetup.all_controls()

        Args:
            twist_count (int): The number of twists to create
            description (str): The description of the twist - this will be used in
                all the node names
            location: The location tag for the nodes
            config: The aniseed.RigConfiguration instance

        Returns:
            The TwistSetup instance
        """
        return aniseed_toolkit.rigging.twist.create_twist_setup(
            twist_count=twist_count,
            description=description,
            location=location,
            config=config,
        )
