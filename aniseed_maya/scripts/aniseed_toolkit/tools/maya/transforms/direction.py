from maya import cmds
import aniseed_toolkit


class GetDirectionClass(aniseed_toolkit.Tool):

    identifier = "Get Direction Class"
    user_facing = False
    categories = [
        "Transforms",
    ]

    def run(self, direction: str = "x") -> aniseed_toolkit.core.direction.Direction:
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
        direction_instance = aniseed_toolkit.core.direction.Direction(
            aniseed_toolkit.core.direction.Direction.Unknown,
        )
        direction_instance.set_direction(direction)
        return direction_instance


class GetUpvectorDirection(aniseed_toolkit.Tool):

    identifier = "Get Upvector Direction"
    user_facing = False
    categories = [
        "Transforms",
    ]

    def run(self, start: str = "", end: str = "", epsilon: float = 0.01) -> aniseed_toolkit.core.direction.Direction:
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
        return aniseed_toolkit.scene.joints.get_upvector_direction(
            start, end, epsilon
        )

class AimAtTool(aniseed_toolkit.Tool):

    identifier = "Aim At"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(self, aim_this="", at_this="", aim_axis="x", up_axis="y", up_target=""):

        selection_list = cmds.ls(sl=True)
        if len(selection_list) == 2:
            aim_this = selection_list[0]
            at_this = selection_list[1]
        elif len(selection_list) == 3:
            aim_this = selection_list[0]
            at_this = selection_list[1]
            up_target = selection_list[2]
        aniseed_toolkit.scene.transforms.aim_at(aim_this, at_this, aim_axis, up_axis, up_target)
