import mref
from maya import cmds
from maya.api import OpenMaya as om


class NurbsCurve(mref.Trait):
    """
    Trait bound to any node with ``MFn.kNurbsCurve`` — nurbs curve
    shape nodes. Provides CV position queries (single and bulk),
    counts of CVs / knots / spans, skin cluster discovery, and the
    skinnable-shape protocol used by ``SkinCluster`` to read and
    write weights.

    Unlike ``Transform``, this trait supports the full set of Maya
    transformation spaces (``"object"``, ``"world"``, ``"local"``,
    ``"pretransform"``, ``"posttransform"``, ``"last"``) via the
    underlying ``MFnNurbsCurve`` API — see :meth:`cv_positions` and
    the other space-aware methods.
    """

    # -- Map of space-name strings to MSpace enums. Exposed as a class
    # -- attribute so callers can enumerate supported space names if
    # -- they need to (e.g. for UI dropdowns).
    spaces = mref.constants.spaces

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._curve = om.MFnNurbsCurve(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kNurbsCurve)

    def skin(self) -> mref.ReferencedItem|None:
        """
        Returns a ReferencedItem for the SkinCluster bound to this
        curve, or None if no skin cluster is connected.
        """
        skins = self.item.inputs(type="skinCluster")
        if skins:
            return skins[0]
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
        Returns the number of CVs in the curve.

        Part of the skinnable-shape protocol consumed by
        :class:`SkinCluster`: ``component_count()`` is the number of
        weights that need to be supplied per influence.
        """
        return self.cv_count()

    def component_path(self, component_index: int) -> str:
        """
        Returns the fully qualified path to the component with the
        given index — for curves, this is ``<full_path>.cv[N]``.

        Part of the skinnable-shape protocol consumed by
        :class:`SkinCluster`.
        """
        return f"{self.item.full_name()}.cv[{component_index}]"

    def cv_positions(self, space: str = "object") -> list[list[float]]:
        """
        Returns a list of ``[x, y, z]`` positions, one per CV, in CV
        index order. Uses ``MFnNurbsCurve.cvPositions`` for a single
        bulk API call instead of iterating per-CV.
        """
        points = self._curve.cvPositions(self._resolve_space(space))
        return [
            [p.x, p.y, p.z]
            for p in points
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

        Where each triplet list defines the position of the CV id in the
        list order. Applies the entire array in one
        ``MFnNurbsCurve.setCVPositions`` call.
        """
        if len(positions) != self.cv_count():
            raise ValueError(
                f"Number of CVs ({self.cv_count()}) does not match "
                f"length of cv_positions ({len(positions)})"
            )

        point_array = om.MPointArray()
        point_array.setLength(len(positions))
        for i, (x, y, z) in enumerate(positions):
            point_array[i] = om.MPoint(x, y, z)

        self._curve.setCVPositions(point_array, self._resolve_space(space))

        # -- Nurbs curves require an explicit updateCurve() after any
        # -- CV mutation; unlike meshes, the API does not propagate the
        # -- dirty flag automatically.
        self._curve.updateCurve()

    def cv_position(self, cv_index: int, space: str = "object") -> list[float]:
        """
        This returns a list containing the three components correlating to
        the x, y, z positions of the cv.
        """
        point = self._curve.cvPosition(cv_index, self._resolve_space(space))
        return [point.x, point.y, point.z]


    def set_cv_position(self, cv_index: int, position: list[float], space: str = "object"):
        """
        This takes in a position list, in the format:

            [x, y, z]

        The vertex with the given id will then have its position set to those values.
        """
        self._curve.setCVPosition(
            cv_index,
            om.MPoint(position[0], position[1], position[2]),
            self._resolve_space(space),
        )

        # -- Nurbs curves require an explicit updateCurve() after any
        # -- CV mutation; unlike meshes, the API does not propagate the
        # -- dirty flag automatically.
        self._curve.updateCurve()

    def _resolve_space(self, space: str):
        """
        Maps a space-name string to the corresponding ``om.MSpace``
        enum. Raises ``ValueError`` for unknown space names with a
        clear message listing the supported values, rather than the
        bare ``KeyError`` a dict lookup would produce.
        """
        if space not in self.spaces:
            raise ValueError(
                f"Unknown space {space!r}; expected one of "
                f"{tuple(self.spaces.keys())}"
            )
        return self.spaces[space]