import mref
from maya import cmds
from maya.api import OpenMaya as om


class DependencyNode(mref.Trait):
    priority = -1

    attribute_types = {
        "bool": "at",
        "long": "at",
        "short": "at",
        "byte": "at",
        "char": "at",
        "enum": "at",
        "float": "at",
        "double": "at",
        "doubleAngle": "at",
        "doubleLinear": "at",
        "string": "dt",
        "stringArray": "dt",
        "compound": "at",
        "message": "at",
        "time": "at",
        "matrix": "dt",
        "fltMatrix": "at",
        "reflectanceRGB": "dt",
        "reflectance": "at",
        "spectrumRGB": "dt",
        "spectrum": "at",
        "float2": "dt",
        "float3": "dt",
        "float3": "at",
        "double2": "dt",
        "double2": "at",
        "double3": "dt",
        "double3": "at",
        "long2": "dt",
        "long2": "at",
        "long3": "dt",
        "long3": "at",
        "short2": "dt",
        "short2": "at",
        "short3": "dt",
        "short3": "at",
        "doubleArray": "dt",
        "floatArray": "dt",
        "Int32Array": "dt",
        "vectorArray": "dt",
        "nurbsCurve": "dt",
        "nurbsSurface": "dt",
        "mesh": "dt",
        "lattice": "dt",
        "pointArray": "dt",
    }

    def __init__(self, *args, **kwargs):
        super(DependencyNode, self).__init__(*args, **kwargs)

        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer):
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kDependencyNode):
            return True

    def name(self) -> str:
        """
        Returns the name of the node which is referenced
        """
        return self._dependency_node.name().split("|")[-1]

    def full_name(self):
        return self.name()

    def rename(self, new_name):
        cmds.rename(
            self.full_name(),
            new_name,
        )

    def attribute(self, attribute_name):
        attribute_address = f"{self.name()}.{attribute_name}"
        if not cmds.objExists(attribute_address):
            return None
        return mref.get(attribute_address)

    def attr(self, attribute_name):
        return self.attribute(attribute_name)

    def attributes(self, **kwargs):
        return [
            mref.get(f"{self.name()}.{attribute}")
            for attribute in cmds.listAttr(self.item.name(), **kwargs)
        ]

    def add_attribute(self, name, value, attribute_type, **kwargs):

        kwargs[self.attribute_types[attribute_type]] = attribute_type
        cmds.addAttr(
            self.full_name(),
            shortName=name,
            **kwargs
        )
        attribute = mref.get(f"{self.full_name()}.{name}")
        attribute.set(value)
        return attribute

    def node_type(self):
        return cmds.nodeType(self.full_name())
