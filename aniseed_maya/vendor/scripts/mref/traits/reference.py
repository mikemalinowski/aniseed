import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- Reference nodes Maya creates for its own bookkeeping. They have
# -- MFn.kReference but are not associated with any file, so every
# -- MFnReference / referenceQuery call on them fails.
_BOOKKEEPING_REFERENCE_NODES = frozenset((
    "sharedReferenceNode",
    "_UNKNOWN_REF_NODE_",
))


class Reference(mref.Trait):
    """
    Trait bound to any node with ``MFn.kReference`` — the reference
    node (``fooRN``) Maya creates for every file reference. Exposes the
    referenced file path, namespace, load state, the nodes the reference
    brings in, nested (parent / child) references and the load, unload,
    reload, replace and remove operations.

    The bookkeeping reference nodes ``sharedReferenceNode`` and
    ``_UNKNOWN_REF_NODE_`` are deliberately not bound, as they are not
    backed by a file and every reference query on them fails.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reference = om.MFnReference(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if not isinstance(pointer, om.MObject) or not pointer.hasFn(om.MFn.kReference):
            return False

        name = om.MFnDependencyNode(pointer).name().split(":")[-1]
        return name not in _BOOKKEEPING_REFERENCE_NODES

    def file_path(self, copy_number: bool = False, resolved: bool = True) -> str:
        """
        Returns the path of the file this reference points to. When the
        same file is referenced more than once Maya suffixes the path
        with a copy number (``scene.ma{1}``); pass ``copy_number=True``
        to keep that suffix. Pass ``resolved=False`` to get the path as
        written in the scene (which may contain environment variables)
        rather than the resolved path.
        """
        return cmds.referenceQuery(
            self.item.full_name(),
            filename=True,
            withoutCopyNumber=not copy_number,
            unresolvedName=not resolved,
        )

    def namespace(self, short: bool = False) -> str:
        """
        Returns the namespace the referenced nodes live in, without a
        leading colon (``char:rig`` for a nested reference). Pass
        ``short=True`` to get only the final namespace (``rig``).
        """
        return self._reference.associatedNamespace(short)

    def is_loaded(self) -> bool:
        """
        Returns True if the referenced file is currently loaded
        """
        return self._reference.isLoaded()

    def load(self) -> None:
        """
        Loads the referenced file. Does nothing if it is already loaded.
        """
        if not self.is_loaded():
            cmds.file(loadReference=self.item.full_name())

    def unload(self) -> None:
        """
        Unloads the referenced file. Does nothing if it is already
        unloaded.
        """
        if self.is_loaded():
            cmds.file(unloadReference=self.item.full_name())

    def reload(self) -> None:
        """
        Reloads the referenced file from disk, picking up any changes
        saved since it was loaded. Loads it if it is currently unloaded.
        """
        cmds.file(loadReference=self.item.full_name())

    def replace_file(self, file_path: str) -> None:
        """
        Swaps the file this reference points to for the given file,
        keeping the reference node, namespace and any reference edits
        which still apply.
        """
        cmds.file(file_path, loadReference=self.item.full_name())

    def contained_nodes(self) -> mref.ReferenceList:
        """
        Returns the nodes brought into the scene by this reference. Nodes
        belonging to nested references are reported by those nested
        reference nodes, not this one. Unloaded references contain no
        nodes.
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in self._reference.nodes()
        )

    def parent_reference(self) -> mref.ReferencedItem|None:
        """
        Returns the reference node this reference is nested within, or
        None if it is a top-level reference.
        """
        parent = self._reference.parentReference()
        if parent.isNull():
            return None
        return mref.get(parent)

    def child_references(self) -> mref.ReferenceList:
        """
        Returns the reference nodes directly nested within this
        reference's file.
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in cmds.referenceQuery(
                self.item.full_name(),
                child=True,
                referenceNode=True,
            ) or []
        )

    def remove(self) -> None:
        """
        Removes this reference from the scene entirely, along with all
        the nodes it brought in and its reference node.
        """
        cmds.file(removeReference=True, referenceNode=self.item.full_name())
