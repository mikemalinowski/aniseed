import bony
import json
import typing
import aniseed_everywhere

import maya.cmds as mc


# --------------------------------------------------------------------------------------
class MayaRig(aniseed_everywhere.Rig):
    """
    We subclass the Rig to be a maya specific class which allows us to override
    the save and load. We do the because we want to be able to write additional
    data into the file such as joint and transform data.
    """


    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, label="", host=None, component_paths: typing.List or None = None):
        super(MayaRig, self).__init__(
            label=label,
            host=host,
            component_paths=component_paths,
        )

    # ----------------------------------------------------------------------------------
    def save(self, filepath: str, additional_data: typing.Dict or None = None):
        """
        This will serialise the stack to a dictionary, including any additional data
        you may want to stored with it, and then saved to the given filepath
        """
        additional_data = additional_data or {}

        nodes = []

        nodes.extend(
            mc.listRelatives(
                self.label,
                allDescendents=True
            ) or list()
        )

        nodes = [
            n
            for n in nodes
            if mc.nodeType(n) in bony.writer.SUPPORTED_TYPES
        ]

        additional_data = dict(
            hierarchy=bony.writer.create_dataset_from_nodes(
                nodes,
            ),
        )

        super(MayaRig, self).save(filepath, additional_data)

    # ----------------------------------------------------------------------------------
    @classmethod
    def load(cls, data: str or typing.Dict, component_paths: typing.List or None = None):
        stack = super(MayaRig, cls).load(data, component_paths)

        if isinstance(data, str):
            with open(data, "r") as f:
                data = json.load(f)

        additional_data = data.get("additional_data", dict())

        if "hierarchy" in additional_data:
            bony.writer.create_nodes_from_dataset(
                root_parent=stack.label,
                dataset=additional_data["hierarchy"],
            )

        return stack