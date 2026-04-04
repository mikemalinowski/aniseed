import mref
from maya import cmds
from maya.api import OpenMaya as om
import maya.api.OpenMayaAnim as oma


class AnimCurve(mref.Trait):
    """
    This trait will bind and represent attributes.
    """

    def __init__(self, *args, **kwargs):
        super(AnimCurve, self).__init__(*args, **kwargs)
        self._animcurve = oma.MFnAnimCurve(self._pointer)

    @classmethod
    def can_bind(cls, pointer):
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kAnimCurve):
            return True
        return False

    def to_dictionary(self):
        """
        Returns a dictionary serialisation of the curve
        :return:
        """
        curve_name = self.item.name()
        data = {
            "name": curve_name,
            "animCurveType": self._animcurve.animCurveType,
            "isWeighted": self._animcurve.isWeighted,
            "preInfinity": self._animcurve.preInfinityType,
            "postInfinity": self._animcurve.postInfinityType,
            "keys": []
        }
        for i in range(self._animcurve.numKeys):
            time_value = self._animcurve.input(i)

            key_data = {
                "time": time_value,
                "value": self._animcurve.value(i),
                "inTangentType": cmds.keyTangent(curve_name, query=True, index=(i, i), inTangentType=True)[0],
                "outTangentType": cmds.keyTangent(curve_name, query=True, index=(i, i), outTangentType=True)[0],
                "inTangentX": cmds.keyTangent(curve_name, query=True, index=(i, i), ix=True)[0],
                "inTangentY": cmds.keyTangent(curve_name, query=True, index=(i, i), iy=True)[0],
                "outTangentX": cmds.keyTangent(curve_name, query=True, index=(i, i), ox=True)[0],
                "outTangentY": cmds.keyTangent(curve_name, query=True, index=(i, i), oy=True)[0],
                "lockTangents": cmds.keyTangent(curve_name, query=True, index=(i, i), lock=True)[0],
                "inWeight": cmds.keyTangent(curve_name, query=True, index=(i, i), inWeight=True)[0],
                "outWeight": cmds.keyTangent(curve_name, query=True, index=(i, i), outWeight=True)[0],
                "weightLock": cmds.keyTangent(curve_name, query=True, index=(i, i), weightLock=True)[0],
                "weightedTangents": cmds.keyTangent(curve_name, query=True, index=(i, i), weightedTangents=True)[0],
            }

            data["keys"].append(key_data)

        return data

    def construct_from_dictionary(self, data):
        """
        Rebuilds the curve from teh data
        :param data:
        :return:
        """
        curve_name = self.item.name()

        # Set infinity
        cmds.setAttr(f"{curve_name}.preInfinity", data.get("preInfinity", 0))
        cmds.setAttr(f"{curve_name}.postInfinity", data.get("postInfinity", 0))

        # Remove all existing keys safely
        cmds.cutKey(curve_name, time=(0, float('inf')))

        for idx, key_data in enumerate(data["keys"]):
            self._animcurve.addKey(key_data["time"], key_data["value"])

            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), lock=key_data["lockTangents"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), inWeight=key_data["inWeight"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), outWeight=key_data["outWeight"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), weightedTangents=key_data["weightedTangents"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), inTangentType=key_data["inTangentType"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), outTangentType=key_data["outTangentType"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), ix=key_data["inTangentX"], iy=key_data["inTangentY"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), ox=key_data["outTangentX"], oy=key_data["outTangentY"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), inTangentType=key_data["inTangentType"])
            cmds.keyTangent(curve_name, edit=True, index=(idx, idx), outTangentType=key_data["outTangentType"])
