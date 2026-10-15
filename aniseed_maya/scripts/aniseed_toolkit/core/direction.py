"""
The Direction class, which describes an axis and its direction (such as
Positive X) and exposes it in different forms - strings, vectors and indices.
"""
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
            # -- Strings such as "Negative X" (or "-x")
            axis = direction.lower()[-1]
            if "negative" in direction.lower() or direction.startswith("-"):
                self.idx = {"x": self.NegativeX, "y": self.NegativeY, "z": self.NegativeZ}[axis]
                return

            # -- Strings such as "Positive X"
            self.idx = {"x": self.PositiveX, "y": self.PositiveY, "z": self.PositiveZ}[axis]
            return

        if isinstance(direction, str):
            self.idx = {"x": self.PositiveX, "y": self.PositiveY, "z": self.PositiveZ}[direction.lower()]
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

    @classmethod
    def from_string(cls, string_axis):
        string_axis = string_axis.lower()

        for axis in ["x", "y", "z"]:
            if string_axis == axis:
                return cls(getattr(cls, f"Positive{axis.upper()}"))

            if string_axis.startswith("-") and string_axis.endswith(axis):
                return cls(getattr(cls, f"Negative{axis.upper()}"))

        return None
