import mref
from maya import cmds
from maya.api import OpenMaya as om


class Constraint(mref.Trait):
    """
    Trait bound to any node with ``MFn.kConstraint`` — point, orient,
    parent, scale, aim, pole-vector, and any other constraint type
    derived from Maya's constraint base. Exposes the constrained node
    (:meth:`driven`), the nodes driving the constraint
    (:meth:`drivers`), and the per-target weight attributes
    (:meth:`weight_attributes`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kConstraint)

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

    def drivers(self) -> mref.ReferenceList:
        """
        Returns the list of driver nodes feeding this constraint's
        target inputs. The constraint's own target hierarchy
        connections (``targetParentMatrix``) are excluded — only true
        driver transforms are returned.
        """
        target_plug = self._dependency_node.findPlug("target", False)
        drivers = mref.ReferenceList()

        for i in range(target_plug.numElements()):
            element = target_plug.elementByPhysicalIndex(i)

            for child_index in range(element.numChildren()):
                child = element.child(child_index)

                # -- Skip targetParentMatrix; it's the parent of the
                # -- target transform (metadata) not a driver. Use
                # -- useLongNames=True so the suffix check matches
                # -- the long attribute name rather than the short
                # -- alias (``tpm``).
                if child.partialName(useLongNames=True).endswith("targetParentMatrix"):
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

    def weight_attributes(self) -> mref.ReferenceList:
        """
        Returns the per-target weight attributes for the constraint.
        The result is a ``ReferenceList`` of attribute ReferencedItems,
        one entry per target.
        """
        constraint_type = cmds.nodeType(self.item.full_name())

        constraint_func = getattr(cmds, constraint_type)
        attribute_names = constraint_func(self.item.full_name(), query=True, weightAliasList=True)

        return mref.ReferenceList(
            mref.get(f"{self.item.full_name()}.{attribute_name}")
            for attribute_name in attribute_names
        )