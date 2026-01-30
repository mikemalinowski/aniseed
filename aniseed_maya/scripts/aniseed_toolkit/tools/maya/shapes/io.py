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
        if mc.nodeType(node) == "transform" or mc.nodeType(node) == "joint":
            shapes = mc.listRelatives(node, type="nurbsCurve")

        else:
            shapes = [node]
        if not shapes:
            print("no shapes found")
            return {}

        # -- Define out output data. Right now we"re only storing
        # -- cv"s, but we wrap it in a dict so we can expand it
        # -- later without compatibility issues.
        data = dict(
            node=node,
            curves=list(),
        )

        # -- Cycle the shapes and store thm
        for shape in shapes:
            pointer = aniseed_toolkit.run("Get MObject", shape)
            nurbs_fn = om.MFnNurbsCurve(pointer)

            node_data = dict(
                form=mc.getAttr(f"{shape}.form"),
                degree=mc.getAttr(f"{shape}.degree"),
                knots=[n for n in nurbs_fn.knots()],
                cvs=[list(p)[:3] for p in nurbs_fn.cvPositions(om.MSpace.kObject)],
            )

            data["curves"].append(node_data)

        return data


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
        if not shape_file.endswith(".json"):
            shape_file = shape_file + ".json"

        if not os.path.exists(shape_file):
            shape_file = aniseed_toolkit.resources.get("shapes/" + shape_file)

        if not os.path.exists(shape_file):
            print("could not find shape : %s" % shape_file)
            return None

        with open (shape_file, "r") as f:
            return json.load(f)


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
        node = node or mc.ls(sl=True)[0]

        if not filepath:
            filepath = qtility.request.filepath(
                title="Shape Writing",
                filter_="*.json (*.json)",
                save=True,
                parent=None,
            )

        if not filepath:
            return dict()

        data = aniseed_toolkit.run("Read Shape From Node", node)

        if not data:
            return {}

        with open(filepath, "w") as f:
            json.dump(
                data,
                f,
                indent=4,
                sort_keys=True,
            )

        return data


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

        if isinstance(data, str):
            data = aniseed_toolkit.run("Read Shape From File", data)

        if not data:
            print("Could not find shape : %s" % data)
            return []

        if clear:
            for curve in mc.listRelatives(node, type="nurbsCurve") or list():
                mc.delete(curve)

        # -- Define a list which we will collate all the shapes
        # -- in
        shape_list = list()

        # -- Cycle over each curve element in the data
        for curve_data in data["curves"]:
            # -- Create a curve with the given cv"s
            transform = mc.curve(
                p=[
                    p
                    for p in curve_data["cvs"]
                ],
                d=curve_data["degree"],
                k=curve_data["knots"],
            )

            # -- Parent the shape under the node
            curve = mc.listRelatives(transform, type="nurbsCurve")[0]

            aniseed_toolkit.run("Scale Shapes", curve, scale_by)

            mc.parent(
                curve,
                node,
                shape=True,
                r=True,
            )

            # -- Delete the transform
            mc.delete(transform)

            shape_list.append(curve)

        if color:
            aniseed_toolkit.run("Apply Shape Color", node, *color)

        mc.select(node)

        return shape_list


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
