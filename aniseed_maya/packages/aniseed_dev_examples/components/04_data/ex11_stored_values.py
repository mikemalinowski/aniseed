"""
Provides the "Dev Example : Stored Values" component, which captures attribute
values from the scene, stores them in the rig, and re-applies them on every
build. This is how pose, set driven key and shape capture components work.

What this example teaches:
    * Buttons in the options panel, and entries in the component's menu
    * Two ways to store data: a hidden option, and on_serialise
    * Versioning stored data, and migrating data saved by an older version

Read next: ../05_extending/ex12_custom_widget.py
"""
import time
import typing
import getpass
import logging

# -- maya.cmds is the only Maya API this example uses
from maya import cmds

import aniseed

log = logging.getLogger(__name__)


class StoredValues(aniseed.RigComponent):
    """
    Press Capture to store the current values of the chosen attributes on the
    chosen nodes. Every build then sets them back to those values. Use the
    menu to capture or apply for just the selected nodes.
    """

    identifier = "Dev Example : Stored Values"

    # -- Key idea: version is stored alongside this component's data in the
    # -- recipe. Version 1 stored the values as a list of [node, attribute,
    # -- value] entries; version 2 stores a dictionary. Whenever a recipe
    # -- saved by an older version is loaded, migrate (below) is given the
    # -- old data to convert. Without this, changing how data is stored would
    # -- break every rig saved before the change.
    version = 2

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes input, the Attributes option, the Capture button
        and the hidden option which stores the captured values.
        """
        super().__init__(*args, **kwargs)

        # -- Who captured the values and when, which is stored through
        # -- on_serialise rather than as an option (see on_serialise)
        self._capture_info: typing.Dict = {}

        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes to capture values from. Wired inputs can only be captured after a build.",
            group="Scene",
        )

        self.declare_option(
            name="Attributes",
            value=["translateX", "translateY", "translateZ"],
            description="The attributes to capture. Only single numeric or boolean attributes are supported.",
            group="Behaviour",
        )

        # -- An option whose widget is a button. The button does not hold a
        # -- value of its own, so the value is None.
        self.declare_option(
            name="Capture",
            value=None,
            description="Stores the current values of the attributes, replacing anything stored before",
            group="Behaviour",
        )

        # -- Storage approach A: a hidden option. It is saved in the recipe
        # -- like any other option, but never shown in the app. The data is
        # -- {node name: {attribute name: value}}.
        self.declare_option(
            name="_Stored Values",
            value={},
            hidden=True,
            description="The captured values, keyed by node and then attribute",
        )

    def option_widget(self, option_name):
        """
        Returns a Capture button for the Capture option and a text list for
        the Attributes option.
        """
        if option_name == "Capture":
            return aniseed.widgets.ButtonWidget(
                button_name="Capture",
                func=self.capture,
            )

        if option_name == "Attributes":
            return aniseed.widgets.TextList()

        return None

    def input_widget(self, requirement_name):
        """
        Returns an object list for the Nodes input.
        """
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()
        return None

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Adds entries to this component's menu in the app. Menu entries are a
        good place for actions the user takes now and then, rather than on
        every build.
        """
        return {
            "Capture Selected": self.capture_selected,
            "Apply To Selected": self.apply_to_selected,
            "Print Stored Values": self.print_stored_values,
        }

    def run(self):
        """
        Sets every stored value back onto its node.
        """
        self._apply()
        return True

    # ----------------------------------------------------------------------------------
    # -- Storage approach B: on_serialise and on_deserialise.
    # --
    # -- on_serialise returns any extra json serialisable data to store with
    # -- the component, and on_deserialise is given it back when the recipe
    # -- loads. Use it for data the user should never edit or wire up, or which
    # -- is awkward to hold as an option. Use a hidden option (approach A) for
    # -- data which other components might want to address, and for anything
    # -- you want to see in the recipe beside the rest of the options.
    def on_serialise(self) -> dict:
        """
        Stores who captured the values, when, and from which scene.
        """
        return {"capture_info": self._capture_info}

    def on_deserialise(self, additional_data: dict) -> None:
        """
        Restores the capture details stored by on_serialise.
        """
        self._capture_info = additional_data.get("capture_info", {})

    # ----------------------------------------------------------------------------------
    @classmethod
    def migrate(cls, data: dict, from_version: int) -> dict:
        """
        Converts the data of a recipe saved by an older version of this
        component. Version 1 stored the values as a list of
        [node, attribute, value] entries.

        Args:
            data: A copy of this component's data from the recipe.
            from_version: The version the data was saved with.
        """
        if from_version < 2:
            stored = data.get("options", {}).get("_Stored Values")

            if isinstance(stored, list):
                converted = {}
                for node, attribute, value in stored:
                    converted.setdefault(node, {})[attribute] = value

                data["options"]["_Stored Values"] = converted

        return data

    # ----------------------------------------------------------------------------------
    def capture(self):
        """
        Captures the values from every node in Nodes, replacing anything
        stored before.
        """
        nodes = self.input("Nodes").get() or []

        # -- A wired input may hold a single node name rather than a list
        if isinstance(nodes, str):
            nodes = [nodes]

        self._store(self._read_values(nodes), replace=True)

    def capture_selected(self):
        """
        Captures the values from the selected nodes, adding to (or updating)
        what is already stored.
        """
        self._store(self._read_values(cmds.ls(selection=True) or []), replace=False)

    def apply_to_selected(self):
        """
        Applies the stored values to the selected nodes only.
        """
        self._apply(only=cmds.ls(selection=True) or [])

    def print_stored_values(self):
        """
        Prints the stored values and who captured them.
        """
        print(f"{self.label()} : captured {self._capture_info or '(no capture details)'}")
        for node, values in self.option("_Stored Values").get().items():
            print(f"    {node} : {values}")

    # ----------------------------------------------------------------------------------
    def _read_values(self, nodes: typing.List[str]) -> dict:
        """
        Returns {node: {attribute: value}} for the given nodes and the
        Attributes option. Missing nodes and unsupported attributes are skipped
        with a warning.
        """
        captured = {}

        for node in nodes:
            if not cmds.objExists(node):
                log.warning(f"{self.label()} : {node} does not exist, so was not captured")
                continue

            for attribute_name in self.option("Attributes").get():

                if not cmds.attributeQuery(attribute_name, node=node, exists=True):
                    continue

                value = cmds.getAttr(f"{node}.{attribute_name}")

                # -- Compound attributes (such as translate) come back as a
                # -- list of tuples. Keep to single values, as they are simple
                # -- to store and set back.
                if not isinstance(value, (int, float, bool)):
                    log.warning(f"{self.label()} : {node}.{attribute_name} is not a single value, so was skipped")
                    continue

                captured.setdefault(node, {})[attribute_name] = value

        return captured

    def _store(self, values: dict, replace: bool):
        """
        Stores the captured values on the hidden option, and records who
        captured them.

        Args:
            values: {node: {attribute: value}} to store.
            replace: If True, anything stored before is discarded.
        """
        stored = {} if replace else dict(self.option("_Stored Values").get())

        for node, attributes in values.items():
            stored.setdefault(node, {}).update(attributes)

        # -- Always set a new value rather than changing the stored one in
        # -- place. Setting it is what tells aniseed the rig has changed, so
        # -- the recipe is written back to the rig node.
        self.option("_Stored Values").set(stored)

        self._capture_info = {
            "user": getpass.getuser(),
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scene": cmds.file(query=True, sceneName=True) or "(unsaved scene)",
        }

        log.info(f"{self.label()} : stored values for {len(values)} node(s)")

    def _apply(self, only: typing.Optional[typing.List[str]] = None):
        """
        Sets the stored values back onto their nodes. Nodes which no longer
        exist, and attributes which cannot be set (locked or connected), are
        skipped with a warning.

        Args:
            only: If given, only these nodes are set.
        """
        for node, values in self.option("_Stored Values").get().items():

            if only is not None and node not in only:
                continue

            if not cmds.objExists(node):
                log.warning(f"{self.label()} : {node} does not exist, so its values were not applied")
                continue

            for attribute_name, value in values.items():
                plug = f"{node}.{attribute_name}"

                # -- settable is False when the attribute is locked or has an
                # -- incoming connection, where setAttr would raise
                if not cmds.getAttr(plug, settable=True):
                    log.warning(f"{self.label()} : {plug} is locked or connected, so was not applied")
                    continue

                cmds.setAttr(plug, value)
