import mref
from maya import cmds
from maya.api import OpenMaya as om


class Constraint(mref.Trait):

    def __init__(self, *args, **kwargs):
        super(Constraint, self).__init__(*args, **kwargs)

        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer):
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kConstraint):
            return True

    def driven(self):
        """
        Returns the node being driven by the constraint
        """
        potential_attributes = [
            "constraintTranslateX",
            "constraintRotateX",
            "constraintScaleX",
        ]
        for attribute_name in potential_attributes:
            if not self._dependency_node.hasAttribute(attribute_name):
                continue

            plug = self._dependency_node.findPlug(attribute_name, False)
            destinations = plug.destinations()

            for destination in destinations:
                return mref.get(destination.node())

        return None

    def drivers(self):
        """
        Returns the list of drivers for the constraint
        """
        target_plug = self._dependency_node.findPlug("target", False)
        drivers = []

        for i in range(target_plug.numElements()):
            element = target_plug.elementByPhysicalIndex(i)

            for child_index in range(element.numChildren()):
                child = element.child(child_index)

                if child.partialName(useLongNames=False).endswith("targetParentMatrix"):
                    continue

                source = child.source()

                if not source.isNull:
                    referenced_node = mref.get(source.node())

                    if referenced_node == self.item:
                        continue
                    if referenced_node not in drivers:
                        drivers.append(referenced_node)

        return drivers

    def weight_attributes(self):
        """
        Returns a list of weight attributes for the constraint
        """
        constraint_type = cmds.nodeType(self.item.full_name())

        constraint_func = getattr(cmds, constraint_type)
        return constraint_func(query=True, weightAliasList=True)
