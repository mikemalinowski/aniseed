"""
Provides the "Dev Example : Validation" component, which checks that a node
exists, and can be told to fail on purpose so each kind of failure can be seen.

What this example teaches:
    * Required inputs (validate=True) and is_valid
    * Why is_valid must not check inputs which are wired to outputs
    * Returning False versus raising an exception from run

Read next: ex04_lifecycle_logger.py
"""
import logging

# -- maya.cmds is used to check whether the node exists
from maya import cmds

import aniseed

log = logging.getLogger(__name__)


class ValidationExample(aniseed.RigComponent):
    """
    Checks that the given node exists before the rig builds. Set Fail On
    Purpose to see how a failed run is reported.
    """

    identifier = "Dev Example : Validation"

    # -- The choices for the Fail On Purpose option
    FAILURE_MODES = ["Never", "Return False", "Raise"]

    def __init__(self, *args, **kwargs):
        """
        Declares the Node input and the Fail On Purpose option.
        """
        super().__init__(*args, **kwargs)

        # -- validate=True (the default for inputs) makes the input required.
        # -- Before anything is built, the stack checks every required input
        # -- has been given a value, and refuses to build if one is empty.
        self.declare_input(
            name="Node",
            value="",
            validate=True,
            description="The node which must exist for the build to go ahead",
        )

        self.declare_option(
            name="Fail On Purpose",
            value="Never",
            description=(
                "Never: run succeeds. Return False: run reports a failure. "
                "Raise: run raises an exception."
            ),
        )

    def option_widget(self, option_name):
        """
        Returns a drop down of the failure modes for Fail On Purpose.
        """
        if option_name == "Fail On Purpose":
            return aniseed.widgets.ItemSelector(
                items=self.FAILURE_MODES,
                default_item=self.option("Fail On Purpose").get(),
            )
        return None

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the Node input.
        """
        if requirement_name == "Node":
            return aniseed.widgets.ObjectSelector(component=self)
        return None

    def is_valid(self) -> bool:
        """
        Checks the node exists. Returns False, with a warning saying why, if
        it does not.
        """
        # -- Key idea: the stack calls is_valid on EVERY component before it
        # -- builds ANY of them, so a problem is reported before the scene is
        # -- changed at all. Keep is_valid quick, and never change the scene
        # -- in it.
        node_input = self.input("Node")

        # -- If the input is wired to another component's output, the output
        # -- is only filled in when that component runs, which has not
        # -- happened yet. There is nothing we can check at this point.
        if node_input.is_address():
            return True

        node = node_input.get()

        # -- An empty value is already reported by the required input check
        # -- (validate=True), so there is no need to report it twice
        if not node:
            return True

        if not cmds.objExists(node):
            # -- Always say which component failed and why. The build report
            # -- only says that validation failed.
            log.warning(f"{self.label()} : {node!r} does not exist in the scene")
            return False

        return True

    def run(self):
        """
        Succeeds, returns False or raises, depending on Fail On Purpose.
        """
        mode = self.option("Fail On Purpose").get()

        if mode == "Return False":
            # -- Return False for a failure you expected and can explain, such
            # -- as missing data. Log the reason first, as the build report
            # -- only records that this component returned False.
            log.warning(f"{self.label()} : failing on purpose by returning False")
            return False

        if mode == "Raise":
            # -- Raise for something that should never happen. The build
            # -- stops and the traceback is shown in the app and recorded in
            # -- self.last_error().
            raise RuntimeError(f"{self.label()} : failing on purpose by raising")

        log.info(f"{self.label()} : {self.input('Node').get()} exists")
        return True
