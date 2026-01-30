import scribble
import qtility
import aniseed_toolkit
import maya.cmds as mc
import maya.api.OpenMaya as om

AXIS = ["x", "y", "z"]

def _get_mirror_array(axis):

    scale = [
        1,
        1,
        1,
    ]

    scale[AXIS.index(axis.lower())] = -1

    return scale


class MirrorShape(aniseed_toolkit.Tool):

    identifier = "Mirror Shape"
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(self, nodes: list[str] = None, axis: str = "") -> None:
        """
        This will mirror the shapes for a given node across a specific axis (x, y, z)

        Args:
            nodes: List of nodes to perform the mirror on
            axis: What axis should be mirrored (x, y, z)

        Returns: None
        """
        if not nodes:
            nodes = mc.ls(sl=True)

        if isinstance(nodes, str):
            nodes = [nodes]

        if not axis:
            axis = qtility.request.item(
                items=AXIS,
                title="Select Mirror Axis",
                message="Select Mirror Axis.",
            )

        if not axis:
            return

        for node in nodes:
            curves = mc.listRelatives(node, type="nurbsCurve")

            if not curves:
                return

            scale = _get_mirror_array(axis)

            for curve in curves:
                mc.xform(
                    f"{curve}.cv[:]",
                    scale=scale,
                )


class AutoMirrorShapes(aniseed_toolkit.Tool):

    identifier = "Mirror All Shapes Across"
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(self, mapping: str = "_LF:_RT", axis="x"):

        from_tag = mapping.split(":")[0]
        to_tag = mapping.split(":")[1]

        for control in aniseed_toolkit.run("Get Controls"):
            if from_tag not in control:
                continue

            to_node = control.replace(from_tag, to_tag)

            if not mc.objExists(to_node):
                continue

            aniseed_toolkit.run(
                "Mirror Across",
                from_node=control,
                to_node=to_node,
                axis=axis,
            )


class MirrorAcross(aniseed_toolkit.Tool):

    identifier = "Mirror Across"
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(self, from_nodes: str = "", to_nodes: str = "", axis: str = ""):
        """
        This will attempt to mirror (globally) the shape from the from_node to the
        to_node across the specified axis.

        Args:
            from_node: What node should be the mirror from
            to_node: What node should be the mirror to
            axis: What axis should be mirrored (x, y, z)

        Returns:
            None
        """
        if not from_nodes:
            from_nodes = mc.ls(sl=True)
        elif isinstance(from_nodes, str):
            from_nodes = [from_nodes]

        if to_nodes and isinstance(to_nodes, str):
            to_nodes = [to_nodes]

        if not to_nodes:
            to_nodes = []
        if not axis:
            axis = qtility.request.item(
                items=AXIS,
                title="Select Mirror Axis",
                message="Select Mirror Axis.",
                editable=False,
            )

        if not axis:
            return

        if not to_nodes:
            shape_prefs = scribble.get("shape_tools")
            mapping = shape_prefs.get("location_mapping", "_LF:_RT")
            mapping = qtility.request.text(
                title="Select Mirror Location Mapping",
                message="Give a mapping (such as _LF:_RT)",
                text=mapping,
            )
            shape_prefs["location_mapping"] = mapping
            shape_prefs.save()

            if not mapping:
                return

            for from_node in from_nodes:
                to_node = from_node.replace(
                    mapping.split(":")[0].strip(),
                    mapping.split(":")[1].strip(),
                )
                to_nodes.append(to_node)

        if not to_nodes:
            return

        for idx, from_node in enumerate(from_nodes):

            to_node = to_nodes[idx]
            if not mc.objExists(to_node):
                print("Could not find node with name : %s" % to_node)
                continue


            scale = _get_mirror_array(axis)

            # -- Read the shape data from the current side
            shape_data = aniseed_toolkit.run("Read Shape From Node", from_node)

            # -- Clear the shapes on the other side
            shapes_to_remove = mc.listRelatives(
                to_node,
                shapes=True,
            ) or list()

            for shape in shapes_to_remove:
                mc.delete(shape)

            # -- Apply the shapes to that side
            aniseed_toolkit.run("Apply Shape", node=to_node, data=shape_data)

            source_shapes = mc.listRelatives(from_node, shapes=True) or list()
            target_shapes = mc.listRelatives(to_node, shapes=True) or list()

            for shape_idx in range(len(source_shapes)):

                source_shape = source_shapes[shape_idx]
                target_shape = target_shapes[shape_idx]

                source_dag = aniseed_toolkit.run("Get DagPath", source_shape)
                target_dag = aniseed_toolkit.run("Get DagPath", target_shape)

                source_nurbs_fn = om.MFnNurbsCurve(source_dag)
                target_nurbs_fn = om.MFnNurbsCurve(target_dag)

                for cv_idx in range(source_nurbs_fn.numCVs):

                    source_worldspace_cv = source_nurbs_fn.cvPosition(cv_idx, om.MSpace.kWorld)

                    worldspace_vector = om.MVector(source_worldspace_cv)

                    worldspace_vector.x = worldspace_vector.x * scale[0]
                    worldspace_vector.y = worldspace_vector.y * scale[1]
                    worldspace_vector.z = worldspace_vector.z * scale[2]

                    target_nurbs_fn.setCVPosition(
                        cv_idx,
                        om.MPoint(
                            worldspace_vector.x,
                            worldspace_vector.y,
                            worldspace_vector.z,
                        ),
                        space=om.MSpace.kWorld,
                    )

                target_nurbs_fn.updateCurve()