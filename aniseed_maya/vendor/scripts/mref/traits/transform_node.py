import mref
from maya.api import OpenMaya as om
from maya import cmds


class Transform(mref.Trait):

    @classmethod
    def can_bind(cls, pointer):
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kTransform):
            return True

    def get_matrix(self, space="object"):

        additional_kwargs = dict()
        if space == "object":
            additional_kwargs["objectSpace"] = True
        else:
            additional_kwargs["worldSpace"] = True

        return cmds.xform(self.item.full_name(), query=True, matrix=True, **additional_kwargs)

    def set_matrix(self, matrix, space="object"):

        additional_kwargs = dict()
        if space == "object":
            additional_kwargs["objectSpace"] = True
        else:
            additional_kwargs["worldSpace"] = True


        cmds.xform(self.item.full_name(), matrix=matrix, **additional_kwargs)

    def xform(self, **kwargs):
        return cmds.xform(self.item.full_name(), **kwargs)

    def match_to(self, other):
        self.set_matrix(other.get_matrix(space="world"), space="world")
