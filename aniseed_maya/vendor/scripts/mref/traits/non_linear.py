import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- The type-specific parameters of each nonLinear deformer type, in
# -- the order the attribute editor lists them. These live on the
# -- nonLinear node and are mirrored (by connection) onto the handle
# -- shape.
_PARAMETERS = {
    "bend": ["curvature", "lowBound", "highBound"],
    "twist": ["startAngle", "endAngle", "lowBound", "highBound"],
    "flare": ["startFlareX", "startFlareZ", "endFlareX", "endFlareZ", "curve", "lowBound", "highBound"],
    "sine": ["amplitude", "wavelength", "offset", "dropoff", "lowBound", "highBound"],
    "squash": ["factor", "expand", "maxExpandPos", "startSmoothness", "endSmoothness", "lowBound", "highBound"],
    "wave": ["amplitude", "wavelength", "offset", "dropoff", "dropoffPosition", "minRadius", "maxRadius"],
}

# -- Attributes unique to each type, used to identify the type when
# -- the handle shape is missing. Checked in order.
_TYPE_SIGNATURES = [
    ("wave", "maxRadius"),
    ("sine", "amplitude"),
    ("bend", "curvature"),
    ("twist", "startAngle"),
    ("flare", "startFlareX"),
    ("squash", "factor"),
]


class NonLinear(mref.Trait):
    """
    Trait bound to any node with ``MFn.kNonLinear`` — the ``nonLinear``
    deformer node created by ``cmds.nonLinear`` (bend, twist, flare,
    sine, squash and wave). Exposes the handle transform and handle
    shape, the deformer type, and its type-specific parameters
    (curvature, start/end angle, low/high bound, amplitude, ...).

    The parameters are stored on the nonLinear node and drive the
    matching attributes on the handle shape, so they are read and
    written here rather than on the handle.

    Input/output geometry, the envelope and the paintable per-component
    weights are provided by the generic ``GeometryFilter`` trait which is
    also bound to every nonLinear deformer.
    """

    # -- Sits above the generic GeometryFilter trait
    priority = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kNonLinear)

    def handle(self) -> mref.ReferencedItem|None:
        """
        Returns the handle transform which positions the deformer (the
        node whose ``worldMatrix`` feeds the deformer's ``matrix``), or
        None if it is not connected.
        """
        source = self._dependency_node.findPlug("matrix", False).source()
        if source.isNull:
            return None
        return mref.get(source.node())

    def handle_shape(self) -> mref.ReferencedItem|None:
        """
        Returns the handle shape (``deformBend``, ``deformTwist``, ...)
        which draws the deformer, or None if there is none.
        """
        # -- The handle shape feeds the deformer's deformerData
        source = self._dependency_node.findPlug("deformerData", False).source()
        if source.isNull or not source.node().hasFn(om.MFn.kDeformFunc):
            return None
        return mref.get(source.node())

    def deformer_type(self) -> str:
        """
        Returns the type of nonLinear deformer — one of ``"bend"``,
        ``"twist"``, ``"flare"``, ``"sine"``, ``"squash"`` or
        ``"wave"``.
        """
        handle_shape = self.handle_shape()
        if handle_shape is not None:
            node_type = cmds.nodeType(handle_shape.full_name())
            if node_type.startswith("deform"):
                return node_type[len("deform"):].lower()

        # -- Without a handle shape, identify the type by the
        # -- attributes it carries
        for deformer_type, attribute_name in _TYPE_SIGNATURES:
            if self._dependency_node.hasAttribute(attribute_name):
                return deformer_type

        raise RuntimeError(f"Could not determine the deformer type of {self.item.name()}")

    def parameters(self) -> dict:
        """
        Returns a dict of the type-specific parameters of this deformer
        and their values, e.g. ``{"curvature": 0.0, "lowBound": -1.0,
        "highBound": 1.0}`` for a bend.
        """
        return {
            name: self.parameter(name)
            for name in _PARAMETERS[self.deformer_type()]
        }

    def parameter(self, name: str) -> float|bool:
        """
        Returns the value of the named type-specific parameter (see
        :meth:`parameters` for the valid names)
        """
        self._validate_parameter(name)
        return cmds.getAttr(f"{self.item.full_name()}.{name}")

    def set_parameter(self, name: str, value: float|bool) -> None:
        """
        Sets the value of the named type-specific parameter (see
        :meth:`parameters` for the valid names)
        """
        self._validate_parameter(name)
        cmds.setAttr(f"{self.item.full_name()}.{name}", value)

    def bounds(self) -> tuple[float, float]:
        """
        Returns the (low, high) bounds of the deformation along the
        handle's axis. Not available on wave deformers, which are
        radial (see ``minRadius``/``maxRadius``).
        """
        return self.parameter("lowBound"), self.parameter("highBound")

    def set_bounds(self, low: float, high: float) -> None:
        """
        Sets the (low, high) bounds of the deformation along the
        handle's axis. Not available on wave deformers.
        """
        self.set_parameter("lowBound", low)
        self.set_parameter("highBound", high)

    def curvature(self) -> float:
        """
        Returns the curvature of a bend deformer, in degrees
        """
        return self.parameter("curvature")

    def set_curvature(self, value: float) -> None:
        """
        Sets the curvature of a bend deformer, in degrees
        """
        self.set_parameter("curvature", value)

    def angles(self) -> tuple[float, float]:
        """
        Returns the (start, end) angles of a twist deformer, in degrees
        """
        return self.parameter("startAngle"), self.parameter("endAngle")

    def set_angles(self, start: float, end: float) -> None:
        """
        Sets the (start, end) angles of a twist deformer, in degrees
        """
        self.set_parameter("startAngle", start)
        self.set_parameter("endAngle", end)

    def _validate_parameter(self, name: str) -> None:
        """
        Raises a ValueError if the given parameter does not apply to
        this deformer's type
        """
        deformer_type = self.deformer_type()
        valid = _PARAMETERS[deformer_type]
        if name not in valid:
            raise ValueError(
                f"{name!r} is not a parameter of {deformer_type} deformer "
                f"{self.item.name()}; expected one of {tuple(valid)}"
            )
