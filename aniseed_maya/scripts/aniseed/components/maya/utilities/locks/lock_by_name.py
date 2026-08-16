import re
import aniseed
from maya import cmds


class LockByNameComponent(aniseed.RigComponent):

    identifier = "Utility : Lock By Name"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Name Regex",
            value="",
            description="Regex to match",
        )

        self.declare_option(
            name="Type Regex",
            value=".*",
            description="Regex to match",
        )

        self.declare_option(
            name="Match Against Long Name",
            value=False,
            description="Match Against Long Name",
        )

    def run(self):
        match_against_long_name = self.option("Match Against Long Name").get()
        name_regex = re.compile(self.option("Name Regex").get())
        type_regex = re.compile(self.option("Type Regex").get())

        for node in cmds.ls():

            if match_against_long_name:
                node = cmds.ls(node, long=True)[0]

            if name_regex.search(node) and type_regex.search(cmds.nodeType(node)):
                self.run_lock(node)

    def run_lock(self, node):
        cmds.lockNode(node, lock=True)


class LockNodeAndTransformByNameComponent(LockByNameComponent):

    identifier = "Utility : Lock By Name (Including Transform)"

    def run_lock(self, node):
        for type_ in ["translate", "rotate", "scale"]:
            for axis in ["X", "Y", "Z"]:
                cmds.setAttr(f"{node}.{type_}{axis}", lock=True)

        cmds.lockNode(node, lock=True)


class UnlockByNameComponent(LockByNameComponent):

    identifier = "Utility : Unlock By Name"

    def run_lock(self, node):
        cmds.lockNode(node, lock=False)