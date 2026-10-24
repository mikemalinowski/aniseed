"""
Provides LoggingMixin, which gives a component a per-component logger, a
record of the steps it took during its last run and of the nodes it touched,
and two menu entries to inspect them.

What this example teaches:
    * A mixin is a plain class, with no base class and no __init__
    * Mixins add menu entries through mixin_functions
    * Why a mixin cannot rely on overriding the component's hooks

Used by: components/05_extending/ex13_using_a_mixin.py
"""
import logging
import typing

# -- maya.cmds is only used by the "Select Touched Nodes" menu entry
from maya import cmds


class LoggingMixin:
    """
    Adds logging helpers to a RigComponent.

    Call begin_log at the start of run, then log_step and record_touched as
    the component works. The "Print Build Log" and "Select Touched Nodes"
    menu entries then show what the last run did.
    """

    # -- Key idea: a mixin has no __init__. xstack.Component.__init__ does
    # -- call super().__init__(), but with no arguments, so a mixin __init__
    # -- would know nothing about the component it is part of. Instead, any
    # -- state we need is created the first time it is used (see _mixin_state).

    # -- Also note that because RigComponent comes first in the component's
    # -- base classes, its hooks (run, on_build_started...) are found before
    # -- ours. If this mixin defined on_build_started, it would never be
    # -- called. That is why the component calls begin_log itself, rather than
    # -- this mixin hooking into the build.

    # ----------------------------------------------------------------------------------
    def mixin_logger(self) -> logging.Logger:
        """
        Returns a logger named after this component's label, so its messages
        are easy to pick out in the Script Editor.
        """
        return logging.getLogger(f"aniseed_maya_dev_examples.{self.label()}")

    # ----------------------------------------------------------------------------------
    def begin_log(self) -> None:
        """
        Clears the record of the previous run. Call this at the start of run.
        """
        state = self._mixin_state()
        state["steps"] = []
        state["touched"] = []

    # ----------------------------------------------------------------------------------
    def log_step(self, message: str) -> None:
        """
        Logs the message and keeps it in the record of this run.

        Args:
            message: The message to log.
        """
        self._mixin_state()["steps"].append(message)
        self.mixin_logger().info(message)

    # ----------------------------------------------------------------------------------
    def record_touched(self, nodes: typing.List[str]) -> None:
        """
        Adds the given nodes to the record of nodes this run created or
        changed, ignoring any which are already recorded.

        Args:
            nodes: The names of the nodes.
        """
        touched = self._mixin_state()["touched"]
        touched.extend(node for node in nodes if node not in touched)

    # ----------------------------------------------------------------------------------
    def touched_nodes(self) -> typing.List[str]:
        """
        Returns the nodes recorded during the last run.
        """
        return list(self._mixin_state()["touched"])

    # ----------------------------------------------------------------------------------
    def mixin_functions(self) -> typing.Dict[str, callable]:
        """
        Adds the "Print Build Log" and "Select Touched Nodes" menu entries.

        Do not call this directly to gather a component's menu entries. The app
        uses collated_mixin_functions, which asks every mixin on the component
        for its entries, so several mixins can each add their own without
        knowing about one another. For the same reason, a component should not
        override mixin_functions itself (use user_functions instead).
        """
        return {
            "Print Build Log": self._print_build_log,
            "Select Touched Nodes": self._select_touched_nodes,
        }

    # ----------------------------------------------------------------------------------
    def _mixin_state(self) -> dict:
        """
        Returns this mixin's state, creating it the first time it is needed.
        The attribute name is prefixed so it cannot clash with anything the
        component (or another mixin) stores.
        """
        if not hasattr(self, "_logging_mixin_state"):
            self._logging_mixin_state = {"steps": [], "touched": []}

        return self._logging_mixin_state

    # ----------------------------------------------------------------------------------
    def _print_build_log(self) -> None:
        """
        Prints the steps recorded during the last run.
        """
        steps = self._mixin_state()["steps"]

        if not steps:
            print(f"{self.label()} has no build log yet. Build the rig first.")
            return

        print(f"Build log for {self.label()}:")
        for index, step in enumerate(steps, start=1):
            print(f"    {index:02d}. {step}")

    # ----------------------------------------------------------------------------------
    def _select_touched_nodes(self) -> None:
        """
        Selects the recorded nodes which still exist in the scene.
        """
        existing = [node for node in self.touched_nodes() if cmds.objExists(node)]
        cmds.select(existing, replace=True)
