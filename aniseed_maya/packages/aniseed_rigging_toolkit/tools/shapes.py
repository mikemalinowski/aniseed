"""
Rigging Toolkit tools for control shapes: applying shapes from the shape
library, saving, copying, editing, mirroring, colouring and selecting them.
"""
import json
import logging

from maya import cmds

import aniseed
import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)

AXES = ["x", "y", "z"]

JSON_FILTER = "*.json (*.json)"


def _targets(node: str) -> list:
    """
    Returns the given node, or the selected nodes if none is given.
    """
    return [node] if node else cmds.ls(selection=True)


def _requires_targets(node: str, message: str) -> bool:
    if not _targets(node):
        log.warning(message)
        return False

    return True


def _requires_filepath(filepath: str) -> bool:
    if not filepath:
        log.warning("Choose the file in the Filepath option")
        return False

    return True


# --------------------------------------------------------------------------------------
class ApplyShape(toolkits.Tool):
    """
    Gives the selected nodes a shape from the shape library. Their current
    shapes are removed first, unless Clear is turned off, and the shape is
    applied at the size given by Scale By.
    """

    identifier = "Apply Shape"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Shape",
            value="core_circle",
            description="The shape to apply, from the shape library",
        )

        self.declare_option(
            name="Clear",
            value=True,
            description="Whether to remove the node's current shapes first",
        )

        self.declare_option(
            name="Scale By",
            value=1.0,
            description="The size to apply the shape at",
        )

    def option_widget(self, option_name: str):
        if option_name == "Shape":
            return aniseed.widgets.ItemSelector(
                au.scene.shapes.library(),
                self.option("Shape").get(),
            )
        return None

    def is_valid(self) -> bool:
        if self.option("Shape").get() not in au.scene.shapes.library():
            log.warning(f"There is no shape called {self.option('Shape').get()!r}")
            return False

        if not cmds.ls(selection=True):
            log.warning("Select the nodes to apply the shape to")
            return False

        return True

    def run(self) -> None:
        for node in cmds.ls(selection=True):
            au.scene.shapes.load_shape(
                node=node,
                data=self.option("Shape").get(),
                clear=self.option("Clear").get(),
                scale_by=self.option("Scale By").get(),
            )


# --------------------------------------------------------------------------------------
class ApplyShapeColorPrompt(toolkits.Tool):
    """
    Asks for a colour with Maya's colour editor, and applies it to the shapes
    of the selected nodes (turning on their colour overrides).
    """

    identifier = "Apply Shape Color Prompt"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the nodes to colour")
            return False

        return True

    def run(self) -> None:
        cmds.colorEditor()

        if not cmds.colorEditor(query=True, result=True):
            return

        # -- The colour editor gives values between 0 and 1, while
        # -- apply_color takes them between 0 and 255
        r, g, b = [channel * 255.0 for channel in cmds.colorEditor(query=True, rgb=True)]

        for node in cmds.ls(selection=True):
            au.scene.shapes.apply_color(node=node, r=r, g=g, b=b)


# --------------------------------------------------------------------------------------
class CombineShapes(toolkits.Tool):
    """
    Moves the shapes of all the selected nodes under the first selected
    node, and deletes the other nodes.
    """

    identifier = "Combine Shapes"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def is_valid(self) -> bool:
        if len(cmds.ls(selection=True)) < 2:
            log.warning("Select the node to combine the shapes under, then the nodes to take them from")
            return False

        return True

    def run(self) -> None:
        au.scene.shapes.combine(cmds.ls(selection=True))


# --------------------------------------------------------------------------------------
class RotateShapes(toolkits.Tool):
    """
    Spins the shapes of the given node (or the selected nodes) around their
    local origin by X, Y and Z degrees.
    """

    identifier = "Rotate Shapes"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node whose shapes should be spun. If empty, the selected nodes are used",
        )

        for axis in ("X", "Y", "Z"):
            self.declare_option(
                name=axis,
                value=0.0,
                description=f"The degrees to spin the shapes by on their local {axis} axis",
            )

    def is_valid(self) -> bool:
        return _requires_targets(self.option("Node").get(), "Select the nodes whose shapes should be rotated")

    def run(self) -> None:
        for node in _targets(self.option("Node").get()):
            au.scene.shapes.rotate(
                node,
                self.option("X").get(),
                self.option("Y").get(),
                self.option("Z").get(),
            )


# --------------------------------------------------------------------------------------
class OffsetShapes(toolkits.Tool):
    """
    Moves the shapes of the given node (or the selected nodes) by Offset By,
    multiplied per axis by X, Y and Z.
    """

    identifier = "Offset Shapes"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node whose shapes should be offset. If empty, the selected nodes are used",
        )

        self.declare_option(
            name="Offset By",
            value=0.0,
            description="The amount to offset the shapes by",
        )

        for axis in ("X", "Y", "Z"):
            self.declare_option(
                name=axis,
                value=1.0,
                description=f"A multiplier for the offset on the {axis} axis",
            )

    def is_valid(self) -> bool:
        return _requires_targets(self.option("Node").get(), "Select the nodes whose shapes should be offset")

    def run(self) -> None:
        for node in _targets(self.option("Node").get()):
            au.scene.shapes.offset(
                node=node,
                offset_by=self.option("Offset By").get(),
                x=self.option("X").get(),
                y=self.option("Y").get(),
                z=self.option("Z").get(),
            )


# --------------------------------------------------------------------------------------
class ScaleShapes(toolkits.Tool):
    """
    Scales the shapes of the given node (or the selected nodes) in place by
    Scale By, multiplied per axis by X, Y and Z.
    """

    identifier = "Scale Shapes"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node whose shapes should be scaled. If empty, the selected nodes are used",
        )

        self.declare_option(
            name="Scale By",
            value=1.0,
            description="The amount to scale the shapes by",
        )

        for axis in ("X", "Y", "Z"):
            self.declare_option(
                name=axis,
                value=1.0,
                description=f"A multiplier for the scale on the {axis} axis",
            )

    def is_valid(self) -> bool:
        return _requires_targets(self.option("Node").get(), "Select the nodes whose shapes should be scaled")

    def run(self) -> None:
        for node in _targets(self.option("Node").get()):
            au.scene.shapes.scale(
                node=node,
                scale_by=self.option("Scale By").get(),
                x=self.option("X").get(),
                y=self.option("Y").get(),
                z=self.option("Z").get(),
            )


# --------------------------------------------------------------------------------------
class CopyShape(toolkits.Tool):
    """
    Remembers the shapes of the given node (or the first selected node), for
    Paste Shape to apply to other nodes.
    """

    identifier = "Copy Shape"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node to copy the shapes of. If empty, the first selected node is used",
        )

    def is_valid(self) -> bool:
        return _requires_targets(self.option("Node").get(), "Select the node to copy the shapes of")

    def run(self) -> None:
        node = _targets(self.option("Node").get())[0]

        clipboard = toolkits.clipboard("Shape")
        clipboard["data"] = au.scene.shapes.shape_to_dict(node)

        log.info(f"Copied the shapes of {node}")


# --------------------------------------------------------------------------------------
class PasteShape(toolkits.Tool):
    """
    Gives the selected nodes the shapes copied with Copy Shape. Their current
    shapes are removed first, unless Clear is turned off.
    """

    identifier = "Paste Shape"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Clear",
            value=True,
            description="Whether to remove the node's current shapes first",
        )

    def is_valid(self) -> bool:
        if not toolkits.clipboard("Shape").get("data"):
            log.warning("Copy a shape with Copy Shape first")
            return False

        if not cmds.ls(selection=True):
            log.warning("Select the nodes to paste the shape onto")
            return False

        return True

    def run(self) -> None:
        for node in cmds.ls(selection=True):
            au.scene.shapes.load_shape(
                node=node,
                data=toolkits.clipboard("Shape")["data"],
                clear=self.option("Clear").get(),
            )


# --------------------------------------------------------------------------------------
class SaveShape(toolkits.Tool):
    """
    Writes the shapes of the given node (or the first selected node) to a
    json shape file. Save it into a shapes folder of the shape library to
    make it available to Apply Shape.
    """

    identifier = "Save Shape"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Node",
            value="",
            description="The node to save the shapes of. If empty, the first selected node is used",
        )

        self.declare_option(
            name="Filepath",
            value="",
            description="The json file to write the shape to",
        )

    def option_widget(self, option_name: str):
        if option_name == "Filepath":
            return aniseed.widgets.FilepathSelector(
                self.option("Filepath").get(),
                filter_=JSON_FILTER,
                save=True,
                title="Save Shape",
            )
        return None

    def is_valid(self) -> bool:
        if not _requires_targets(self.option("Node").get(), "Select the node to save the shapes of"):
            return False

        return _requires_filepath(self.option("Filepath").get())

    def run(self) -> None:
        node = _targets(self.option("Node").get())[0]
        filepath = self.option("Filepath").get()

        if not au.scene.shapes.save_to_file(node, filepath):
            log.warning(f"{node} has no curve shapes to save")
            return False

        log.info(f"Saved the shapes of {node} to {filepath}")


# --------------------------------------------------------------------------------------
class SaveAllRigControlShapes(toolkits.Tool):
    """
    Writes the shapes of every rig control in the scene to one json file,
    which Load Rig Control Shapes From File can apply again (to controls
    with the same names).
    """

    identifier = "Save All Rig Control Shapes"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Filepath",
            value="",
            description="The json file to write the shapes to",
        )

    def option_widget(self, option_name: str):
        if option_name == "Filepath":
            return aniseed.widgets.FilepathSelector(
                self.option("Filepath").get(),
                filter_=JSON_FILTER,
                save=True,
                title="Store Shapes",
            )
        return None

    def is_valid(self) -> bool:
        return _requires_filepath(self.option("Filepath").get())

    def run(self) -> None:
        all_data = {
            control: au.scene.shapes.shape_to_dict(control)
            for control in au.rig.all_controls()
        }

        with open(self.option("Filepath").get(), "w") as f:
            json.dump(
                all_data,
                f,
                indent=4,
                sort_keys=True,
            )

        log.info(f"Saved the shapes of {len(all_data)} controls to {self.option('Filepath').get()}")


# --------------------------------------------------------------------------------------
class LoadRigControlShapesFromFile(toolkits.Tool):
    """
    Applies the control shapes stored with Save All Rig Control Shapes to the
    controls in the scene with the same names. Controls which do not exist
    are skipped.
    """

    identifier = "Load Rig Control Shapes From File"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Filepath",
            value="",
            description="The json file to read the shapes from",
        )

    def option_widget(self, option_name: str):
        if option_name == "Filepath":
            return aniseed.widgets.FilepathSelector(
                self.option("Filepath").get(),
                filter_=JSON_FILTER,
                save=False,
                title="Load Shapes",
            )
        return None

    def is_valid(self) -> bool:
        return _requires_filepath(self.option("Filepath").get())

    def run(self) -> None:
        with open(self.option("Filepath").get(), "r") as f:
            all_data = json.load(f)

        for control, shape_data in all_data.items():
            if cmds.objExists(control):
                au.scene.shapes.load_shape(control, shape_data)


# --------------------------------------------------------------------------------------
class MirrorShape(toolkits.Tool):
    """
    Mirrors the shapes of each selected node across one of its local axes.
    """

    identifier = "Mirror Shape"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Axis",
            value="x",
            description="The local axis to mirror the shapes across",
        )

    def option_widget(self, option_name: str):
        if option_name == "Axis":
            return aniseed.widgets.ItemSelector(AXES, self.option("Axis").get())
        return None

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the nodes whose shapes should be mirrored")
            return False

        return True

    def run(self) -> None:
        for node in cmds.ls(selection=True):
            au.scene.shapes.mirror([node], self.option("Axis").get())


# --------------------------------------------------------------------------------------
class MirrorAcross(toolkits.Tool):
    """
    Mirrors the shapes of each selected node (in world space, across Axis)
    onto its opposite: the node named with Mapping's replace_this replaced by
    its with_this. With an empty Mapping, the shapes of the first selected
    node are mirrored onto the second.
    """

    identifier = "Mirror Across"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Axis",
            value="x",
            description="The world axis to mirror the shapes across",
        )

        self.declare_option(
            name="Mapping",
            value="_LF:_RT",
            description=(
                "replace_this:with_this, turning a selected node's name into the name "
                "of the node to mirror onto. If empty, the first selected node is "
                "mirrored onto the second"
            ),
        )

    def option_widget(self, option_name: str):
        if option_name == "Axis":
            return aniseed.widgets.ItemSelector(AXES, self.option("Axis").get())
        return None

    def is_valid(self) -> bool:
        mapping = self.option("Mapping").get()
        selection = cmds.ls(selection=True)

        if mapping and ":" not in mapping:
            log.warning(f"{mapping!r} is not a mapping in the form _LF:_RT")
            return False

        if mapping and not selection:
            log.warning("Select the nodes to mirror the shapes of")
            return False

        if not mapping and len(selection) != 2:
            log.warning("Select the node to mirror the shapes of, then the node to mirror them onto")
            return False

        return True

    def run(self) -> None:
        mapping = self.option("Mapping").get()
        selection = cmds.ls(selection=True)

        if mapping:
            replace_this, with_this = [part.strip() for part in mapping.split(":", 1)]
            from_nodes = selection
            to_nodes = [node.replace(replace_this, with_this) for node in selection]

        else:
            from_nodes = selection[:1]
            to_nodes = selection[1:]

        au.scene.shapes.mirror_across(
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            axis=self.option("Axis").get(),
        )


# --------------------------------------------------------------------------------------
class MirrorAllShapesAcross(toolkits.Tool):
    """
    Mirrors the shapes of every rig control whose name contains Mapping's
    replace_this onto the control named with its with_this, where one exists
    (for instance every left control onto its right control).
    """

    identifier = "Mirror All Shapes Across"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Mapping",
            value="_LF:_RT",
            description="replace_this:with_this, turning a control's name into its opposite's",
        )

        self.declare_option(
            name="Axis",
            value="x",
            description="The world axis to mirror the shapes across",
        )

    def option_widget(self, option_name: str):
        if option_name == "Axis":
            return aniseed.widgets.ItemSelector(AXES, self.option("Axis").get())
        return None

    def is_valid(self) -> bool:
        if ":" not in self.option("Mapping").get():
            log.warning(f"{self.option('Mapping').get()!r} is not a mapping in the form _LF:_RT")
            return False

        return True

    def run(self) -> None:
        au.rig.mirror_control_shapes(
            mapping=self.option("Mapping").get(),
            axis=self.option("Axis").get(),
        )


# --------------------------------------------------------------------------------------
class SelectShapes(toolkits.Tool):
    """
    Selects the shapes of the selected nodes, in place of the nodes.
    """

    identifier = "Select Shapes"
    toolkit = "Rigging"
    categories = ["Shapes"]

    def is_valid(self) -> bool:
        if not cmds.ls(selection=True):
            log.warning("Select the nodes to select the shapes of")
            return False

        return True

    def run(self) -> None:
        au.scene.shapes.select_shapes(cmds.ls(selection=True))
