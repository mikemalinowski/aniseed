import mref
from maya import cmds
from maya.api import OpenMaya as om


class Attribute(mref.Trait):
    """
    This trait will bind and represent attributes.
    """

    complex_types = [
        "string",
        "matrix",
        "doubleArray",
        "Int32Array",
        "vectorArray",
        "pointArray",
        "componentList",
        "stringArray",
        "mesh",
        "nurbsCurve",
    ]

    def __init__(self, *args, **kwargs):
        super(Attribute, self).__init__(*args, **kwargs)

        self._node = mref.get(self._pointer.node())
        self._m_plug = self._pointer
        self._attribute_type = cmds.getAttr(self.name(include_node=True), type=True)

    @classmethod
    def can_bind(cls, pointer):
        if isinstance(pointer, om.MPlug):
            return True

    def node(self):
        """
        This will return the mref
        """
        return self._node

    def name(self, include_node=False):
        if include_node:
            return f"{self.node().name()}.{self._m_plug.partialName(useLongNames=True)}"
        else:
            return self._m_plug.partialName(useLongNames=True)

    def path(self):
        return f"{self.node().full_name()}.{self._m_plug.partialName(useLongNames=True)}"

    def set(self, *args, **kwargs):
        if self._attribute_type in self.complex_types and "type" not in kwargs:
            kwargs["type"] = self._attribute_type

        cmds.setAttr(
            self.path(),
            *args,
            **kwargs
        )

    def get(self, **kwargs):
        return cmds.getAttr(
            self.path(),
            **kwargs
        )

    def get_type(self):
        return self._attribute_type

    def connect(self, attribute, force=False, **kwargs):
        attribute = mref.get(attribute)
        cmds.connectAttr(
            self.path(),
            attribute.path(),
            force=force,
            **kwargs
        )

    def disconnect(self, attribute=None):
        if attribute:
            attributes = mref.get(attribute)

        else:
            attributes = self.connections()

        for attribute in attributes:
            if not attribute:
                continue

            cmds.disconnectAttr(
                self.path(),
                attribute.path(),
            )

    def connections(self):
        return self.outputs() + self.inputs()

    def inputs(self):
        return [
            mref.get(attribute)
            for attribute in
            cmds.listConnections(self.path(), source=True, destination=False, plugs=True) or []
        ]

    def outputs(self):
        return [
            mref.get(attribute)
            for attribute in
            cmds.listConnections(self.path(), source=False, destination=True, plugs=True) or []
        ]

    def __repr__(self):
        return self.name(include_node=True)
