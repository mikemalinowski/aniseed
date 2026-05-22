import mref
from maya import cmds
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as oma


class SkinCluster(mref.Trait):
    """
    Trait bound to any node with ``MFn.kSkinClusterFilter``. Provides
    influence enumeration, fast bulk weight read/write via the OpenMaya
    MFnSkinCluster API, influence management, and access to the shapes
    being driven.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._skin_cluster = oma.MFnSkinCluster(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kSkinClusterFilter)

    def influences(self) -> list[mref.ReferencedItem]:
        """
        Returns a list of influences on the skin cluster, in the same
        order ``MFnSkinCluster`` reports them.
        """
        return [
            mref.get(dag_path.node())
            for dag_path in self._skin_cluster.influenceObjects()
        ]

    def weights(self) -> dict:
        """
        Reads every skin weight in a single API call and returns a
        JSON-serialisable dict of the shape::

            {
                "influences":     [name, ...],
                "weights":        [[float, ...], ...],   # per-influence lists
                "max_influences": int,
            }

        ``weights[i]`` is the per-component weight list for
        ``influences[i]``.
        """
        shape = self.shape()
        if not shape:
            return dict(influences=[], weights=[], max_influences=0)

        component_count, component_mobject = self._build_components(shape)
        if component_count == 0:
            return dict(influences=[], weights=[], max_influences=0)

        shape_dag = om.MDagPath.getAPathTo(shape.pointer())

        all_weights, influence_count = self._skin_cluster.getWeights(
            shape_dag,
            component_mobject,
        )

        influences = [
            om.MFnDependencyNode(dag_path.node()).name()
            for dag_path in self._skin_cluster.influenceObjects()
        ]

        # -- MFnSkinCluster.getWeights returns a flat component-major
        # -- array: [v0_inf0, v0_inf1, ..., v1_inf0, v1_inf1, ...].
        # -- Slice it back into per-influence lists.
        influence_weights = [
            [
                all_weights[c * influence_count + i]
                for c in range(component_count)
            ]
            for i in range(influence_count)
        ]

        return dict(
            influences=influences,
            weights=influence_weights,
            max_influences=cmds.getAttr(f"{self.item.full_name()}.maxInfluences"),
        )

    def set_weights(self, weight_data: dict, normalize: bool = True) -> None:
        """
        Applies skin weights from a dict of the shape returned by
        ``weights()``, in a single ``MFnSkinCluster.setWeights`` call.

        Any influences named in ``weight_data["influences"]`` that are
        not yet on this skin cluster are auto-added via ``add_influence``
        before the weights are applied.

        :param weight_data: Dict with ``"influences"`` (list of names)
            and ``"weights"`` (list of per-influence weight lists).
        :param normalize: If True (default), Maya normalises the applied
            weights per component.
        """
        shape = self.shape()
        if not shape:
            return

        component_count, component_mobject = self._build_components(shape)
        if component_count == 0:
            return

        cluster_influence_names = [
            om.MFnDependencyNode(dag_path.node()).name()
            for dag_path in self._skin_cluster.influenceObjects()
        ]

        # -- Auto-add any influences in the input that aren't on this
        # -- cluster yet, then re-query the cluster's influence list so
        # -- our index map reflects the additions.
        added_any = False
        for name in weight_data["influences"]:
            if name not in cluster_influence_names:
                self.add_influence(name)
                added_any = True

        if added_any:
            cluster_influence_names = [
                om.MFnDependencyNode(dag_path.node()).name()
                for dag_path in self._skin_cluster.influenceObjects()
            ]

        influence_indices = om.MIntArray()
        for name in weight_data["influences"]:
            influence_indices.append(cluster_influence_names.index(name))

        # -- MFnSkinCluster.setWeights expects a flat component-major
        # -- array: [v0_inf0, v0_inf1, ..., v1_inf0, v1_inf1, ...].
        # -- Flatten the per-influence weight lists into that layout.
        num_influences = len(weight_data["influences"])
        all_weights = om.MDoubleArray()
        for c in range(component_count):
            for i in range(num_influences):
                all_weights.append(weight_data["weights"][i][c])

        shape_dag = om.MDagPath.getAPathTo(shape.pointer())
        self._skin_cluster.setWeights(
            shape_dag,
            component_mobject,
            influence_indices,
            all_weights,
            normalize,
        )

    def add_influence(self, influence: mref.ReferencedItem|str, **kwargs) -> None:
        """
        Adds the given influence to this skin cluster.
        """
        influence = mref.get(influence)
        cmds.skinCluster(
            self.item.full_name(),
            edit=True,
            addInfluence=influence.full_name(),
            **kwargs,
        )

    def shape(self) -> mref.ReferencedItem | None:
        """
        Returns the first shape driven by this skin cluster, or None if
        the cluster currently drives no geometry.
        """
        results = cmds.skinCluster(self.item.full_name(), query=True, geometry=True) or []
        if results:
            return mref.get(results[0])
        return None

    def shapes(self) -> list[mref.ReferencedItem]:
        """
        Returns a list of all shapes driven by this skin cluster.
        """
        return [
            mref.get(n)
            for n in cmds.skinCluster(self.item.full_name(), query=True, geometry=True) or []
        ]

    @staticmethod
    def _build_components(shape: mref.ReferencedItem):
        """
        Returns ``(component_count, component_mobject)`` for the given
        shape. Supports ``mesh``, ``nurbsSurface``, and ``nurbsCurve``.
        Returns ``(0, None)`` if the shape isn't a recognised skinnable
        type.
        """
        shape_name = shape.full_name()
        shape_type = cmds.nodeType(shape_name)

        if shape_type == "mesh":
            vertex_count = cmds.polyEvaluate(shape_name, vertex=True)
            indices_fn = om.MFnSingleIndexedComponent()
            component_mobject = indices_fn.create(om.MFn.kMeshVertComponent)
            indices_fn.addElements(list(range(vertex_count)))
            return vertex_count, component_mobject

        if shape_type == "nurbsSurface":
            sel = om.MSelectionList()
            sel.add(shape_name)
            dag_path = sel.getDagPath(0)
            nurbs_fn = om.MFnNurbsSurface(dag_path)
            num_u = nurbs_fn.numCVsInU
            num_v = nurbs_fn.numCVsInV
            comp_fn = om.MFnDoubleIndexedComponent()
            component_mobject = comp_fn.create(om.MFn.kSurfaceCVComponent)
            for u in range(num_u):
                for v in range(num_v):
                    comp_fn.addElement(u, v)
            return num_u * num_v, component_mobject

        if shape_type == "nurbsCurve":
            cv_count = len(cmds.ls(f"{shape_name}.cv[*]", flatten=True))
            indices_fn = om.MFnSingleIndexedComponent()
            component_mobject = indices_fn.create(om.MFn.kCurveCVComponent)
            indices_fn.addElements(list(range(cv_count)))
            return cv_count, component_mobject

        return 0, None