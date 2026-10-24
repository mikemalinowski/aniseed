"""
Provides the "Dev Example : Lifecycle Logger" component, which logs every
hook aniseed calls on a component, so you can watch the order they happen in.

What this example teaches:
    * Every hook a component can re-implement, and when each one is called
    * Which hooks run during a build, and which run at other times

Try it: open the Script Editor, then add this component, build the rig, save
the scene and re-open it, and remove the component. Each hook logs a line
starting with [Lifecycle].

Read next: ../02_modify/ex05_colour_nodes_cmds.py
"""
import typing
import logging

import aniseed

log = logging.getLogger(__name__)


class LifecycleLogger(aniseed.RigComponent):
    """
    Logs a line to the Script Editor whenever aniseed calls one of this
    component's hooks. Use the "Print Hook History" menu entry to see every
    hook called so far.
    """

    identifier = "Dev Example : Lifecycle Logger"

    # -- If this is set, RigComponent.help opens it in a web browser when the
    # -- user asks for help on this component. It is left empty here, so the
    # -- help method below just logs.
    help_url = ""

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """
        Called whenever the component is created: when the user adds it, when
        a recipe is loaded, and when a component is duplicated. Declare
        inputs, options and outputs here, and do nothing else. In particular,
        do not change the scene, as __init__ runs far more often than a build.
        """
        super().__init__(*args, **kwargs)

        # -- Every hook call is recorded here, so it can be printed from the
        # -- menu. Create any state you need after calling super().__init__.
        self._history: typing.List[str] = []

        self.declare_option(
            name="Message",
            value="Hello from the lifecycle logger",
            description="Logged when the component runs",
        )

        self._record("__init__")

    # ----------------------------------------------------------------------------------
    def on_enter_stack(self):
        """
        Called when the user adds the component to the stack (and when a
        component is duplicated). This is NOT called when a recipe is loaded,
        so it is the place for one-off setup, such as creating guide nodes
        from the current selection or wiring an input to the parent
        component's output (see ex09_simple_control.py).
        """
        super().on_enter_stack()
        self._record("on_enter_stack")

    # -- xstack.Component also declares on_add_to_stack, but the current
    # -- version of xstack never calls it, so use on_enter_stack instead.

    # ----------------------------------------------------------------------------------
    def on_removed_from_stack(self):
        """
        Called when the component is removed from the stack, including when
        the whole stack is cleared before a recipe is loaded. Use it to tidy
        up anything the component made which should not outlive it.
        """
        super().on_removed_from_stack()
        self._record("on_removed_from_stack")

    # ----------------------------------------------------------------------------------
    def is_valid(self) -> bool:
        """
        Called on every component in the build before any of them run. See
        ex03_validation.py.
        """
        self._record("is_valid")
        return True

    # ----------------------------------------------------------------------------------
    def on_build_started(self) -> None:
        """
        Called on every component in the build, after validation has passed
        and before the first component runs.
        """
        self._record("on_build_started")

    # ----------------------------------------------------------------------------------
    def run(self):
        """
        Called when it is this component's turn in the build order.
        """
        self._record("run")
        log.info(f"[Lifecycle] {self.label()} : {self.option('Message').get()}")
        return True

    # ----------------------------------------------------------------------------------
    def on_build_finished(self, successful: bool) -> None:
        """
        Called on every component in the build once the build ends, telling
        it whether the build succeeded. Components after a failed one never
        run, but still get this call. See ex17_publish_rig.py for a real use.
        """
        self._record(f"on_build_finished (successful={successful})")

    # ----------------------------------------------------------------------------------
    def on_serialise(self) -> dict:
        """
        Called whenever the stack is serialised, which happens a lot: whenever
        the recipe is written to the rig node, and whenever the rig is saved.
        Return any extra data to store (see ex11_stored_values.py).
        """
        self._record("on_serialise")
        return {}

    # ----------------------------------------------------------------------------------
    def on_deserialise(self, additional_data: dict) -> None:
        """
        Called when a recipe is loaded, with whatever on_serialise returned
        when it was saved.
        """
        self._record("on_deserialise")

    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Called whenever the app builds this component's menu. Return a
        dictionary of menu labels to functions.
        """
        self._record("user_functions")
        return {
            "Print Hook History": self._print_history,
        }

    # ----------------------------------------------------------------------------------
    def suggested_label(self):
        """
        Called when the user adds the component, to suggest a label for it.
        """
        self._record("suggested_label")
        return "Lifecycle Logger"

    # ----------------------------------------------------------------------------------
    def help(self):
        """
        Called when the user asks for help on this component in the app.
        """
        self._record("help")
        super().help()

    # ----------------------------------------------------------------------------------
    def _record(self, hook_name: str) -> None:
        """
        Logs the hook call and adds it to the history.
        """
        self._history.append(hook_name)
        log.info(f"[Lifecycle] {self.label()} : {hook_name}")

    # ----------------------------------------------------------------------------------
    def _print_history(self) -> None:
        """
        Prints every hook called on this instance, in order.
        """
        print(f"Hooks called on {self.label()}:")
        for index, hook_name in enumerate(self._history, start=1):
            print(f"    {index:03d}. {hook_name}")
