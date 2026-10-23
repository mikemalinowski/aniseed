import logging

import aniseed
import aniseed_toolkit
from maya import cmds

log = logging.getLogger(__name__)


def _rig_path(node: str) -> str:
    """
    Returns the full DAG path of the aniseed rig node the given node belongs
    to (the closest node in its hierarchy with an aniseed_rig attribute), or an
    empty string if it is not part of an aniseed rig. Full paths are used so
    rigs without a namespace, whose top nodes may share a name, stay distinct.

    Args:
        node: Any node within a rig.

    Returns:
        The rig node's full DAG path, or an empty string.
    """
    parts = cmds.ls(node, long=True)[0].split("|")

    for idx in range(len(parts) - 1, 0, -1):
        path = "|".join(parts[:idx + 1])
        if cmds.objExists(f"{path}.aniseed_rig"):
            return path
    return ""


def _rig_controls(namespace: str = "") -> list[str] | None:
    """
    Returns the controls of the rig to work on:

      * the rig in the given namespace, if one is given
      * otherwise the rig the first selected node belongs to
      * otherwise every aniseed rig in the scene

    Rigs with or without a namespace are both supported.

    Args:
        namespace: Optional namespace of the rig, used instead of the
            selection when given.

    Returns:
        The control names, or None if the selection is not part of an
        aniseed rig.
    """
    controls = aniseed_toolkit.rig.controls.all_controls()

    # -- An explicit namespace wins. Match on the whole namespace (with its
    # -- colon), so RIG_1 does not also pick up RIG_10
    if namespace:
        prefix = namespace.rstrip(":") + ":"
        return [
            control
            for control in controls
            if control.split("|")[-1].startswith(prefix)
        ]

    # -- Otherwise use the rig the selection belongs to, found through the
    # -- DAG rather than the name, so rigs without a namespace work too
    selection = cmds.ls(selection=True)
    if selection:
        rig_path = _rig_path(selection[0])
        if not rig_path:
            return None

        return [
            control
            for control in controls
            if cmds.ls(control, long=True)[0].startswith(f"{rig_path}|")
        ]

    return controls


class SelectControls(aniseed_toolkit.Tool):

    identifier = "Select Controls"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, namespace: str = ""):
        """
        Selects every control of a rig: the rig the first selected node
        belongs to, or every aniseed rig in the scene if nothing is selected.
        Rigs with or without a namespace are both supported.

        Args:
            namespace: Optional namespace of the rig to select, used instead
                of the selection when given.

        Returns:
            None
        """
        controls = _rig_controls(namespace)

        if controls is None:
            cmds.warning("The selection is not part of an aniseed rig")
            return

        cmds.select(controls)


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
        for control in cmds.ls(sl=True):
            control = aniseed_toolkit.run("Get Control", control)

            if not control:
                continue

            aniseed_toolkit.run("Zero Control", control.ctl)

            if key_on_reset:
                cmds.setKeyframe(control.ctl)


class ZeroRig(aniseed_toolkit.Tool):

    identifier = "Zero Rig"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, key_on_reset: bool = False, namespace: str = ""):
        """
        Zero out all the animatable channels on every control of a rig: the
        rig the first selected node belongs to, or every aniseed rig in the
        scene if nothing is selected. Rigs with or without a namespace are
        both supported.

        Args:
            key_on_reset: If True, the controls are keyed after being reset.
            namespace: Optional namespace of the rig to zero, used instead of
                the selection when given.

        Returns:
            None
        """
        controls = _rig_controls(namespace)

        if controls is None:
            cmds.warning("The selection is not part of an aniseed rig")
            return

        for control in controls:
            aniseed_toolkit.run("Zero Control", control)

            if key_on_reset:
                cmds.setKeyframe(control)



class SelectOpposite(aniseed_toolkit.Tool):

    identifier = "Select Opposite"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self):
        """
        This will select the controls of the opposing location (side) to the
        selected controls. Opposites which do not exist are skipped.
        """
        selection = cmds.ls(selection=True)

        if not selection:
            log.warning("Select the controls to find the opposites of")
            return

        opposites = [
            opposite
            for opposite in aniseed_toolkit.run("Get Opposites", selection)
            if cmds.objExists(opposite)
        ]

        if not opposites:
            log.warning("No opposite controls were found for the selection")
            return

        cmds.select(opposites)


class GetSelectedRigs(aniseed_toolkit.Tool):

    identifier = "Get Selected Rigs"
    classification = "Animation"
    user_facing = False

    def run(self):
        """
        This will return a list of aniseed Rig instances based on the selection.
        """
        selected_rigs = []

        for selected in cmds.ls(sl=True):
            rig_node = aniseed_toolkit.run("Resolve Rig Node", selected)

            if rig_node:
                selected_rigs.append(rig_node)

        selected_rigs = list(set(selected_rigs))

        return [
            aniseed.Rig.for_host(rig)
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
        for attribute_name in cmds.listAttr(node, k=True) or list():

            if "scale" in attribute_name:
                value = 1.0

            elif "translate" in attribute_name or "rotate" in attribute_name:
                value = 0.0

            else:
                continue

            # -- Locked or connected channels cannot be reset, and are
            # -- left as they are
            try:
                cmds.setAttr(
                    f"{node}.{attribute_name}",
                    value,
                )

            except RuntimeError:
                pass

        for attribute_name in cmds.listAttr(node, k=True, ud=True) or list():
            default_value = cmds.attributeQuery(
                attribute_name,
                node=node,
                listDefault=True,
            )

            if not default_value:
                continue

            # -- Locked or connected attributes cannot be reset, and are
            # -- left as they are
            try:
                cmds.setAttr(
                    f"{node}.{attribute_name}",
                    *default_value,
                )

            except RuntimeError:
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
        This will select the alternate of every rig control whose name
        contains replace_this: the control with replace_this replaced by
        with_this, where one exists.

        Args:
            node: Unused
            replace_this: The part of the control names to replace
            with_this: The string to replace it with

        Returns:
            None
        """
        alternate_controls = []
        controls = aniseed_toolkit.run("Get Controls")

        for control in controls:

            if not replace_this in control:
                continue

            alternate = control.replace(replace_this, with_this)
            if cmds.objExists(alternate):
                alternate_controls.append(alternate)

        cmds.select(alternate_controls)

class SelectFilteredControls(aniseed_toolkit.Tool):

    identifier = "Select Filtered Controls"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, node: str = "", name_filter="_LF") -> None:
        """
        This will select every rig control whose name contains the given
        filter.

        Args:
            node: Unused
            name_filter: The string the control names must contain

        Returns:
            None
        """
        filtered_controls = []
        controls = aniseed_toolkit.run("Get Controls")

        for control in controls:
            if name_filter in control:
                filtered_controls.append(control)

        cmds.select(filtered_controls)


class SelectControlsByLocation(aniseed_toolkit.Tool):

    identifier = "Select Controls By Location"
    classification = "Animation"
    categories = [
        "Selection",
        "Controls",
    ]

    def run(self, node: str = "") -> None:
        """
        This will select every rig control which shares the location (side)
        of the first selected control.

        Args:
            node: Unused

        Returns:
            None
        """
        cmds.select(aniseed_toolkit.run("Get By Location"))
