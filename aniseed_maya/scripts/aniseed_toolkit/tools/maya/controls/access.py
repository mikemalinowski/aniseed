import aniseed
import aniseed_toolkit
import maya.cmds as mc


class GetControls(aniseed_toolkit.Tool):

    identifier = 'Get Controls'
    classification = "Animation"
    user_facing = False

    def run(self):
        """
        This will return the control nodes for all the selected rigs. If no
        rig is selected then all controls in all rigs will be returned.
        """
        rigs = aniseed_toolkit.run(
            "Get Selected Rigs",
        )

        if not rigs:
            rigs = aniseed.Rig.find()

        if not rigs:
            return

        rig_nodes = [
            rig.label
            for rig in rigs
        ]

        results = []

        for control in mc.controller(query=True, allControllers=True):
            rig_node = aniseed_toolkit.run("Resolve Rig Node", control)

            if rig_node in rig_nodes:
                results.append(control)

        return results


class ResolveRigNode(aniseed_toolkit.Tool):

    identifier = "Resolve Rig Node"
    classification = "Animation"
    user_facing = False

    def run(self, node: str = "") -> "str":
        """
        This will attempt to find the rig for the given node

        Args:
            node: The node to attempt to find the rig for

        Returns:
            node name
        """
        full_node_path = mc.ls(node, long=True)[0].split("|")

        for potential_rig_node in reversed(full_node_path):
            if mc.objExists(f"{potential_rig_node}.aniseed_rig"):
                return potential_rig_node

        return ""


class GetRigTool(aniseed_toolkit.Tool):

    identifier = "Get Rig"
    classification = "Animation"
    user_facing = False

    def run(self, node: str = "") -> "aniseed.Rig" or None:
        """
        This will attempt to find the rig for the given node

        Args:
            node: The node to attempt to find the rig for

        Returns:
            node name
        """
        rig_node = aniseed_toolkit.run("Resolve Rig Node", node)

        if not rig_node:
            return None

        return aniseed.Rig(host=rig_node)


class GetOpposite(aniseed_toolkit.Tool):

    identifier = "Get Opposites"
    classification = "Animation"
    user_facing = False
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, controls: list[str] or None = None) -> list[str]:
        """
        This will return the opposite controls for the given controls

        Args:
            controls: List of controls to get the opposites for. If none are
                given then the selection will be used.
        """
        opposites = []
        rig = None

        for control in controls or mc.ls(sl=True):

            control = aniseed_toolkit.run("Get Control", control)

            if not control:
                continue

            # -- Get the rig
            if not rig:
                rig = aniseed_toolkit.run("Get Rig", control.ctl)

            # -- Get the location of the control
            name_decomposition = rig.config().decompose_name(control.ctl)

            # -- Now use the rig's config
            side = rig.config().left
            if name_decomposition["location"] == rig.config().left:
                side = rig.config().right

            name_decomposition["location"] = side
            opposite_control = rig.config().generate_name(
                unique=False,
                **name_decomposition

            )
            opposites.append(opposite_control)

        return opposites
