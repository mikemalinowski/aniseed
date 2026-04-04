import mref
from maya.api import OpenMaya as om


class MayaObject(mref.Trait):

    def __init__(self, *args, **kwargs):
        super(MayaObject, self).__init__(*args, **kwargs)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject):
            return True
        return False

    def m_object(self) -> om.MObject:
        """
        Returns the mobject for this object
        """
        return self._pointer
