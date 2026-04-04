import mref
from maya import cmds
from maya.api import OpenMaya as om


class Constraint(mref.Trait):

    def __init__(self, *args, **kwargs):
        super(Constraint, self).__init__(*args, **kwargs)

        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kConstraint):
            return True
        return False

    def driven(self) -> mref.ReferencedItem|None:
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

    def drivers(self) -> list[mref.ReferencedItem]:
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

                if source.isNull:
                    continue

                referenced_node = mref.get(source.node())

                if referenced_node == self.item:
                    continue
                if referenced_node not in drivers:
                    drivers.append(referenced_node)

        return drivers

    def weight_attributes(self, full_name=False) -> list[mref.ReferencedItem|str]:
        """
        Returns a list of weight attributes for the constraint
        """
        constraint_type = cmds.nodeType(self.item.full_name())

        constraint_func = getattr(cmds, constraint_type)
        attribute_names = constraint_func(self.item.full_name(), query=True, weightAliasList=True)

        if not full_name:
            return attribute_names

        return mref.get(
            [
                f"{self.item.full_name()}.{attribute_name}"
                for attribute_name in attribute_names
            ]
        )