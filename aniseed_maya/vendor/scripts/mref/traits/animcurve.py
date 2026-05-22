import mref
from maya import cmds
from maya.api import OpenMaya as om
import maya.api.OpenMayaAnim as oma


class AnimCurve(mref.Trait):
    """
    Trait bound to any node with ``MFn.kAnimCurve``. Provides
    serialisation of an anim curve's keys, tangents, infinity
    behaviour and weighting state, plus a reconstruction method that
    rebuilds the same key data on a curve of the same type.

    Note: this trait only serialises the *shape* of the curve. It does
    not record which attribute the curve drives, nor any character
    set, layer, or container membership.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._animcurve = oma.MFnAnimCurve(self._pointer)

    @classmethod
    def can_bind(cls, pointer) -> bool:
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kAnimCurve)

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

        for i in range(self._animcurve.numKeys):
            # Batch all tangent queries into one cmds.keyTangent call;
            # returned values match the flag order below.
            (
                in_tangent_type,
                out_tangent_type,
                in_tangent_x,
                in_tangent_y,
                out_tangent_x,
                out_tangent_y,
                lock_tangents,
                in_weight,
                out_weight,
                weight_lock,
                weighted_tangents,
            ) = cmds.keyTangent(
                curve_name,
                query=True,
                index=(i, i),
                inTangentType=True,
                outTangentType=True,
                ix=True, iy=True,
                ox=True, oy=True,
                lock=True,
                inWeight=True, outWeight=True,
                weightLock=True,
                weightedTangents=True,
            )

            data["keys"].append({
                "time": self._animcurve.input(i),
                "value": self._animcurve.value(i),
                "inTangentType": in_tangent_type,
                "outTangentType": out_tangent_type,
                "inTangentX": in_tangent_x,
                "inTangentY": in_tangent_y,
                "outTangentX": out_tangent_x,
                "outTangentY": out_tangent_y,
                "lockTangents": lock_tangents,
                "inWeight": in_weight,
                "outWeight": out_weight,
                "weightLock": weight_lock,
                "weightedTangents": weighted_tangents,
            })

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

        # Clear all existing keys, including any at negative time.
        cmds.cutKey(curve_name, clear=True)

        for idx, key_data in enumerate(data["keys"]):
            self._animcurve.addKey(key_data["time"], key_data["value"])

            # Each flag (or pair of position flags) goes in its own
            # cmds.keyTangent call because Maya rejects several
            # combinations in a single edit-mode call (e.g. inWeight +
            # weightedTangents together). Tangent types are set last so
            # we don't need to re-assert them after the positions —
            # setting positions can otherwise flip the type to "fixed".
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), lock=key_data["lockTangents"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), weightedTangents=key_data["weightedTangents"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), inWeight=key_data["inWeight"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), outWeight=key_data["outWeight"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), ix=key_data["inTangentX"], iy=key_data["inTangentY"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), ox=key_data["outTangentX"], oy=key_data["outTangentY"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), inTangentType=key_data["inTangentType"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), outTangentType=key_data["outTangentType"])