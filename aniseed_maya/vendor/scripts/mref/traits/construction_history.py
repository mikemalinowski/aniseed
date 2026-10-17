import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- MFn types which identify construction-history nodes:
# --   kPolyCreator  - polyCreator: polyCube, polyPlane, polyUnite, ...
# --   kMidModifier  - polyModifier: polyExtrudeFace, polySmoothFace, polyBevel3, ...
# --   kCreate       - abstractBaseCreate: makeNurbSphere, makeNurbCircle, loft, revolve, extrude, ...
_HISTORY_FN_TYPES = (
    om.MFn.kPolyCreator,
    om.MFn.kMidModifier,
    om.MFn.kCreate,
)

# -- Typed-attribute data types which carry geometry between nodes
_GEOMETRY_DATA_TYPES = frozenset((
    om.MFnData.kMesh,
    om.MFnData.kNurbsCurve,
    om.MFnData.kNurbsSurface,
    om.MFnData.kSubdSurface,
))


class ConstructionHistory(mref.Trait):
    """
    Trait bound to Maya's poly and NURBS construction-history nodes —
    any node with ``MFn.kPolyCreator`` (``polyCreator``: polyCube,
    polyPlane, polyUnite, ...), ``MFn.kMidModifier`` (``polyModifier``:
    polyExtrudeFace, polySmoothFace, polyBevel3, ...) or ``MFn.kCreate``
    (``abstractBaseCreate``: makeNurbSphere, makeNurbCircle, loft,
    revolve, extrude, ...). Deformers are not construction history in
    this sense and are handled by ``GeometryFilter``.

    Exposes the geometry flowing in and out of the node, the shapes it
    ultimately feeds, the rest of the history chain it is part of,
    enabling / disabling it, and baking history out of the shapes it
    feeds while keeping their deformers.

    Geometry connections are found by attribute type: a connection
    counts if either end is a typed mesh / NURBS curve / NURBS surface /
    subdiv attribute, or both ends are generic attributes (groupParts,
    deformer input / output geometry). Message, matrix and numeric
    connections are ignored.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dependency_node = om.MFnDependencyNode(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if not isinstance(pointer, om.MObject):
            return False
        return any(pointer.hasFn(fn_type) for fn_type in _HISTORY_FN_TYPES)

    def geometry_inputs(self) -> mref.ReferenceList:
        """
        Returns the nodes directly feeding geometry into this node — the
        upstream history node or shape. Creator nodes with no geometry
        input (polyCube, makeNurbSphere, ...) return an empty list.
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in _geometry_neighbours(self._pointer, upstream=True)
        )

    def geometry_outputs(self) -> mref.ReferenceList:
        """
        Returns the nodes this node directly feeds geometry into — the
        next history node, deformer or shape downstream.
        """
        return mref.ReferenceList(
            mref.get(node)
            for node in _geometry_neighbours(self._pointer, upstream=False)
        )

    def output_shapes(self, include_intermediate: bool = False) -> mref.ReferenceList:
        """
        Returns the shapes this node's geometry ends up in. The geometry
        is followed downstream through other history nodes, deformers and
        intermediate (original) shapes until a visible shape is reached,
        so for a deformed mesh this is the final deformed shape. Pass
        ``include_intermediate=True`` to also include any intermediate
        shapes passed along the way.
        """
        results = mref.ReferenceList()
        visited = set()
        pending = list(_geometry_neighbours(self._pointer, upstream=False))

        while pending:
            node = pending.pop(0)

            handle = om.MObjectHandle(node).hashCode()
            if handle in visited:
                continue
            visited.add(handle)

            if node.hasFn(om.MFn.kShape):
                intermediate = om.MFnDagNode(node).isIntermediateObject
                if not intermediate or include_intermediate:
                    results.append(mref.get(node))

                # -- A visible shape is the end of the line. Geometry leaving
                # -- it (e.g. outMesh driving a wrap) belongs to something else.
                if not intermediate:
                    continue

            pending.extend(_geometry_neighbours(node, upstream=False))

        return results

    def upstream_history(self) -> mref.ReferenceList:
        """
        Returns the construction-history nodes upstream of this one in
        the same chain, nearest first, stopping at the first shape. For
        ``polyCube -> polyExtrudeFace -> polyBevel3`` the bevel returns
        ``[polyExtrudeFace, polyCube]``.
        """
        return self._history_chain(upstream=True)

    def downstream_history(self) -> mref.ReferenceList:
        """
        Returns the construction-history nodes downstream of this one in
        the same chain, nearest first, stopping at the first shape. For
        ``polyCube -> polyExtrudeFace -> polyBevel3`` the cube returns
        ``[polyExtrudeFace, polyBevel3]``.
        """
        return self._history_chain(upstream=False)

    def is_enabled(self) -> bool:
        """
        Returns True if this node is contributing to the geometry, or
        False if its ``nodeState`` has been set to "Has No Effect" (or
        any other non-normal state).
        """
        return cmds.getAttr(f"{self.item.full_name()}.nodeState") == 0

    def set_enabled(self, state: bool) -> None:
        """
        Enables or disables this node. Disabling sets ``nodeState`` to
        "Has No Effect", so a modifier passes its input geometry through
        unchanged — useful to preview geometry without an operation
        without deleting it.
        """
        cmds.setAttr(f"{self.item.full_name()}.nodeState", 0 if state else 1)

    def bake_history_on_outputs(self) -> mref.ReferenceList:
        """
        Bakes the construction history of every shape this node feeds
        (see :meth:`output_shapes`) into the shape, then removes the
        history. This affects the whole non-deformer history of those
        shapes, not only this node, and this node itself is typically
        deleted as a result.

        Unlike ``cmds.delete(constructionHistory=True)`` this is safe on
        deformed geometry: deformers (skin clusters, blendshapes, ...)
        are kept and keep working, only the modelling history beneath
        them is baked. Returns the shapes that were baked.
        """
        shapes = self.output_shapes()

        for shape in shapes:
            name = shape.full_name()
            history = cmds.listHistory(name, pruneDagObjects=True) or []

            if cmds.ls(history, type="geometryFilter"):
                cmds.bakePartialHistory(name, prePostDeformers=True)
            else:
                cmds.delete(name, constructionHistory=True)

        return shapes

    def _history_chain(self, upstream: bool) -> mref.ReferenceList:
        """
        Walks geometry connections in the given direction, collecting
        construction-history nodes until a shape is reached.
        """
        results = mref.ReferenceList()
        visited = {om.MObjectHandle(self._pointer).hashCode()}
        pending = list(_geometry_neighbours(self._pointer, upstream=upstream))

        while pending:
            node = pending.pop(0)

            handle = om.MObjectHandle(node).hashCode()
            if handle in visited:
                continue
            visited.add(handle)

            if node.hasFn(om.MFn.kShape):
                continue

            if self.can_bind(node):
                results.append(mref.get(node))

            pending.extend(_geometry_neighbours(node, upstream=upstream))

        return results


def _plug_kind(plug: om.MPlug) -> str|None:
    """
    Returns ``"geometry"`` if the plug is a typed geometry attribute,
    ``"generic"`` if it is a generic attribute (which Maya uses for
    geometry on groupParts, deformers, loft inputs and so on), or None.
    """
    attribute = plug.attribute()

    if attribute.hasFn(om.MFn.kTypedAttribute):
        if om.MFnTypedAttribute(attribute).attrType() in _GEOMETRY_DATA_TYPES:
            return "geometry"
        return None

    if attribute.hasFn(om.MFn.kGenericAttribute):
        return "generic"

    return None


def _is_geometry_connection(source: om.MPlug, destination: om.MPlug) -> bool:
    """
    Returns True if the connection between the two plugs carries
    geometry: either end is a typed geometry attribute, or both ends are
    generic attributes (e.g. ``groupParts.outputGeometry`` into
    ``skinCluster.input[0].inputGeometry``).
    """
    kinds = (_plug_kind(source), _plug_kind(destination))
    return "geometry" in kinds or kinds == ("generic", "generic")


def _geometry_neighbours(node: om.MObject, upstream: bool) -> list[om.MObject]:
    """
    Returns the nodes connected to the given node by geometry-carrying
    connections, either upstream (feeding it) or downstream (fed by it),
    in connection order and without duplicates.
    """
    results = []
    seen = set()

    for plug in om.MFnDependencyNode(node).getConnections():

        if upstream:
            if not plug.isDestination:
                continue
            source = plug.source()
            if source.isNull or not _is_geometry_connection(source, plug):
                continue
            neighbours = [source.node()]

        else:
            if not plug.isSource:
                continue
            neighbours = [
                destination.node()
                for destination in plug.destinations()
                if _is_geometry_connection(plug, destination)
            ]

        for neighbour in neighbours:
            handle = om.MObjectHandle(neighbour).hashCode()
            if handle not in seen:
                seen.add(handle)
                results.append(neighbour)

    return results
