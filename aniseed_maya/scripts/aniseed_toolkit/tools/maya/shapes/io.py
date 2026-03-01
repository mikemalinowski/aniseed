import os
import json
import typing
import qtility
import aniseed
import aniseed_toolkit

import maya.cmds as mc
import maya.api.OpenMaya as om


class CopyShape(aniseed_toolkit.Tool):

    identifier = 'Copy Shape'
    classification = "Rigging"
    categories = [
        "Shapes"
    ]
    CACHE = None

    def run(self, node: str = ""):
        """
        This will return a list of shape files which are present in the
        aniseed toolkit shapes directory

        Returns:
            List of absolute paths to the json shape files
        """
        try:
            node = node or mc.ls(sl=True)[0]
        except IndexError:
            print("You must give or select a node")
            return

        CopyShape.CACHE = aniseed_toolkit.run(
            "Read Shape From Node",
            node,
        )


class PasteShape(aniseed_toolkit.Tool):
    identifier = 'Paste Shape'
    classification = "Rigging"
    categories = [
        "Shapes"
    ]
    _CACHE = None

    def run(self, node: str = "", clear=True):
        """
        This will return a list of shape files which are present in the
        aniseed toolkit shapes directory

        Returns:
            List of absolute paths to the json shape files
        """
        if not CopyShape.CACHE:
            print("No copied shape data")
            return

        try:
            node = node or mc.ls(sl=True)[0]
        except IndexError:
            print("You must give or select a node")
            return

        CopyShape._CACHE = aniseed_toolkit.run(
            "Apply Shape",
            node=node,
            data=CopyShape.CACHE,
            clear=clear,
        )


class GetShapeList(aniseed_toolkit.Tool):

    identifier = 'Get Shape List'
    classification = "Rigging"
    user_facing = False
    categories = [
        "Shapes"
    ]

    def run(self) -> list[str]:
        """
        This will return a list of shape files which are present in the
        aniseed toolkit shapes directory

        Returns:
            List of absolute paths to the json shape files
        """
        return aniseed_toolkit.resources.contents("shapes")


class ReadShapeFromNode(aniseed_toolkit.Tool):

    identifier = "Read Shape From Node"
    classification = "Rigging"
    user_facing = False

    categories = [
        "Shapes",
    ]

    def run(self, node: str = "") -> typing.Dict:
        """
        Looks at all the NurbsCurve shape nodes under  the given node
        and attempts to read them into a dictionary format.

        Args:
            node: The node to seralise the shape data for

        Returns:
            dictionary
        """
        return aniseed_toolkit.shapes.shape_to_dict(node)


class ReadShapeFromFile(aniseed_toolkit.Tool):

    identifier = "Read Shape From File"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Shapes",
    ]

    def run(self, shape_file: str = "") -> typing.Dict or None:
        """
        This will attempt to get the shape dictionary data from a shape file.
        The shape file can either be the local name of a shape in the shapes
        directory or an absolute path to a shape file.

        Args:
            shape_file: The shape file to read (either absolute path or the name
                of a shape in the shapes directory)

        Returns:
            dict
        """
        return aniseed_toolkit.shapes.shape_data_from_file(shape_file)


class SaveShape(aniseed_toolkit.Tool):

    identifier = "Save Shape"
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(self, node: str = "", filepath: str = "") -> typing.Dict:
        """
        Writes the curve data of the given node to the given filepath

        Args:
            node: Node to read from
            filepath: Path to write the data into

        Returns:
            Dict of the data stored in the filepath
        """
        node = node or mc.ls(selection=True)[0]

        if not filepath:
            filepath = qtility.request.filepath(
                title="Shape Writing",
                filter_="*.json (*.json)",
                save=True,
                parent=None,
            )

        if not filepath:
            return dict()

        return aniseed_toolkit.shapes.save_to_file(node, filepath)


class ApplyShape(aniseed_toolkit.Tool):

    identifier = "Apply Shape"
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    # noinspection PyTypeChecker,PyUnresolvedReferences
    def run(
            self,
            node: str = "",
            data: typing.Dict or str = "",
            clear: bool = True,
            color=None,
            scale_by=1,
    ) -> typing.List[str]:
        """
        Applies the given shape data to the given node.

        Args:
            node: Node to apply the shape data to
            data: Either a dictionary of shape data, or the absolute path
                to a shape file, or the name of a shape in the shapes directory
            clear: If true, any pre-existing shapes will be removed before this applies
                the shape.
            color: Optional list [r, g, b] which will be used to colour the shape
                on creation
            scale_by: Optional multiplier for scaling the shape at the time of it
                being applied.

        Returns:
            List of shape nodes created
        """
        if not node:
            node = mc.ls(sl=True)[0]

        if not data:
            data = qtility.request.item(
                items=aniseed_toolkit.run("Get Shape List"),
                title="Apply Shape",
                message="Select Shape",
                editable=False,
            )

        return aniseed_toolkit.shapes.load_shape(
            node=node,
            data=data,
            clear=clear,
            color=color,
            scale_by=scale_by,
        )


class SaveAllRigControlShapesToFile(aniseed_toolkit.Tool):

    identifier = "Save All Rig Control Shapes"
    classification = "Rigging"
    categories = ["Shapes"]

    def run(self, filepath: str = ""):

        if not filepath:
            filepath = qtility.request.filepath(
                title="Store Shapes",
                filter_="*.json (*.json)",
                save=True,
                parent=None,
            )

        if not filepath:
            return

        all_controls = aniseed_toolkit.run("Get Controls")

        all_data = dict()

        for control in all_controls:
            all_data[control] = aniseed_toolkit.run("Read Shape From Node", control)

        with open(filepath, "w") as f:
            json.dump(
                all_data,
                f,
                indent=4,
                sort_keys=True,
            )


class LoadRigControlShapesFromFile(aniseed_toolkit.Tool):

    identifier = "Load Rig Control Shapes From File"
    classification = "Rigging"
    categories = ["Shapes"]

    def run(self, filepath: str = ""):

        if not filepath:
            filepath = qtility.request.filepath(
                title="Load Shapes",
                filter_="*.json (*.json)",
                save=False,
                parent=None,
            )

        if not filepath:
            return

        with open(filepath, "r") as f:
            all_data = json.load(f)

        for control, shape_data in all_data.items():
            if mc.objExists(control):
                aniseed_toolkit.run("Apply Shape", control, shape_data)

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name == "filepath":
            return aniseed.widgets.FilepathSelector()
