import aniseed_toolkit


class GetDirectionClass(aniseed_toolkit.Tool):

    identifier = "Get Direction Class"
    user_facing = False
    categories = [
        "Transforms",
    ]

    def run(self, direction: str = "x") -> aniseed_toolkit.direction.Direction:
        """
        This will return a Direction instance for the given direction.

        The Direction instance is a class which provides easy access to directional
        data in different formats such as:
            axis: x, y, z
            full_string: Positive X, Negative X
            axis_vector: [1, 0, 0]
            direction_vector: [-1, 0, 0]
            cross_axis: x, y, z (the axis that crosses this one)

        Args:
            direction: The direction string (x, y, z) to instance a direction class
                with

        Return
            Direction class
        """
        return aniseed_toolkit.direction.Direction(direction)


class GetChainFacingDirection(aniseed_toolkit.Tool):

    identifier = "Get Chain Facing Direction"
    user_facing = False
    categories = [
        "Transforms",
    ]
    
    def run(self, start: str = "", end: str = "", epsilon: float = 0.01) -> aniseed_toolkit.direction.Direction:
        """
        This will return a Direction class which represents the facing direction
        of a chain. The facing direction is the direction ALL bones are using
        down-the-bone.

        The Direction instance is a class which provides easy access to directional
        data in different formats such as:
            axis: x, y, z
            full_string: Positive X, Negative X
            axis_vector: [1, 0, 0]
            direction_vector: [-1, 0, 0]
            cross_axis: x, y, z (the axis that crosses this one)

        Args:
            start: The first bone in the chain
            end: The last bone in the chain
            epsilon: How much variance in axis change we will tolerate

        Returns:
            Direction instance
        """
        return aniseed_toolkit.direction.get_chain_facing_direction(
            start, end, epsilon
        )


class GetUpvectorDirection(aniseed_toolkit.Tool):

    identifer = "Get Upvector Direction"
    user_facing = False
    categories = [
        "Transforms",
    ]

    def run(self, start: str = "", end: str = "", epsilon: float = 0.01) -> aniseed_toolkit.direction.Direction:
        """
        This will attempt to return a Direction instance which represents the
        upvector direction of the chain between the start and end joint.

        The Direction instance is a class which provides easy access to directional
        data in different formats such as:
            axis: x, y, z
            full_string: Positive X, Negative X
            axis_vector: [1, 0, 0]
            direction_vector: [-1, 0, 0]
            cross_axis: x, y, z (the axis that crosses this one)

        Args:
            start: The first bone in the chain
            end: The last bone in the chain
            epsilon: How much variance in axis change we will tolerate

        Returns:
            Direction instance
        """
        return aniseed_toolkit.direction.get_upvector_direction(
            start, end, epsilon
        )
