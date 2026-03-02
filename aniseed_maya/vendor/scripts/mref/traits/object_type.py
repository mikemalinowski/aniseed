import mref
from maya.api import OpenMaya as om


class MayaObject(mref.Trait):

    def __init__(self, *args, **kwargs):
        super(MayaObject, self).__init__(*args, **kwargs)

    @classmethod
    def can_bind(cls, pointer):
        if isinstance(pointer, om.MObject):
            return True

    def m_object(self):
        return self._pointer
