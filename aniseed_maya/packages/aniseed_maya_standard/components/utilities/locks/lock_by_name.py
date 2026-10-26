"""
Provides regex driven node locking components. "Utility : Lock By Name"
locks every scene node whose name and node type match the given regexes,
"Utility : Lock By Name (Including Transform)" also locks their transform
channels, and "Utility : Unlock By Name" unlocks the matched nodes instead.
"""
import re
import logging
import mref
import aniseed
from maya import cmds

log = logging.getLogger(__name__)


class LockByNameComponent(aniseed.RigComponent):
    """
    Locks every node in the scene whose name matches the Name Regex and
    whose node type matches the Type Regex.
    """

    identifier = "Utility : Lock By Name"

    def __init__(self, *args, **kwargs):
        """
        Declares the Name Regex, Type Regex and Match Against Long Name options.
        """
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

    def is_valid(self) -> bool:
        """
        Checks that the Name Regex is given and that both regexes compile. An
        empty Name Regex would match every node in the scene.
        """
        name_regex = self.option("Name Regex").get()

        if not name_regex:
            log.warning(
                f"{self.label()} : Name Regex is empty, which would match every node in the scene"
            )
            return False

        for option_name, pattern in (
            ("Name Regex", name_regex),
            ("Type Regex", self.option("Type Regex").get()),
        ):
            try:
                re.compile(pattern)

            except re.error as exc:
                log.warning(f"{self.label()} : {option_name} {pattern!r} is not a valid regex ({exc})")
                return False

        return True

    def run(self):
        """
        Scans every node in the scene and calls run_lock on each one whose name
        (short or long, depending on Match Against Long Name) matches the Name
        Regex and whose node type matches the Type Regex.
        """
        match_against_long_name = self.option("Match Against Long Name").get()
        name_regex = re.compile(self.option("Name Regex").get())
        type_regex = re.compile(self.option("Type Regex").get())

        # -- This scans every node in the scene, so the matching is done on
        # -- plain names with maya.cmds and only the matches are wrapped
        for node in cmds.ls():

            if match_against_long_name:
                node = cmds.ls(node, long=True)[0]

            if name_regex.search(node) and type_regex.search(cmds.nodeType(node)):
                self.run_lock(mref.get(node))

    def run_lock(self, node: mref.ReferencedItem):
        """
        Applies the lock to a single matched node
        """
        node.lock()


class LockNodeAndTransformByNameComponent(LockByNameComponent):
    """
    As Lock By Name, but also locks the translate, rotate and scale
    channels of each matched node before locking the node itself.
    """

    identifier = "Utility : Lock By Name (Including Transform)"

    def run_lock(self, node: mref.ReferencedItem):
        """
        Locks the translate, rotate and scale channels of the matched node and
        then locks the node itself.
        """
        # -- Plain attribute locks. Note that the node's
        # -- lock_transform_attributes is not equivalent, as it
        # -- also alters the channel box state.
        node.lock_attributes(
            [
                f"{type_}{axis}"
                for type_ in ["translate", "rotate", "scale"]
                for axis in ["X", "Y", "Z"]
            ]
        )
        node.lock()


class UnlockByNameComponent(LockByNameComponent):
    """
    As Lock By Name, but unlocks each matched node instead.
    """

    identifier = "Utility : Unlock By Name"

    def run_lock(self, node: mref.ReferencedItem):
        """
        Unlocks the matched node.
        """
        node.unlock()
