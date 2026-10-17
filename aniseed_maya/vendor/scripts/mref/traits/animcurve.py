import mref
from maya import cmds
from maya.api import OpenMaya as om
import maya.api.OpenMayaAnim as oma


# -- cmds-style tangent type names to MFnAnimCurve tangent constants
_TANGENT_TYPES = {
    "global": oma.MFnAnimCurve.kTangentGlobal,
    "fixed": oma.MFnAnimCurve.kTangentFixed,
    "linear": oma.MFnAnimCurve.kTangentLinear,
    "flat": oma.MFnAnimCurve.kTangentFlat,
    "spline": oma.MFnAnimCurve.kTangentSmooth,
    "step": oma.MFnAnimCurve.kTangentStep,
    "stepnext": oma.MFnAnimCurve.kTangentStepNext,
    "slow": oma.MFnAnimCurve.kTangentSlow,
    "fast": oma.MFnAnimCurve.kTangentFast,
    "clamped": oma.MFnAnimCurve.kTangentClamped,
    "plateau": oma.MFnAnimCurve.kTangentPlateau,
    "auto": oma.MFnAnimCurve.kTangentAuto,
    "autoease": oma.MFnAnimCurve.kTangentAutoEase,
    "automix": oma.MFnAnimCurve.kTangentAutoMix,
    "autocustom": oma.MFnAnimCurve.kTangentAutoCustom,
}
_TANGENT_NAMES = {value: key for key, value in _TANGENT_TYPES.items()}

# -- cmds-style infinity names to MFnAnimCurve infinity constants
_INFINITY_TYPES = {
    "constant": oma.MFnAnimCurve.kConstant,
    "linear": oma.MFnAnimCurve.kLinear,
    "cycle": oma.MFnAnimCurve.kCycle,
    "cycleRelative": oma.MFnAnimCurve.kCycleRelative,
    "oscillate": oma.MFnAnimCurve.kOscillate,
}
_INFINITY_NAMES = {value: key for key, value in _INFINITY_TYPES.items()}


def _lookup(mapping: dict, name: str, label: str):
    """
    Returns mapping[name], raising a ValueError listing the valid
    names if the name is unknown.
    """
    try:
        return mapping[name]
    except KeyError:
        raise ValueError(
            f"Unknown {label} {name!r}; expected one of {sorted(mapping)}"
        )


class AnimCurve(mref.Trait):
    """
    Trait bound to any node with ``MFn.kAnimCurve``. Provides
    serialisation of an anim curve's keys, tangents, infinity
    behaviour and weighting state, plus a reconstruction method that
    rebuilds the same key data on a curve of the same type.

    It also exposes key querying/editing (count, times, values, add,
    insert, remove, evaluate), tangent and infinity types, weighting,
    the curve type (``TL``, ``TA``, ``UU`` ...) and the attributes the
    curve is driven by / drives.

    Units: unless stated otherwise every time and value accepted or
    returned by this trait is in Maya's current UI units (frames in the
    current time unit, degrees for angular curves, the current linear
    unit for linear curves) — matching what ``cmds.keyframe`` reports.
    For driven-key curves (``U*`` input) the "time" is the driver value.

    Note: :meth:`to_dictionary` only serialises the *shape* of the
    curve. It does not record which attribute the curve drives, nor
    any character set, layer, or container membership.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._animcurve = oma.MFnAnimCurve(self._pointer)

    @classmethod
    def can_bind(cls, pointer) -> bool:
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kAnimCurve)

    def scale(self, scale_by: float):
        anim_curve = self.item.name()

        key_count = cmds.keyframe(anim_curve, query=True, keyframeCount=True)

        for i in range(key_count):
            value = cmds.keyframe(
                anim_curve,
                query=True,
                index=(i, i),
                valueChange=True
            )[0]

            cmds.keyframe(
                anim_curve,
                edit=True,
                index=(i, i),
                valueChange=value * scale_by
            )

    def to_dictionary(self) -> dict:
        """
        Serialise this anim curve to a dictionary containing the
        curve's name, type, weighting state, infinity behaviour, and
        every key (time, value, tangent types, tangent positions, and
        weights).
        """
        curve_name = self.item.name()
        data = {
            "name": curve_name,
            "animCurveType": self._animcurve.animCurveType,
            "isWeighted": self._animcurve.isWeighted,
            "preInfinity": self._animcurve.preInfinityType,
            "postInfinity": self._animcurve.postInfinityType,
            "keys": [],
        }

        if not self._animcurve.numKeys:
            return data

        # Query each tangent flag once for the whole curve (one value
        # per key). Flags must not be batched into a single
        # cmds.keyTangent query: Maya returns the values in its own
        # internal flag order, not the order the flags were passed in.
        flags = {
            "inTangentType": "inTangentType",
            "outTangentType": "outTangentType",
            "inTangentX": "ix",
            "inTangentY": "iy",
            "outTangentX": "ox",
            "outTangentY": "oy",
            "lockTangents": "lock",
            "inWeight": "inWeight",
            "outWeight": "outWeight",
            "weightLock": "weightLock",
            "weightedTangents": "weightedTangents",
        }
        tangent_data = {
            key: cmds.keyTangent(curve_name, query=True, **{flag: True})
            for key, flag in flags.items()
        }

        for i in range(self._animcurve.numKeys):
            key_data = {
                "time": self._animcurve.input(i),
                "value": self._animcurve.value(i),
            }
            for key, values in tangent_data.items():
                # -- Curve-level flags (weightedTangents) may come back
                # -- as a single value rather than one per key.
                key_data[key] = values[i] if len(values) == self._animcurve.numKeys else values[0]
            data["keys"].append(key_data)

        return data

    def construct_from_dictionary(self, data: dict) -> None:
        """
        Rebuild this curve's keys from a dictionary produced by
        ``to_dictionary``. All existing keys on the curve are cleared
        first.

        :param data: A dictionary with the same shape as
            ``to_dictionary`` returns. Keys must be in time-ascending
            order — the order of ``data["keys"]`` is taken to match
            the curve-index of each key after insertion.
        """
        curve_name = self.item.name()

        cmds.setAttr(f"{curve_name}.preInfinity", data.get("preInfinity", 0))
        cmds.setAttr(f"{curve_name}.postInfinity", data.get("postInfinity", 0))

        # Restore curve-level weighting state before adding keys so the
        # per-key weights apply correctly.
        self._animcurve.setIsWeighted(data.get("isWeighted", False))

        # Clear all existing keys, including any at negative time. This
        # is done through the API rather than cmds.cutKey(clear=True)
        # because cutKey deletes the curve node itself once it has no
        # keys left, which would leave this trait pointing at nothing.
        self._remove_all_keys()

        for idx, key_data in enumerate(data.get("keys", [])):
            self._animcurve.addKey(key_data["time"], key_data["value"])

            # Each flag (or pair of position flags) goes in its own
            # cmds.keyTangent call because Maya rejects several
            # combinations in a single edit-mode call (e.g. inWeight +
            # weightedTangents together). Tangent types are set last so
            # we don't need to re-assert them after the positions —
            # setting positions can otherwise flip the type to "fixed".
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), lock=key_data["lockTangents"])
            # weightedTangents is really a curve-level setting, so the
            # curve's isWeighted value wins over the per-key copy.
            weighted = data.get("isWeighted", key_data["weightedTangents"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), weightedTangents=weighted)
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), inWeight=key_data["inWeight"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), outWeight=key_data["outWeight"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), ix=key_data["inTangentX"], iy=key_data["inTangentY"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), ox=key_data["outTangentX"], oy=key_data["outTangentY"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), inTangentType=key_data["inTangentType"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), outTangentType=key_data["outTangentType"])

    # ------------------------------------------------------------------
    # Curve classification
    # ------------------------------------------------------------------

    def curve_type(self) -> str:
        """
        Returns the two-letter curve type taken from the node type —
        input then output: ``T`` (time) or ``U`` (unitless) followed by
        ``L`` (linear), ``A`` (angular), ``T`` (time) or ``U``
        (unitless). For example ``"TL"`` for an ``animCurveTL``.
        """
        return om.MFnDependencyNode(self._pointer).typeName[-2:]

    def is_driven_key(self) -> bool:
        """
        Returns True if this is a set-driven-key style curve — i.e. its
        input is unitless (``UL``, ``UA``, ``UT``, ``UU``) and is driven
        by an attribute rather than by time.
        """
        return self._animcurve.isUnitlessInput

    # ------------------------------------------------------------------
    # Key queries
    # ------------------------------------------------------------------

    def key_count(self) -> int:
        """
        Returns the number of keys on this curve.
        """
        return self._animcurve.numKeys

    def key_times(self) -> list[float]:
        """
        Returns the time (or driver value, for driven keys) of every
        key in index order, in UI units.
        """
        return [
            self._input_to_ui(self._animcurve.input(index))
            for index in range(self._animcurve.numKeys)
        ]

    def key_values(self) -> list[float]:
        """
        Returns the value of every key in index order, in UI units
        (e.g. degrees for an angular curve).
        """
        if not self._animcurve.numKeys:
            return []
        return list(
            cmds.keyframe(self.item.full_name(), query=True, valueChange=True) or []
        )

    def key_index(self, time: float) -> int|None:
        """
        Returns the index of the key at exactly the given time (or
        driver value), or None if there is no key there.
        """
        return self._animcurve.find(self._input_from_ui(time))

    def value_at(self, time: float) -> float:
        """
        Evaluates the curve at the given time (or driver value) and
        returns the result in UI units. Works between and outside keys,
        honouring tangents and pre/post infinity.
        """
        return self._output_to_ui(
            self._animcurve.evaluate(self._input_from_ui(time))
        )

    # ------------------------------------------------------------------
    # Key editing
    # ------------------------------------------------------------------

    def add_key(
        self,
        time: float,
        value: float,
        in_tangent_type: str|None = None,
        out_tangent_type: str|None = None,
    ) -> int:
        """
        Adds a key at the given time (or driver value) with the given
        value, both in UI units. If a key already exists at that time
        its value is replaced. Returns the index of the key.

        :param in_tangent_type: Optional cmds-style tangent name
            (``"auto"``, ``"linear"``, ``"flat"``, ``"step"``,
            ``"spline"``, ``"clamped"``, ...). None uses the global
            default.
        :param out_tangent_type: As ``in_tangent_type``.
        """
        tangent_in = _lookup(_TANGENT_TYPES, in_tangent_type or "global", "tangent type")
        tangent_out = _lookup(_TANGENT_TYPES, out_tangent_type or "global", "tangent type")

        return self._animcurve.addKey(
            self._input_from_ui(time),
            self._output_from_ui(value),
            tangentInType=tangent_in,
            tangentOutType=tangent_out,
        )

    def insert_key(self, time: float) -> int:
        """
        Inserts a key at the given time (or driver value) without
        changing the shape of the curve — the key takes the curve's
        current value and neighbouring tangents are adjusted. If a key
        already exists there its index is returned unchanged.
        """
        existing = self.key_index(time)
        if existing is not None:
            return existing
        return self._animcurve.insertKey(self._input_from_ui(time))

    def remove_key(self, time: float) -> bool:
        """
        Removes the key at exactly the given time (or driver value).
        Returns True if a key was removed, False if there was none.
        Unlike ``cmds.cutKey`` this never deletes the curve node, even
        when the last key is removed.
        """
        index = self.key_index(time)
        if index is None:
            return False
        self._animcurve.remove(index)
        return True

    def offset_keys(self, time_offset: float = 0.0, value_offset: float = 0.0) -> None:
        """
        Shifts every key on the curve by the given time (or driver
        value) offset and value offset, both in UI units.
        """
        if not self._animcurve.numKeys:
            return

        kwargs = dict(edit=True, relative=True)
        if time_offset:
            if self.is_driven_key():
                kwargs["floatChange"] = time_offset
            else:
                kwargs["timeChange"] = time_offset
        if value_offset:
            kwargs["valueChange"] = value_offset

        if len(kwargs) > 2:
            cmds.keyframe(self.item.full_name(), **kwargs)

    # ------------------------------------------------------------------
    # Tangents / infinity / weighting
    # ------------------------------------------------------------------

    def tangent_types(self, index: int) -> tuple[str, str]:
        """
        Returns the ``(in, out)`` tangent type names of the key at the
        given index, using cmds-style names (``"auto"``, ``"linear"``
        etc).
        """
        return (
            _TANGENT_NAMES.get(self._animcurve.inTangentType(index), "unknown"),
            _TANGENT_NAMES.get(self._animcurve.outTangentType(index), "unknown"),
        )

    def set_tangent_types(
        self,
        in_type: str|None = None,
        out_type: str|None = None,
        index: int|None = None,
    ) -> None:
        """
        Sets the in and/or out tangent type of the key at the given
        index, or of every key when ``index`` is None. Types use
        cmds-style names (``"auto"``, ``"linear"``, ``"flat"``,
        ``"step"``, ``"spline"``, ``"clamped"``, ...); a type left as
        None is not changed.
        """
        tangent_in = _lookup(_TANGENT_TYPES, in_type, "tangent type") if in_type else None
        tangent_out = _lookup(_TANGENT_TYPES, out_type, "tangent type") if out_type else None

        indices = range(self._animcurve.numKeys) if index is None else [index]
        for key_index in indices:
            if tangent_in is not None:
                self._animcurve.setInTangentType(key_index, tangent_in)
            if tangent_out is not None:
                self._animcurve.setOutTangentType(key_index, tangent_out)

    def pre_infinity(self) -> str:
        """
        Returns the pre-infinity behaviour as a cmds-style name —
        ``"constant"``, ``"linear"``, ``"cycle"``, ``"cycleRelative"``
        or ``"oscillate"``.
        """
        return _INFINITY_NAMES[self._animcurve.preInfinityType]

    def set_pre_infinity(self, infinity_type: str) -> None:
        """
        Sets the pre-infinity behaviour from a cmds-style name (see
        :meth:`pre_infinity`).
        """
        self._animcurve.setPreInfinityType(
            _lookup(_INFINITY_TYPES, infinity_type, "infinity type"),
        )

    def post_infinity(self) -> str:
        """
        Returns the post-infinity behaviour as a cmds-style name (see
        :meth:`pre_infinity`).
        """
        return _INFINITY_NAMES[self._animcurve.postInfinityType]

    def set_post_infinity(self, infinity_type: str) -> None:
        """
        Sets the post-infinity behaviour from a cmds-style name (see
        :meth:`pre_infinity`).
        """
        self._animcurve.setPostInfinityType(
            _lookup(_INFINITY_TYPES, infinity_type, "infinity type"),
        )

    def is_weighted(self) -> bool:
        """
        Returns True if the curve uses weighted tangents.
        """
        return self._animcurve.isWeighted

    def set_weighted(self, state: bool) -> None:
        """
        Sets whether the curve uses weighted tangents.
        """
        self._animcurve.setIsWeighted(state)

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    def driven_attributes(self) -> mref.ReferenceList:
        """
        Returns the attributes this curve's ``output`` drives, skipping
        any unitConversion nodes. Note that if the curve feeds an
        intermediate node (e.g. a ``blendWeighted`` for stacked driven
        keys, or an anim layer blend) that node's input is returned,
        not the final attribute.
        """
        return mref.ReferenceList(
            mref.get(attribute)
            for attribute in cmds.listConnections(
                f"{self.item.full_name()}.output",
                source=False,
                destination=True,
                plugs=True,
                skipConversionNodes=True,
            ) or []
        )

    def driver_attribute(self) -> mref.ReferencedItem|None:
        """
        Returns the attribute connected to this curve's ``input`` —
        the driver of a driven-key curve — skipping unitConversion
        nodes. Returns None when nothing is connected (the normal case
        for time-based curves, which implicitly use scene time).
        """
        sources = cmds.listConnections(
            f"{self.item.full_name()}.input",
            source=True,
            destination=False,
            plugs=True,
            skipConversionNodes=True,
        ) or []
        return mref.get(sources[0]) if sources else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _remove_all_keys(self) -> None:
        """
        Removes every key from the curve without deleting the node.
        """
        for index in reversed(range(self._animcurve.numKeys)):
            self._animcurve.remove(index)

    def _input_from_ui(self, time: float):
        """
        Converts a UI-unit time / driver value into what MFnAnimCurve
        expects for this curve's input.
        """
        if self._animcurve.isUnitlessInput:
            return float(time)
        return om.MTime(time, om.MTime.uiUnit())

    def _input_to_ui(self, time) -> float:
        """
        Converts an MFnAnimCurve input (MTime or float) to UI units.
        """
        if isinstance(time, om.MTime):
            return time.asUnits(om.MTime.uiUnit())
        return float(time)

    def _output_from_ui(self, value: float):
        """
        Converts a UI-unit value into the internal unit MFnAnimCurve
        expects for this curve's output.
        """
        output = self.curve_type()[-1]
        if output == "A":
            return om.MAngle(value, om.MAngle.uiUnit()).asRadians()
        if output == "L":
            return om.MDistance(value, om.MDistance.uiUnit()).asCentimeters()
        if output == "T":
            return om.MTime(value, om.MTime.uiUnit())
        return float(value)

    def _output_to_ui(self, value) -> float:
        """
        Converts an internal MFnAnimCurve output value to UI units.
        """
        if isinstance(value, om.MTime):
            return value.asUnits(om.MTime.uiUnit())
        output = self.curve_type()[-1]
        if output == "A":
            return om.MAngle(value).asUnits(om.MAngle.uiUnit())
        if output == "L":
            return om.MDistance(value).asUnits(om.MDistance.uiUnit())
        return float(value)