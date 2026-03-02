import mref
from maya import cmds
from maya.api import OpenMaya as om


class DagNode(mref.Trait):

    def __init__(self, *args, **kwargs):
        super(DagNode, self).__init__(*args, **kwargs)

        self._dag_node = om.MFnDagNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer):
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kDagNode):
            return True

    def full_name(self):
        """
        Returns the full path (long) name of the node.
        """
        return self._dag_node.fullPathName()

    def children(self, recursive: bool = False, node_type: str = None) -> list["NodeReference"]:
        """
        Returns a list of all children of the node

        Args:
            recursive (bool, optional): If False (default) only immediate children
                will be returned. If True all children will be returned.
            node_type (str, optional): Only return children of the specified type

        Returns:
            A list of NodeReference objects
        """
        additional_args = dict()

        if recursive:
            additional_args['allDescendents'] = True

        if node_type:
            additional_args['type'] = node_type

        return [
            mref.get(node)
            for node in cmds.listRelatives(self.full_name(), children=True, **additional_args) or []
        ]


    def parent(self) -> "NodeReference":
        """
        This will return the parent node

        Args:
            idx: You may give the index of the parent to return
        """
        parents = cmds.listRelatives(self.full_name(), parent=True, fullPath=True)
        if parents:
            return mref.get(parents[0])

    def all_parents(self) -> list["NodeReference"]:
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


    def set_parent(self, parent: "NodeReference" or om.MObject or str) -> None:
        if not parent:
            cmds.parent(self.full_name(), world=True)
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
        # parent.dag().addChild(self.item.pointer())

    def add_child(self, child):
        child = mref.get(child)
        self._dag_node.addChild(child.pointer())

    def add_children(self, children):
        for child in children:
            self.add_child(child)

    def dag(self):
        return self._dag_node

    def shapes(self):
        return [
            mref.get(shape)
            for shape in cmds.listRelatives(self.full_name(), shapes=True) or []
        ]

    def shape(self):
        try:
            return mref.get(cmds.listRelatives(self.full_name(), shapes=True)[0])
        except IndexError:
            return None
