import mref
from maya import cmds
from maya.api import OpenMaya as om


class Expression(mref.Trait):
    """
    Trait bound to any node with ``MFn.kExpression`` — expression nodes
    created by ``cmds.expression``. Exposes the expression text, the
    object it is bound to, whether it is time-driven, and the attributes
    it reads from and writes to.

    Maya inserts ``unitConversion`` nodes between an expression and any
    angular attribute it reads or writes; :meth:`input_attributes` and
    :meth:`output_attributes` look through those so the real scene
    attributes are returned.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kExpression)

    def expression_string(self) -> str:
        """
        Returns the expression text. Maya rewrites attribute references
        to their long names (``box.tx`` becomes ``box.translateX``).
        """
        return cmds.expression(self.item.full_name(), query=True, string=True)

    def set_expression_string(self, expression: str) -> None:
        """
        Replaces the expression text. Maya re-parses it and rebuilds the
        input / output connections to match.
        """
        cmds.expression(self.item.full_name(), edit=True, string=expression)

    def bound_object(self) -> mref.ReferencedItem|None:
        """
        Returns the object the expression is bound to (the node that
        unqualified attribute names in the expression refer to), or None
        if it is not bound to an object.
        """
        name = cmds.expression(self.item.full_name(), query=True, object=True)
        if not name:
            return None
        return mref.get(name)

    def set_bound_object(self, node: mref.ReferencedItem|str) -> None:
        """
        Binds the expression to the given object
        """
        if isinstance(node, mref.ReferencedItem):
            node = node.full_name()
        cmds.expression(self.item.full_name(), edit=True, object=node)

    def is_animated(self) -> bool:
        """
        Returns True if the expression is evaluated whenever time changes
        (Maya's "always evaluate"), rather than only when its inputs
        change.
        """
        return bool(cmds.expression(self.item.full_name(), query=True, alwaysEvaluate=True))

    def set_animated(self, state: bool) -> None:
        """
        Sets whether the expression is evaluated whenever time changes
        """
        cmds.expression(self.item.full_name(), edit=True, alwaysEvaluate=int(state))

    def input_attributes(self) -> mref.ReferenceList:
        """
        Returns the scene attributes the expression reads from, looking
        through any unitConversion nodes Maya inserted.
        """
        results = mref.ReferenceList()

        for plug in _array_elements(self._dependency_node.findPlug("input", False)):
            source = plug.source()
            if source.isNull:
                continue

            source = _through_unit_conversion(source, upstream=True)
            if source is None:
                continue

            for resolved in source:
                attribute = mref.get(resolved)
                if attribute not in results:
                    results.append(attribute)

        return results

    def output_attributes(self) -> mref.ReferenceList:
        """
        Returns the scene attributes the expression writes to, looking
        through any unitConversion nodes Maya inserted.
        """
        results = mref.ReferenceList()

        for plug in _array_elements(self._dependency_node.findPlug("output", False)):
            for destination in plug.destinations():
                for resolved in _through_unit_conversion(destination, upstream=False) or []:
                    attribute = mref.get(resolved)
                    if attribute not in results:
                        results.append(attribute)

        return results


def _array_elements(plug: om.MPlug) -> list[om.MPlug]:
    """
    Returns the existing elements of the given array plug
    """
    return [
        plug.elementByPhysicalIndex(index)
        for index in range(plug.numElements())
    ]


def _through_unit_conversion(plug: om.MPlug, upstream: bool) -> list[om.MPlug]|None:
    """
    If the given plug belongs to a unitConversion node, follow the
    conversion to the plug(s) on the other side of it. Otherwise the
    plug itself is returned in a list.
    """
    if not plug.node().hasFn(om.MFn.kUnitConversion):
        return [plug]

    conversion = om.MFnDependencyNode(plug.node())

    if upstream:
        source = conversion.findPlug("input", False).source()
        return None if source.isNull else [source]

    return list(conversion.findPlug("output", False).destinations())
