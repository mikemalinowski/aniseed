import mref
from maya import cmds
from maya.api import OpenMaya as om


class NurbsCurve(mref.Trait):

    spaces = mref.constants.spaces

    def __init__(self, *args, **kwargs):
        super(NurbsCurve, self).__init__(*args, **kwargs)
        self._curve = om.MFnNurbsCurve(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kNurbsCurve):
            return True
        return False

    def skin(self) -> mref.ReferencedItem|None:
        """
        This will return a ReferencedItem for the SkinCluster if one is bound
        to this curve.
        """
        try:
            return self.item.inputs(type="skinCluster")[0]
        except IndexError:
            return None

    def cv_count(self) -> int:
        """
        Returns the total count of cv's making up the curve
        """
        return self._curve.numCVs

    def knot_count(self) -> int:
        """
        Returns the total count of knots making up the curve
        """
        return self._curve.numKnots

    def span_count(self) -> int:
        """
        Returns the total count of spans making up the curve
        """
        return self._curve.numSpans

    def component_count(self) -> int:
        """
        Returns the total count of cv's making up the curve
        """
        return self.cv_count()

    def component_path(self, component_index: int) -> str:
        """
        This will return the fully qualified path of the component id
        """
        return f"{self.item.full_name()}.cv[{component_index}]"

    def cv_positions(self, space: str = "object") -> list[list[float]]:
        """
        This returns a list containing a list of three components correlating to
        the x, y, z positions of the cv's.
        """
        return [
            list(self._curve.cvPosition(i, self.spaces[space]))
            for i in range(self.cv_count())
        ]

    def set_cv_positions(self, positions: list[list[float]], space: str = "object"):
        """
        This takes in a positions list, in the format:

        [
            [x, y, z],
            [x, y, z],
            [x, y, z],
            [x, y, z],
            ...
        ]

        Where each triplet list defines the position of the vertex id in the
        list order.
        """
        if len(positions) != self.cv_count():
            raise ValueError(f"Number of CVs ({self.cv_count()}) does not match length of cv_positions ({len(positions)})")

        for i, position in enumerate(positions):
            self._curve.setCVPosition(i, om.MPoint(position[0], position[1], position[2]), self.spaces[space])
        self._curve.updateCurve()

    def cv_position(self, cv_index: int, space: str = "object") -> list[float]:
        """
        This returns a list containing the three components correlating to
        the x, y, z positions of the cv.
        """
        point = self._curve.cvPosition(cv_index, self.spaces[space])
        return [point.x, point.y, point.z]


    def set_cv_position(self, cv_index: int, position: list[float], space: str = "object"):
        """
        This takes in a position list, in the format:

            [x, y, z]

        The vertex with the given id will then have its position set to those values.
        """
        self._curve.setCVPosition(cv_index, om.MPoint(position[0], position[1], position[2]), self.spaces[space])
        self._curve.updateCurve()