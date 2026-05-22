import mref
from maya import cmds
from maya.api import OpenMaya as om


class DagNode(mref.Trait):
    """
    Trait bound to any node with ``MFn.kDagNode`` — transforms, joints,
    locators, all shape types, and anything else that lives in the DAG
    hierarchy. Exposes parent/child traversal, DAG-path queries, shape
    access, and constraint discovery.

    Priority ``0`` (the default), so it sits above ``DependencyNode``
    (``-1``) in the resolution order — ``full_name()`` returns the DAG
    path rather than the short name for any DAG node.
    """

    def __init__(self, *args, **kwargs):
        super(DagNode, self).__init__(*args, **kwargs)

        self._dag_node = om.MFnDagNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kDagNode):
            return True
        return False

    def full_name(self) -> str:
        """
        Returns the full path (long) name of the node.
        """
        return self._dag_node.fullPathName()

    def children(
        self,
        recursive: bool = False,
        node_type: str = None,
        name_match: str = None,
        include_shapes: bool = True,
    ) -> list[mref.ReferencedItem]:
        """
        Returns a list of children of the node.

        Args:
            recursive (bool, optional): If False (default) only immediate
                children will be returned. If True all descendants will be
                returned.
            node_type (str, optional): Only return children of the specified
                Maya node type.
            name_match (str, optional): Substring filter on the child's short
                name. Only children whose short name contains this substring
                are returned. Matching is case-sensitive.
            include_shapes (bool, optional): If True (default), shape children
                are included in the result. Set to False to skip shapes —
                useful when iterating only transform children.

        Returns:
            A list of mref.ReferencedItem instances.
        """
        additional_args = dict()

        if recursive:
            additional_args['allDescendents'] = True

        if node_type:
            additional_args['type'] = node_type

        return mref.ReferenceList(
            [
                mref.get(node)
                for node in cmds.listRelatives(self.item.full_name(), children=True, **additional_args) or []
                if not name_match or name_match in node.split("|")[-1]
                if include_shapes or not cmds.objectType(node, isAType="shape")
            ],
        )

    def parent(self) -> mref.ReferencedItem|None:
        """
        Returns the parent of this node, or None if this node is at the
        scene root.
        """
        parents = cmds.listRelatives(self.item.full_name(), parent=True, fullPath=True)
        if parents:
            return mref.get(parents[0])
        return None

    def all_parents(self) -> list[mref.ReferencedItem]:
        """
        Returns all the parents of this node
        """
        node = self
        parents = []

        while True:
            parent = node.parent()

            if not parent:
                return parents

            parents.append(parent)
            node = parent


    def set_parent(self, parent: mref.ReferencedItem|str|None) -> None:
        """
        This will set the parent of the current node. If the parent being
        passed is None, then this node will be parented to the scene root.
        """
        if parent is None:
            cmds.parent(self.item.full_name(), world=True)
            return

        parent = mref.get(parent)
        if parent.pointer() == self._pointer:
            return

        if self.parent() == parent:
            return

        cmds.parent(
            self.item.full_name(),
            parent.full_name(),
            absolute=True,
        )

    def add_child(self, child: mref.ReferencedItem|str) -> None:
        """
        This will make the given node a child of this node. Goes through
        ``cmds.parent`` so the operation is recorded in Maya's undo stack.
        No-ops if ``child`` is this node itself, or if ``child`` is
        already parented to this node.
        """
        child = mref.get(child)

        if child.pointer() == self._pointer:
            return

        if child.parent() == self.item:
            return

        cmds.parent(child.full_name(), self.item.full_name())

    def add_children(self, children: list[mref.ReferencedItem|str]) -> None:
        """
        This will make all the given nodes children of this node. Issued
        as a single ``cmds.parent`` call so the operation is recorded as
        one entry in Maya's undo stack. Children that are this node
        itself, or are already parented to this node, are silently
        skipped — matching ``add_child``'s guard behaviour.
        """
        if not children:
            return

        valid = []
        for child in children:
            child = mref.get(child)
            if child.pointer() == self._pointer:
                continue
            if child.parent() == self.item:
                continue
            valid.append(child.full_name())

        if not valid:
            return

        cmds.parent(*valid, self.item.full_name())

    def dag(self) -> om.MFnDagNode:
        """
        This will return the MFnDagNode object of the current node
        """
        return self._dag_node

    def shapes(self) -> list[mref.ReferencedItem]:
        """
        Returns a list of shapes belonging to the current node
        """
        return [
            mref.get(shape)
            for shape in cmds.listRelatives(self.item.full_name(), shapes=True, fullPath=True) or []
        ]

    def shape(self) -> mref.ReferencedItem|None:
        """
        Returns the first shape belonging to this node, or None if it
        has none.
        """
        results = cmds.listRelatives(self.item.full_name(), shapes=True, fullPath=True) or []
        if results:
            return mref.get(results[0])
        return None

    def constraints(self) -> mref.ReferenceList:
        """
        Returns the constraint nodes parented under this node.

        Limitation: only finds constraints that are direct children of
        this node, which is the conventional Maya layout for constraints
        driving a transform. Constraints that target this node but live
        elsewhere in the scene (custom rigs, exported skeletons, certain
        pipeline conventions) are not returned by this method. Walk the
        connection graph (``listConnections`` on the constraint output
        plugs) for those cases.

        Uses Maya's type-inheritance check (``isAType="constraint"``)
        rather than a substring match on the type name, so user-defined
        nodes whose type name happens to contain ``"constraint"`` won't
        be falsely included.
        """
        results = mref.ReferenceList()

        for child in self.children():
            if cmds.objectType(child.full_name(), isAType="constraint"):
                results.append(child)

        return results
