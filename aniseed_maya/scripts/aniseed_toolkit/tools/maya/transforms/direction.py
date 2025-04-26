import aniseed_toolkit
import maya.cmds as mc


class Direction:

    PositiveX = 0
    PositiveY = 1
    PositiveZ = 2

    NegativeX = 3
    NegativeY = 4
    NegativeZ = 6

    Unknown = 7
    
    def __init__(self, idx):
        self.idx = idx
    
    def __eq__(self, other):
        if isinstance(other, Direction):
            return self.idx == other.idx
        
        if isinstance(other, int):
            return self.idx == other
        return False
    
    def set_direction(self, direction):
        if isinstance(direction, int):
            self.idx = direction
            return

        if isinstance(direction, str) and len(direction) > 1:
            if "negative" in direction.lower():
                self.idx = {"x":3, "y":4, "z":5}[direction.lower()]
                return

        if isinstance(direction, str):
            self.idx = {"x":0, "y":1, "z":2}[direction.lower()]
            return
        
    @property
    def full_string(self):
        direction = self.idx
        if direction == self.PositiveX: return "Positive X"
        if direction == self.NegativeX: return "Negative X"
        if direction == self.PositiveY: return "Positive Y"
        if direction == self.NegativeY: return "Negative Y"
        if direction == self.PositiveZ: return "Positive Z"
        if direction == self.NegativeZ: return "Negative Z"
    
        return "Unknown"
        
    @property
    def axis(self):
        if self.idx == self.Unknown:
            return None
        
        return self.full_string[-1].lower()
    
    @property
    def direction_multiplier(self):
        if "Negative" in self.full_string:
            return -1
        return 1
    
    @property
    def ik_solve_attribute_index(self):
        
        direction = self.idx
        
        if direction == self.PositiveX:
            return 0

        elif direction == self.NegativeX:
            return 1

        elif direction == self.PositiveY:
            return 2

        elif direction == self.NegativeY:
            return 3

        elif direction == self.PositiveZ:
            return 4

        return 5
    
    @property
    def cross_axis(self):
        axis = self.axis
        if axis == "x":
            return "y"
    
        if axis == "y":
            return "z"
    
        return "x"
    
    @property
    def axis_vector(self):
        axis = self.axis
        
        if axis == "x":
            return [1, 0, 0]
    
        elif axis == "y":
            return [0, 1, 0]
    
        else:
            return [0, 0, 1]
    
    @property
    def direction_vector(self):
        direction = self.idx
        if direction == self.PositiveX: return [1, 0, 0]
        if direction == self.NegativeX: return [-1, 0, 0]
    
        if direction == self.PositiveY: return [0, 1, 0]
        if direction == self.NegativeY: return [0, -1, 0]
    
        if direction == self.PositiveZ: return [0, 0, 1]
        if direction == self.NegativeZ: return [0, 0, -1]


class GetDirectionClass(aniseed_toolkit.Tool):

    identifier = "Get Direction Class"
    user_facing = False
    categories = [
        "Transforms",
    ]

    def run(self, direction: str = "x") -> Direction:
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
        return Direction(direction)


class GetChainFacingDirection(aniseed_toolkit.Tool):

    identifier = "Get Chain Facing Direction"
    user_facing = False
    categories = [
        "Transforms",
    ]
    
    def run(self, start: str = "", end: str = "", epsilon: float = 0.01) -> Direction:
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
        axis = dict(
            x=0,
            y=0,
            z=0,
        )
    
        for joint in aniseed_toolkit.run("Get Joints Between", start, end)[1:]:
            for channel in axis:
                axis[channel] += mc.getAttr(
                    f"{joint}.translate{channel.upper()}",
                )
    
        has_x = abs(axis["x"]) > epsilon
        has_y = abs(axis["y"]) > epsilon
        has_z = abs(axis["z"]) > epsilon
    
        if sum([int(has_x), int(has_y), int(has_z)]) > 1:
            return Direction(Direction.Unknown)
    
        if has_x and axis["x"] > 0:
            return Direction(Direction.PositiveX)
    
        if has_x and axis["x"] < 0:
            return Direction(Direction.NegativeX)
    
        if has_y and axis["y"] > 0:
            return Direction(Direction.PositiveY)
    
        if has_y and axis["y"] < 0:
            return Direction(Direction.NegativeY)
    
        if has_z and axis["z"] > 0:
            return Direction(Direction.PositiveZ)
    
        if has_z and axis["z"] < 0:
            return  Direction(Direction.NegativeZ)
    
        return Direction(Direction.Unknown)


class GetUpvectorDirection(aniseed_toolkit.Tool):

    identifer = "Get Upvector Direction"
    user_facing = False
    categories = [
        "Transforms",
    ]

    def run(self, start: str = "", end: str = "", epsilon: float = 0.01) -> Direction:
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
        all_joints = aniseed_toolkit.run(
            "Get Joints Between",
            start,
            end,
        )

        temp_a = mc.createNode("transform")
        temp_b = mc.createNode("transform")

        facing_direction = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            start,
            end,
            epsilon,
        )

        mc.parent(temp_b, temp_a)

        mc.xform(
            temp_a,
            matrix=mc.xform(
                all_joints[0],
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        mc.xform(
            temp_b,
            matrix=mc.xform(
                all_joints[1],
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        highest_rotation_value = 0
        recorded_value = 0
        rotate_axis = "X"

        for idx, axis in enumerate(["X", "Y", "Z"]):
            value = mc.getAttr(f"{temp_b}.rotate{axis}")
            if abs(value) > highest_rotation_value:
                rotate_axis = axis
                highest_rotation_value = abs(value)
                recorded_value = value

        mc.delete(temp_a)

        if facing_direction == Direction.PositiveX and rotate_axis == "Z":
            if recorded_value >= 0:
                return Direction(Direction.NegativeY)
            return Direction(Direction.PositiveY)

        if facing_direction == Direction.NegativeX and rotate_axis == "Z":
            if recorded_value >= 0:
                return Direction(Direction.PositiveY)
            return Direction(Direction.NegativeY)

        if facing_direction == Direction.PositiveX and rotate_axis == "Y":
            if recorded_value >= 0:
                return Direction(Direction.PositiveZ)
            return Direction(Direction.NegativeZ)

        if facing_direction == Direction.NegativeX and rotate_axis == "Y":
            if recorded_value >= 0:
                return Direction(Direction.NegativeZ)
            return Direction(Direction.PositiveZ)

        if facing_direction == Direction.PositiveY and rotate_axis == "Z":
            if recorded_value >= 0:
                return Direction(Direction.PositiveX)
            return Direction(Direction.NegativeX)

        if facing_direction == Direction.NegativeY and rotate_axis == "Z":
            if recorded_value >= 0:
                return Direction(Direction.NegativeX)
            return Direction(Direction.PositiveX)

        if facing_direction == Direction.PositiveY and rotate_axis == "X":
            if recorded_value >= 0:
                return Direction(Direction.NegativeZ)
            return Direction(Direction.PositiveZ)

        if facing_direction == Direction.NegativeY and rotate_axis == "X":
            if recorded_value >= 0:
                return Direction(Direction.PositiveZ)
            return Direction(Direction.NegativeZ)

        if facing_direction == Direction.PositiveZ and rotate_axis == "Y":
            if recorded_value >= 0:
                return Direction(Direction.NegativeX)
            return Direction(Direction.PositiveX)

        if facing_direction == Direction.NegativeZ and rotate_axis == "Y":
            if recorded_value >= 0:
                return Direction(Direction.PositiveX)
            return Direction(Direction.NegativeX)

        if facing_direction == Direction.PositiveZ and rotate_axis == "X":
            if recorded_value >= 0:
                return Direction(Direction.PositiveY)
            return Direction(Direction.NegativeY)

        if facing_direction == Direction.NegativeZ and rotate_axis == "X":
            if recorded_value >= 0:
                return Direction(Direction.NegativeY)
            return Direction(Direction.PositiveY)

        return Direction(Direction.Unknown)
