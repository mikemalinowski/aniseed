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

        return aniseed_toolkit.shapes.mirror(nodes, axis)


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
            from_nodes: What node should be the mirror from
            to_nodes: What node should be the mirror to
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

        return aniseed_toolkit.shapes.mirror_across(
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            axis=axis,
        )