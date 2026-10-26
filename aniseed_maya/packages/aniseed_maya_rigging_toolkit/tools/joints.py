"""
Rigging Toolkit tools for joints: replicating, reversing, measuring and
rolling joint chains, moving values between rotations and joint orients,
showing or hiding bones, and writing joint hierarchies to (and loading them
from) json files.
"""
import logging
import os

import mref
from maya import cmds

import aniseed
import aniseed_toolkit
from aniseed import toolkits

log = logging.getLogger(__name__)


def _requires_selection(message: str) -> bool:
    if not cmds.ls(selection=True):
        log.warning(message)
        return False

    return True


def _requires_nodes(tool, option_names: list) -> bool:
    """
    Checks that each of the named options is set to a node which exists,
    logging a warning naming the first which is not.
    """
    for option_name in option_names:
        node = tool.option(option_name).get()

        if not node:
            log.warning(f"Set {option_name} to run {tool.identifier}")
            return False

        if not cmds.objExists(node):
            log.warning(f"{option_name} ({node}) does not exist")
            return False

    return True


def _parent_exists(tool) -> bool:
    """
    Checks the (optional) Parent option names a node which exists.
    """
    parent = tool.option("Parent").get()

    if parent and not cmds.objExists(parent):
        log.warning(f"Parent ({parent}) does not exist")
        return False

    return True


def _set_draw_style(joints: list, visible: bool) -> None:
    """
    Shows (draw style 0) or hides (draw style 2) the bones of the given
    nodes. Nodes without a draw style, or whose draw style is locked or
    connected, are left as they are.
    """
    draw_style = 0 if visible else 2

    for joint in joints:
        if joint.has_attribute("drawStyle"):
            try:
                joint.drawStyle.set(draw_style)
            except RuntimeError:
                pass


# --------------------------------------------------------------------------------------
class ReplicateJoint(toolkits.Tool):
    """
    Creates a new joint which copies the transform and joint attributes
    (translate, rotate, scale, joint orient and preferred angle) of Joint,
    parented under Parent (or at the scene root if Parent is not given).

    Worldspace matches the new joint to Joint's world space transform. Link
    connects Joint's attributes to the new joint rather than copying them.
    Copy Local Name names the new joint after Joint (without its namespace).
    """

    identifier = "Replicate Joint"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Joint",
            value="",
            description="The joint to replicate",
        )

        self.declare_option(
            name="Parent",
            value="",
            description="The node to parent the new joint under (the scene root if not given)",
        )

        self.declare_option(
            name="Worldspace",
            value=False,
            description="Whether to match the new joint to the world space transform of the joint",
        )

        self.declare_option(
            name="Link",
            value=False,
            description="Whether to connect the joint's attributes to the new joint rather than copy them",
        )

        self.declare_option(
            name="Copy Local Name",
            value=False,
            description="Whether to name the new joint after the joint (without its namespace)",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Joint", "Parent"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        return _requires_nodes(self, ["Joint"]) and _parent_exists(self)

    def run(self) -> None:
        new_joint = aniseed_toolkit.scene.joints.replicate(
            joint=self.option("Joint").get(),
            parent=self.option("Parent").get(),
            worldspace=self.option("Worldspace").get(),
            link=self.option("Link").get(),
            copy_local_name=self.option("Copy Local Name").get(),
        )
        log.info(f"Created {new_joint}")


# --------------------------------------------------------------------------------------
class CopyJointAttributes(toolkits.Tool):
    """
    Copies the transform and joint attributes (translate, rotate, scale,
    joint orient and preferred angle) of From This onto To This. Turn on
    Link to connect the attributes instead of copying their values.
    """

    identifier = "Copy Joint Attributes"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="From This",
            value="",
            description="The joint to copy the values from",
        )

        self.declare_option(
            name="To This",
            value="",
            description="The joint to copy the values to",
        )

        self.declare_option(
            name="Link",
            value=False,
            description="Whether to connect the attributes rather than copy their values",
        )

    def option_widget(self, option_name: str):
        if option_name in ["From This", "To This"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        return _requires_nodes(self, ["From This", "To This"])

    def run(self) -> None:
        aniseed_toolkit.scene.joints.copy_attributes(
            from_this=self.option("From This").get(),
            to_this=self.option("To This").get(),
            link=self.option("Link").get(),
        )


# --------------------------------------------------------------------------------------
class GetJointsBetween(toolkits.Tool):
    """
    Logs the joints from Start down to End (including both). Only the joints
    directly in the chain between them are included, so Start must be above
    End in the hierarchy.
    """

    identifier = "Get Joints Between"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Start",
            value="",
            description="The highest joint of the chain",
        )

        self.declare_option(
            name="End",
            value="",
            description="The lowest joint of the chain",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Start", "End"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        return _requires_nodes(self, ["Start", "End"])

    def run(self) -> None:
        joints = aniseed_toolkit.scene.joints.get_between(
            self.option("Start").get(),
            self.option("End").get(),
        )
        log.info(f"Joints between: {joints}")


# --------------------------------------------------------------------------------------
class ReplicateChain(toolkits.Tool):
    """
    Replicates the joint chain from From This down to To This (only the
    joints directly between them), copying every joint's attributes, and
    parents the new chain under Parent (or the scene root if not given).

    With World on, the first new joint is matched to the world space
    transform of From This, otherwise it gets the same local values.
    """

    identifier = "Replicate Chain"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="From This",
            value="",
            description="The joint to start replicating from",
        )

        self.declare_option(
            name="To This",
            value="",
            description="The joint to stop replicating at",
        )

        self.declare_option(
            name="Parent",
            value="",
            description="The node to parent the new chain under (the scene root if not given)",
        )

        self.declare_option(
            name="World",
            value=True,
            description="Whether to match the first new joint in world space rather than local space",
        )

    def option_widget(self, option_name: str):
        if option_name in ["From This", "To This", "Parent"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        return _requires_nodes(self, ["From This", "To This"]) and _parent_exists(self)

    def run(self) -> None:
        new_joints = aniseed_toolkit.scene.joints.replicate_chain(
            from_this=self.option("From This").get(),
            to_this=self.option("To This").get(),
            parent=self.option("Parent").get(),
            world=self.option("World").get(),
        )
        log.info(f"Created {new_joints}")


# --------------------------------------------------------------------------------------
class ReverseChain(toolkits.Tool):
    """
    Reverses the hierarchy of the selected joint chain (select the joints
    in order, root to tip), so the tip becomes the root (under the old
    root's parent) and the root becomes the tip.
    """

    identifier = "Reverse Chain"
    toolkit = "Rigging"
    categories = ["Joints"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the joints of the chain to reverse, in order from root to tip")

    def run(self) -> None:
        joints = aniseed_toolkit.scene.joints.reverse_chain(cmds.ls(selection=True))
        log.info(f"Reversed chain: {joints}")


# --------------------------------------------------------------------------------------
class ReplicateEntireChain(toolkits.Tool):
    """
    Replicates Joint Root and every joint below it, copying every joint's
    attributes, and parents the new hierarchy under Parent (or the scene
    root if not given).

    Link connects the original joints' attributes to the new joints rather
    than copying them. Copy Local Name names each new joint after the one it
    replicates (without its namespace).
    """

    identifier = "Replicate Entire Chain"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Joint Root",
            value="",
            description="The joint to replicate, along with every joint below it",
        )

        self.declare_option(
            name="Parent",
            value="",
            description="The node to parent the new hierarchy under (the scene root if not given)",
        )

        self.declare_option(
            name="Link",
            value=False,
            description="Whether to connect the original joints' attributes to the new joints",
        )

        self.declare_option(
            name="Copy Local Name",
            value=False,
            description="Whether to name the new joints after the ones they replicate",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Joint Root", "Parent"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        if not _requires_nodes(self, ["Joint Root"]) or not _parent_exists(self):
            return False

        if not cmds.listRelatives(self.option("Joint Root").get(), allDescendents=True, type="joint"):
            log.warning("Joint Root has no joints below it, use Replicate Joint instead")
            return False

        return True

    def run(self) -> None:
        new_root = aniseed_toolkit.scene.joints.replicate_entire_chain(
            joint_root=self.option("Joint Root").get(),
            parent=self.option("Parent").get(),
            link=self.option("Link").get(),
            copy_local_name=self.option("Copy Local Name").get(),
        )
        log.info(f"Created {new_root}")


# --------------------------------------------------------------------------------------
class GetChainLength(toolkits.Tool):
    """
    Logs the length of the joint chain from Start down to End: the sum of
    the world space distances between each joint and the next.
    """

    identifier = "Get Chain Length"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Start",
            value="",
            description="The joint to start measuring from",
        )

        self.declare_option(
            name="End",
            value="",
            description="The joint to stop measuring at",
        )

    def option_widget(self, option_name: str):
        if option_name in ["Start", "End"]:
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())
        return None

    def is_valid(self) -> bool:
        return _requires_nodes(self, ["Start", "End"])

    def run(self) -> None:
        start = self.option("Start").get()
        end = self.option("End").get()

        length = aniseed_toolkit.scene.joints.chain_length(start=start, end=end)
        log.info(f"Chain length between {start} and {end} is {length}")


# --------------------------------------------------------------------------------------
class LoadJointFileTool(toolkits.Tool):
    """
    Builds the joint hierarchy stored in a json file (written by Write
    Joints File) beneath Root Parent, or beneath the first selected node if
    Root Parent is not given.

    Apply Names gives the new nodes their stored names. Invert inverts the
    translations (useful when mirroring). Worldspace Root applies the stored
    values of each root node as its world space transform.
    """

    identifier = "Load Joints File"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Root Parent",
            value="",
            description="The node to build the hierarchy under (the first selected node if not given)",
        )

        self.declare_option(
            name="Filepath",
            value="",
            description="The json file to load",
        )

        self.declare_option(
            name="Apply Names",
            value=True,
            description="Whether to give the new nodes their stored names",
        )

        self.declare_option(
            name="Invert",
            value=False,
            description="Whether to invert the translations (useful when mirroring)",
        )

        self.declare_option(
            name="Worldspace Root",
            value=False,
            description="Whether to apply the stored values of each root node in world space",
        )

    def option_widget(self, option_name: str):
        if option_name == "Root Parent":
            return aniseed.widgets.ObjectSelector(self.option(option_name).get())

        if option_name == "Filepath":
            return aniseed.widgets.FilepathSelector(
                self.option(option_name).get(),
                filter_="*.json (*.json)",
                save=False,
                title="Load Joint File",
            )

        return None

    def is_valid(self) -> bool:
        if not self.option("Root Parent").get() and not cmds.ls(selection=True):
            log.warning("Select (or set Root Parent to) the node to load the hierarchy under")
            return False

        filepath = self.option("Filepath").get()

        if not filepath:
            log.warning("Set the Filepath of the joints file to load")
            return False

        if not os.path.isfile(filepath):
            log.warning(f"{filepath} does not exist")
            return False

        return True

    def run(self) -> None:
        created = aniseed_toolkit.scene.hierarchy_io.load_hierarchy_file(
            root_parent=self.option("Root Parent").get() or cmds.ls(selection=True)[0],
            filepath=self.option("Filepath").get(),
            apply_names=self.option("Apply Names").get(),
            invert=self.option("Invert").get(),
            worldspace_root=self.option("Worldspace Root").get(),
        )
        log.info(f"Created {created}")


# --------------------------------------------------------------------------------------
class WriteJointsFile(toolkits.Tool):
    """
    Writes the selected nodes (joints, transforms and their parent and
    point constraints) and their attributes to a json file, which Load
    Joints File can build again.
    """

    identifier = "Write Joints File"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Filepath",
            value="",
            description="The json file to write",
        )

    def option_widget(self, option_name: str):
        if option_name == "Filepath":
            return aniseed.widgets.FilepathSelector(
                self.option(option_name).get(),
                filter_="*.json (*.json)",
                save=True,
                title="Save Joint File",
            )

        return None

    def is_valid(self) -> bool:
        if not _requires_selection("Select the nodes to write"):
            return False

        if not self.option("Filepath").get():
            log.warning("Set the Filepath to write the joints file to")
            return False

        return True

    def run(self) -> None:
        filepath = self.option("Filepath").get()

        aniseed_toolkit.scene.hierarchy_io.write_hierarchy_file(
            cmds.ls(selection=True),
            filepath,
        )
        log.info(f"Written {filepath}")


# --------------------------------------------------------------------------------------
class RollJoints(toolkits.Tool):
    """
    Rolls each selected joint around one of its own local axes (Axis) by
    Value degrees, keeping the world transforms of its children. The
    resulting values end up on the joints' rotations.
    """

    identifier = "Roll Joints"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Axis",
            value="x",
            description="The local axis to roll around: x, y or z",
        )

        self.declare_option(
            name="Value",
            value=90,
            description="The amount to roll by, in degrees",
        )

    def option_widget(self, option_name: str):
        if option_name == "Axis":
            return aniseed.widgets.ItemSelector(
                items=["x", "y", "z"],
                default_item=self.option(option_name).get(),
            )
        return None

    def is_valid(self) -> bool:
        if self.option("Axis").get() not in ["x", "y", "z"]:
            log.warning("Axis must be x, y or z")
            return False

        return _requires_selection("Select the joints to roll")

    def run(self) -> None:
        aniseed_toolkit.scene.joints.roll(
            cmds.ls(selection=True),
            self.option("Axis").get(),
            self.option("Value").get(),
        )


# --------------------------------------------------------------------------------------
class SetJointDrawStyle(toolkits.Tool):
    """
    Shows or hides the bones of the selected joints (by setting their draw
    style). Turn Visible off to hide them.
    """

    identifier = "Set Draw Style"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Visible",
            value=True,
            description="Whether to show the bones (otherwise they are hidden)",
        )

    def is_valid(self) -> bool:
        return _requires_selection("Select the joints to show or hide")

    def run(self) -> None:
        _set_draw_style(mref.selected(), self.option("Visible").get())


# --------------------------------------------------------------------------------------
class SetJointHierarchyDrawStyle(toolkits.Tool):
    """
    Shows or hides the bones of the selected joints and of every joint below
    them (by setting their draw style). Turn Visible off to hide them.
    Locked or connected draw styles are left as they are.
    """

    identifier = "Set Draw Style (Hierarchy)"
    toolkit = "Rigging"
    categories = ["Joints"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Visible",
            value=True,
            description="Whether to show the bones (otherwise they are hidden)",
        )

    def is_valid(self) -> bool:
        return _requires_selection("Select the joints at the top of the hierarchies to show or hide")

    def run(self) -> None:
        joints = []

        for node in mref.selected():
            joints.append(node)
            joints.extend(node.children(recursive=True, node_type="joint"))

        _set_draw_style(joints, self.option("Visible").get())


# --------------------------------------------------------------------------------------
class MoveJointOrientsToRotation(toolkits.Tool):
    """
    Zeros the joint orients of the selected joints, moving their orientation
    onto their rotations so each joint keeps its world transform.
    """

    identifier = "Move Joint Orients to Rotation"
    toolkit = "Rigging"
    categories = ["Joints"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the joints to move the joint orients of")

    def run(self) -> None:
        aniseed_toolkit.scene.joints.move_orients_to_rotation(cmds.ls(selection=True))


# --------------------------------------------------------------------------------------
class MoveJointRotationsToOrients(toolkits.Tool):
    """
    Zeros the rotations of the selected joints, moving their orientation
    onto their joint orients so each joint keeps its world transform.
    """

    identifier = "Move Joint Rotations To Orients"
    toolkit = "Rigging"
    categories = ["Joints"]

    def is_valid(self) -> bool:
        return _requires_selection("Select the joints to move the rotations of")

    def run(self) -> None:
        aniseed_toolkit.scene.joints.move_rotations_to_orients(cmds.ls(selection=True))
