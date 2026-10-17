import mref
from maya import cmds
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as oma


# -- Enum values of skinCluster.normalizeWeights and .skinningMethod
_NORMALIZATION_MODES = ["none", "interactive", "post"]
_SKINNING_METHODS = ["linear", "dual_quaternion", "blended"]


def _enum_index(value: str|int, options: list[str]) -> int:
    """
    Resolves an enum given as either its index or its name in options.
    """
    if isinstance(value, int):
        return value
    if value not in options:
        raise ValueError(f"{value!r} is not one of {options}")
    return options.index(value)


class SkinCluster(mref.Trait):
    """
    Trait bound to any node with ``MFn.kSkinClusterFilter``. Provides
    influence enumeration, fast bulk weight read/write via the OpenMaya
    MFnSkinCluster API, influence management, and access to the shapes
    being driven. Also exposes single-influence / single-component
    weights, weight maintenance (max influences, pruning, normalisation),
    the skinning method, and the bind pose.
    """

    # -- Sits above the generic GeometryFilter trait
    priority = 1

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

    # ------------------------------------------------------------------
    # Influence management
    # ------------------------------------------------------------------

    def remove_influence(self, influence: mref.ReferencedItem|str) -> None:
        """
        Removes the given influence from this skin cluster. Maya
        redistributes (normalises) the removed influence's weight across
        the remaining influences.
        """
        influence = mref.get(influence)
        cmds.skinCluster(
            self.item.full_name(),
            edit=True,
            removeInfluence=influence.full_name(),
        )

    def unused_influences(self) -> mref.ReferenceList:
        """
        Returns the influences which carry no weight on any component
        of the skinned shape. Read with a single bulk ``getWeights`` call.
        """
        shape = self.shape()
        dag_paths = self._skin_cluster.influenceObjects()
        if not shape or not dag_paths:
            return mref.ReferenceList()

        component_count, component_mobject = self._build_components(shape)
        if component_count == 0:
            return mref.ReferenceList(mref.get(dag.node()) for dag in dag_paths)

        all_weights, influence_count = self._skin_cluster.getWeights(
            om.MDagPath.getAPathTo(shape.pointer()),
            component_mobject,
        )

        # -- Component-major layout: sum each influence's column
        totals = [0.0] * influence_count
        for flat_index, weight in enumerate(all_weights):
            totals[flat_index % influence_count] += weight

        return mref.ReferenceList(
            mref.get(dag_paths[i].node())
            for i in range(influence_count)
            if totals[i] <= 1e-9
        )

    def remove_unused_influences(self) -> mref.ReferenceList:
        """
        Removes every influence which carries no weight (see
        :meth:`unused_influences`) and returns the removed influences.
        """
        unused = self.unused_influences()
        for influence in unused:
            self.remove_influence(influence)
        return unused

    # ------------------------------------------------------------------
    # Weights - single influence / single component
    # ------------------------------------------------------------------

    def influence_weights(self, influence: mref.ReferencedItem|str) -> list[float]:
        """
        Returns the per-component weights of a single influence on the
        skinned shape, in component order.
        """
        shape = self.shape()
        if not shape:
            return []

        component_count, component_mobject = self._build_components(shape)
        if component_count == 0:
            return []

        return list(
            self._skin_cluster.getWeights(
                om.MDagPath.getAPathTo(shape.pointer()),
                component_mobject,
                self._influence_position(influence),
            )
        )

    def set_influence_weights(
            self,
            influence: mref.ReferencedItem|str,
            weights: list[float],
            normalize: bool = True,
    ) -> None:
        """
        Sets the per-component weights of a single influence in one
        ``MFnSkinCluster.setWeights`` call. ``weights`` must have exactly
        one entry per component.

        :param normalize: If True (default), the other influences on each
            component are scaled so the component still sums to 1.
        """
        shape = self.shape()
        if not shape:
            raise RuntimeError(f"{self.item.name()} is not deforming any geometry")

        component_count, component_mobject = self._build_components(shape)
        if len(weights) != component_count:
            raise ValueError(
                f"Number of components ({component_count}) does not "
                f"match length of weights ({len(weights)})"
            )

        self._skin_cluster.setWeights(
            om.MDagPath.getAPathTo(shape.pointer()),
            component_mobject,
            om.MIntArray([self._influence_position(influence)]),
            om.MDoubleArray(weights),
            normalize,
        )

    def component_weights(self, index: int) -> dict:
        """
        Returns the weights of a single component (vertex / CV) as a dict
        of ``{influence_name: weight}``. Only influences with a non-zero
        weight are included. For NURBS surfaces ``index`` is the flattened
        ``u * numCVsInV + v`` index used by ``weights()``.
        """
        shape = self.shape()
        if not shape:
            return {}

        component_mobject = self._single_component(shape, index)
        values, influence_count = self._skin_cluster.getWeights(
            om.MDagPath.getAPathTo(shape.pointer()),
            component_mobject,
        )

        dag_paths = self._skin_cluster.influenceObjects()
        return {
            om.MFnDependencyNode(dag_paths[i].node()).name(): values[i]
            for i in range(influence_count)
            if values[i] > 0.0
        }

    def set_component_weights(self, index: int, weights: dict, normalize: bool = True) -> None:
        """
        Sets the weights of a single component (vertex / CV) from a dict
        of ``{influence: weight}``, as returned by
        :meth:`component_weights`. Influences not named in the dict are
        set to zero on that component, so the dict fully describes it.

        :param normalize: If True (default), the given weights are
            normalised to sum to 1.
        """
        shape = self.shape()
        if not shape:
            raise RuntimeError(f"{self.item.name()} is not deforming any geometry")

        influence_count = len(self._skin_cluster.influenceObjects())
        values = [0.0] * influence_count
        for influence, weight in weights.items():
            values[self._influence_position(influence)] = weight

        self._skin_cluster.setWeights(
            om.MDagPath.getAPathTo(shape.pointer()),
            self._single_component(shape, index),
            om.MIntArray(list(range(influence_count))),
            om.MDoubleArray(values),
            normalize,
        )

    def copy_weights_to(
            self,
            skin_cluster: mref.ReferencedItem|str,
            surface_association: str = "closestPoint",
            influence_association: tuple = ("name", "closestJoint"),
    ) -> None:
        """
        Copies this skin's weights onto another skin cluster using
        ``copySkinWeights``. Any of this skin's influences missing from
        the destination are added to it first, as ``copySkinWeights``
        only transfers onto influences already present.
        """
        destination = mref.get(skin_cluster)
        destination_name = destination.full_name()

        existing = set(cmds.ls(
            cmds.skinCluster(destination_name, query=True, influence=True) or [],
            long=True,
        ))
        for dag_path in self._skin_cluster.influenceObjects():
            if dag_path.fullPathName() not in existing:
                cmds.skinCluster(
                    destination_name,
                    edit=True,
                    addInfluence=dag_path.fullPathName(),
                    weight=0.0,
                )

        cmds.copySkinWeights(
            sourceSkin=self.item.full_name(),
            destinationSkin=destination_name,
            noMirror=True,
            surfaceAssociation=surface_association,
            influenceAssociation=list(influence_association),
        )

    # ------------------------------------------------------------------
    # Weight maintenance
    # ------------------------------------------------------------------

    def max_influences(self) -> int:
        """
        Returns the maximum number of influences allowed per component.
        """
        return cmds.getAttr(f"{self.item.full_name()}.maxInfluences")

    def set_max_influences(self, value: int, maintain: bool = True) -> None:
        """
        Sets the maximum number of influences per component, and whether
        Maya should enforce it while weights are edited
        (``maintainMaxInfluences``). Existing weights that already exceed
        the limit are not altered.
        """
        skin = self.item.full_name()
        cmds.setAttr(f"{skin}.maxInfluences", value)
        cmds.setAttr(f"{skin}.maintainMaxInfluences", maintain)

    def prune_weights(self, threshold: float = 0.01) -> None:
        """
        Zeroes every weight below ``threshold`` on the skinned shape and
        renormalises the remaining weights (``skinPercent -pruneWeights``).
        """
        shape = self.shape()
        if shape:
            cmds.skinPercent(self.item.full_name(), shape.full_name(), pruneWeights=threshold)

    def normalize_weights(self) -> None:
        """
        Forces every component's weights to sum to 1, regardless of the
        current normalisation mode.
        """
        cmds.skinCluster(self.item.full_name(), edit=True, forceNormalizeWeights=True)

    def normalization_mode(self) -> str:
        """
        Returns the weight normalisation mode: ``"none"``,
        ``"interactive"`` or ``"post"``.
        """
        return _NORMALIZATION_MODES[cmds.getAttr(f"{self.item.full_name()}.normalizeWeights")]

    def set_normalization_mode(self, mode: str|int) -> None:
        """
        Sets the weight normalisation mode from ``"none"``,
        ``"interactive"``, ``"post"`` or the equivalent enum index.
        """
        cmds.setAttr(
            f"{self.item.full_name()}.normalizeWeights",
            _enum_index(mode, _NORMALIZATION_MODES),
        )

    def skinning_method(self) -> str:
        """
        Returns the skinning method: ``"linear"``, ``"dual_quaternion"``
        or ``"blended"`` (weight blended).
        """
        return _SKINNING_METHODS[cmds.getAttr(f"{self.item.full_name()}.skinningMethod")]

    def set_skinning_method(self, method: str|int) -> None:
        """
        Sets the skinning method from ``"linear"``, ``"dual_quaternion"``,
        ``"blended"`` or the equivalent enum index.
        """
        cmds.setAttr(
            f"{self.item.full_name()}.skinningMethod",
            _enum_index(method, _SKINNING_METHODS),
        )

    # ------------------------------------------------------------------
    # Bind pose
    # ------------------------------------------------------------------

    def bind_pose(self) -> mref.ReferencedItem|None:
        """
        Returns the dagPose node storing this skin's bind pose, or None
        if it has none.
        """
        poses = cmds.listConnections(
            f"{self.item.full_name()}.bindPose",
            source=True,
            destination=False,
        ) or []
        return mref.get(poses[0]) if poses else None

    def go_to_bind_pose(self) -> None:
        """
        Restores the influences to this skin's bind pose.

        :raises RuntimeError: If the skin cluster has no bind pose.
        """
        pose = self.bind_pose()
        if not pose:
            raise RuntimeError(f"{self.item.name()} has no bind pose")
        cmds.dagPose(pose.full_name(), restore=True)

    def unbind(self) -> None:
        """
        Unbinds the skin, deleting this skin cluster and leaving the
        geometry in its undeformed state. This ReferencedItem is no
        longer valid afterwards.
        """
        cmds.skinCluster(self.item.full_name(), edit=True, unbind=True)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _influence_position(self, influence: mref.ReferencedItem|str) -> int:
        """
        Returns the position of the given influence within
        ``influenceObjects()`` — the index ``getWeights`` and
        ``setWeights`` expect.
        """
        influence = mref.get(influence)
        target = influence.pointer()
        for position, dag_path in enumerate(self._skin_cluster.influenceObjects()):
            if dag_path.node() == target:
                return position
        raise ValueError(f"{influence.name()} is not an influence of {self.item.name()}")

    @staticmethod
    def _single_component(shape: mref.ReferencedItem, index: int) -> om.MObject:
        """
        Returns a component MObject for the single component at the given
        flattened index on a mesh, nurbsCurve or nurbsSurface.
        """
        shape_type = cmds.nodeType(shape.full_name())

        if shape_type in ("mesh", "nurbsCurve"):
            component_type = om.MFn.kMeshVertComponent if shape_type == "mesh" else om.MFn.kCurveCVComponent
            component_fn = om.MFnSingleIndexedComponent()
            component_mobject = component_fn.create(component_type)
            component_fn.addElement(index)
            return component_mobject

        if shape_type == "nurbsSurface":
            num_v = om.MFnNurbsSurface(om.MDagPath.getAPathTo(shape.pointer())).numCVsInV
            component_fn = om.MFnDoubleIndexedComponent()
            component_mobject = component_fn.create(om.MFn.kSurfaceCVComponent)
            component_fn.addElement(index // num_v, index % num_v)
            return component_mobject

        raise TypeError(f"Unsupported skinned shape type: {shape_type}")

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