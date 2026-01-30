import aniseed
import aniseed_toolkit
import maya.cmds as mc


class SelectControls(aniseed_toolkit.Tool):

    identifier = "Select Controls"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self):
        """
        This will select all the controls for the given rig (if there is a selection
        or all the controls in all rigs if there is not a selection).
        """
        mc.select(
            aniseed_toolkit.run(
                "Get Controls",
            ),
        )


class ZeroSelection(aniseed_toolkit.Tool):

    identifier = "Zero Selection"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, key_on_reset: bool = False):
        """
        This will zero out all the animatable channels for the selected
        controls.

        Args:
            key_on_reset (bool, optional): If True, the objects will be keyed
                after being reset

        Returns:
            None
        """
        for control in mc.ls(sl=True):
            control = aniseed_toolkit.run("Get Control", control)

            if not control:
                continue

            aniseed_toolkit.run("Zero Control", control.ctl)

            if key_on_reset:
                mc.setKeyframe(control.ctl)


class ZeroRig(aniseed_toolkit.Tool):

    identifier = "Zero Rig"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, key_on_reset: bool = False):
        """
        This will zero out all the animatable channels for the selected
        controls.

        Args:
            key_on_reset (bool, optional): If True, the objects will be keyed
                after being reset

        Returns:
            None
        """

        for control in aniseed_toolkit.run("Get Controls"):
            aniseed_toolkit.run("Zero Control", control)

            if key_on_reset:
                mc.setKeyframe(control)



class SelectOpposite(aniseed_toolkit.Tool):

    identifier = "Select Opposite"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self):
        """
        This will select controls of the opposing location (side)
        """
        mc.select(
            aniseed_toolkit.run("Get Opposites"),
        )


class GetSelectedRigs(aniseed_toolkit.Tool):

    identifier = "Get Selected Rigs"
    classification = "Animation"
    user_facing = False

    def run(self):
        """
        This will return a list of aniseed Rig instances based on the selection.
        """
        selected_rigs = []

        for selected in mc.ls(sl=True):
            rig_node = aniseed_toolkit.run("Resolve Rig Node", selected)

            if rig_node:
                selected_rigs.append(rig_node)

        selected_rigs = list(set(selected_rigs))

        return [
            aniseed.Rig(host=rig)
            for rig in selected_rigs
        ]


class ZeroControl(aniseed_toolkit.Tool):

    identifier = "Zero Control"
    classification = "Animation"
    user_facing = False

    def run(self, node: str = "") -> None:
        """
        This will zero out all the animatable channels for the
        given node

        Args:
            node: The node to zero out (reset)

        Returns:
            None
        """
        for attribute_name in mc.listAttr(node, k=True) or list():

            if "scale" in attribute_name:
                value = 1.0

            elif "translate" in attribute_name or "rotate" in attribute_name:
                value = 0.0

            else:
                continue

            try:
                mc.setAttr(
                    f"{node}.{attribute_name}",
                    value,
                )

            except:
                pass

        for attribute_name in mc.listAttr(node, k=True, ud=True) or list():
            value = mc.attributeQuery(
                attribute_name,
                node=node,
                listDefault=True,
            )

            try:
                mc.setAttr(
                    f"{node}.{attribute_name}",
                    value,
                )

            except:
                continue


class SelectAlternateControls(aniseed_toolkit.Tool):

    identifier = "Select Alternate Controls"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, node: str = "", replace_this="_LF", with_this="_RT") -> None:
        """
        This will zero out all the animatable channels for the
        given node

        Args:
            node: The node to zero out (reset)

        Returns:
            None
        """
        alternate_controls = []
        controls = aniseed_toolkit.run("Get Controls")

        for control in controls:

            if not replace_this in control:
                continue

            alternate = control.replace(replace_this, with_this)
            if mc.objExists(alternate):
                alternate_controls.append(alternate)

        mc.select(alternate_controls)

class SelectFilteredControls(aniseed_toolkit.Tool):

    identifier = "Select Filtered Controls"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, node: str = "", name_filter="_LF") -> None:
        """
        This will zero out all the animatable channels for the
        given node

        Args:
            node: The node to zero out (reset)

        Returns:
            None
        """
        filtered_controls = []
        controls = aniseed_toolkit.run("Get Controls")

        for control in controls:
            if name_filter in control:
                filtered_controls.append(control)

        mc.select(filtered_controls)


class SelectControlsByLocation(aniseed_toolkit.Tool):

    identifier = "Select Controls By Location"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, node: str = "") -> None:
        """
        This will zero out all the animatable channels for the
        given node

        Args:
            node: The node to zero out (reset)

        Returns:
            None
        """
        filtered_controls = []
        mc.select(aniseed_toolkit.run("Get By Location"))
