import mref
from maya.api import OpenMaya as om
from maya import cmds


class Transform(mref.Trait):

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kTransform):
            return True

    def get_matrix(self, space: str = "object") -> list[float]:
        """
        Returns the matrix of this node as a flat 4x4 matrix list
        """
        additional_kwargs = dict()
        if space == "object":
            additional_kwargs["objectSpace"] = True
        else:
            additional_kwargs["worldSpace"] = True

        return cmds.xform(self.item.full_name(), query=True, matrix=True, **additional_kwargs)

    def set_matrix(self, matrix: list[float], space: str = "object") -> None:
        """
        Sets the matrix of this transform
        """
        additional_kwargs = dict()
        if space == "object":
            additional_kwargs["objectSpace"] = True
        else:
            additional_kwargs["worldSpace"] = True

        cmds.xform(self.item.full_name(), matrix=matrix, **additional_kwargs)

    def xform(self, **kwargs) -> None:
        """
        Runs an xform process over this transform
        """
        return cmds.xform(self.item.full_name(), **kwargs)

    def match_to(self, other: mref.ReferencedItem|str) -> None:
        """
        Does a worldspace transform match between this object and the
        given object.
        """
        other = mref.get(other)
        self.set_matrix(other.get_matrix(space="world"), space="world")
