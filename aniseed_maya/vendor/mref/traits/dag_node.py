import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- Values of the overrideDisplayType enum, in index order
_DISPLAY_OVERRIDE_TYPES = ("normal", "template", "reference")

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
                for node in cmds.listRelatives(self.item.full_name(), children=True, path=True, **additional_args) or []
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

    def has_zeroed_pivots(self, tolerance=1e-6):
        """Return True if the transform has reset/frozen pivots.

        Checks that rotatePivot, scalePivot, rotatePivotTranslate and
        scalePivotTranslate are all at the origin. Accepts either a transform
        or a shape name.
        """
        for attr in ("rotatePivot", "scalePivot", "rotatePivotTranslate", "scalePivotTranslate"):
            x, y, z = cmds.getAttr("{}.{}".format(self.item.full_name(), attr))[0]
            if abs(x) > tolerance or abs(y) > tolerance or abs(z) > tolerance:
                return False
        return True

    def lock_transform_attributes(self, hide=False) -> None:
        """
        Locks the nine scalar transform channels on this node — translateX/Y/Z,
        rotateX/Y/Z, scaleX/Y/Z. Does not lock visibility, nor the parent
        compound translate/rotate/scale attributes themselves. Has no unlock
        counterpart; call ``unlock_attributes`` with explicit channel names
        to reverse.
        """
        additional_kwargs = {}
        if hide:
            additional_kwargs["channelBox"] = False

        for type_ in ["t", "r", "s"]:
            for axis in ["x", "y", "z"]:
                cmds.setAttr(f"{self.item.full_name()}.{type_}{axis}", lock=True, **additional_kwargs)

    def unlock_transform_attributes(self, hide=False) -> None:
        """
        Unlocks the nine scalar transform channels on this node — translateX/Y/Z,
        rotateX/Y/Z, scaleX/Y/Z — reversing ``lock_transform_attributes``.
        Does not touch visibility, nor the parent compound
        translate/rotate/scale attributes themselves.
        """
        for type_ in ["t", "r", "s"]:
            for axis in ["x", "y", "z"]:
                cmds.setAttr(f"{self.item.full_name()}.{type_}{axis}", lock=False)
                try:
                    cmds.setAttr(f"{self.item.full_name()}.{type_}{axis}", channelBox=not hide)
                except: pass

    # ------------------------------------------------------------------
    # DAG path and hierarchy
    # ------------------------------------------------------------------

    def dag_path(self) -> om.MDagPath:
        """
        Returns the MDagPath of this node. For an instanced node this is
        the path of the first instance.
        """
        return self._dag_node.getPath()

    def root(self) -> mref.ReferencedItem:
        """
        Returns the top-most ancestor of this node (the node directly
        under the scene root), or this node itself if it has no parent.
        """
        full_name = self.item.full_name()
        return mref.get("|" + full_name.lstrip("|").split("|")[0])

    def siblings(self, include_shapes: bool = True) -> mref.ReferenceList:
        """
        Returns the other children of this node's parent, not including
        this node. For a node at the scene root this is the other
        top-level nodes (including the default cameras).

        :param include_shapes: If False, shape nodes are skipped.
        """
        parent = self.parent()
        if parent:
            candidates = cmds.listRelatives(parent.full_name(), children=True, fullPath=True) or []
        else:
            candidates = cmds.ls(assemblies=True, long=True) or []

        return mref.ReferenceList(
            mref.get(node)
            for node in candidates
            if node != self.item.full_name()
            if include_shapes or not cmds.objectType(node, isAType="shape")
        )

    def instance_count(self) -> int:
        """
        Returns the number of DAG paths to this node — 1 for a node that
        is not instanced. Includes indirect instancing (an instanced
        parent).
        """
        return self._dag_node.instanceCount(True)

    def is_instanced(self) -> bool:
        """
        Returns True if this node can be reached by more than one DAG
        path, either directly or through an instanced parent.
        """
        return self._dag_node.isInstanced(True)

    # ------------------------------------------------------------------
    # Visibility and display
    # ------------------------------------------------------------------

    def is_visible(self) -> bool:
        """
        Returns True if this node is actually drawn — i.e. it and all of
        its parents are visible (taking ``visibility``, ``lodVisibility``,
        drawing overrides and intermediate state into account). This
        differs from reading the ``visibility`` attribute, which ignores
        the parents.
        """
        return self.dag_path().isVisible()

    def show(self) -> None:
        """
        Sets this node's ``visibility`` attribute on. Parents that are
        hidden will still hide it — see ``is_visible``.
        """
        cmds.setAttr(f"{self.item.full_name()}.visibility", True)

    def hide(self) -> None:
        """
        Sets this node's ``visibility`` attribute off.
        """
        cmds.setAttr(f"{self.item.full_name()}.visibility", False)

    def world_matrix(self, inverse: bool = False) -> list[float]:
        """
        Returns the world-space matrix of this node as a flat list of 16
        floats, read directly from the DAG path. Works for shapes as well
        as transforms (a shape returns its transform's world matrix).

        :param inverse: If True, returns the inverse world matrix.
        """
        path = self.dag_path()
        matrix = path.inclusiveMatrixInverse() if inverse else path.inclusiveMatrix()
        return list(matrix)

    def outliner_colour(self) -> tuple[float, float, float]|None:
        """
        Returns the custom outliner colour as an ``(r, g, b)`` tuple, or
        None if the node does not use a custom outliner colour.
        """
        if not cmds.getAttr(f"{self.item.full_name()}.useOutlinerColor"):
            return None
        return tuple(cmds.getAttr(f"{self.item.full_name()}.outlinerColor")[0])

    def set_outliner_colour(self, colour: "tuple[float, float, float]|None") -> None:
        """
        Sets the colour this node's name is drawn with in the outliner,
        as ``(r, g, b)`` floats in the 0-1 range. Pass None to go back to
        the default colour.
        """
        if colour is None:
            cmds.setAttr(f"{self.item.full_name()}.useOutlinerColor", False)
            return

        cmds.setAttr(f"{self.item.full_name()}.useOutlinerColor", True)
        cmds.setAttr(f"{self.item.full_name()}.outlinerColor", *colour, type="float3")

    def display_override(self) -> str:
        """
        Returns the drawing-override display type of this node:
        ``"normal"``, ``"template"`` or ``"reference"`` (unselectable).
        Returns ``"normal"`` when drawing overrides are not enabled.
        """
        if not cmds.getAttr(f"{self.item.full_name()}.overrideEnabled"):
            return "normal"
        index = cmds.getAttr(f"{self.item.full_name()}.overrideDisplayType")
        return _DISPLAY_OVERRIDE_TYPES[index]

    def set_display_override(self, display_type: str) -> None:
        """
        Sets the drawing-override display type of this node to
        ``"normal"``, ``"template"`` or ``"reference"`` (unselectable).
        Setting template or reference enables drawing overrides; setting
        normal leaves ``overrideEnabled`` alone so that any override
        colour set on the node is kept.
        """
        if display_type not in _DISPLAY_OVERRIDE_TYPES:
            raise ValueError(
                f"Unsupported display type {display_type!r}; "
                f"expected one of {_DISPLAY_OVERRIDE_TYPES}"
            )

        if display_type != "normal":
            cmds.setAttr(f"{self.item.full_name()}.overrideEnabled", True)

        cmds.setAttr(
            f"{self.item.full_name()}.overrideDisplayType",
            _DISPLAY_OVERRIDE_TYPES.index(display_type),
        )
