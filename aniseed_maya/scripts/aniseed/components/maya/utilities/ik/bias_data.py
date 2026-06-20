import os
import json
import aniseed
import qtility
import functools

from maya import cmds


# noinspection PyUnresolvedReferences
class ApplyIKBiasData(aniseed.RigComponent):
    """
    Captures spring-angle-bias data from a chosen list of IK handles into
    a self-contained cache, and re-applies that cache at build time. Use
    the Snapshot Bias Data button to capture current values from the
    scene; the cache is then re-applied on every subsequent rig build.
    """

    identifier = "Utility : Apply IK Bias Data"
    icon = os.path.join(os.path.dirname(__file__), "icon.png")

    _RECORDABLE_ATTRIBUTES = (
        "springAngleBias_Position",
        "springAngleBias_FloatValue",
        "springAngleBias_Interp",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Apply Data",
            value=True,
            description="If false, the component is a no-op. Useful for temporarily disabling apply without removing the component.",
        )

        self.declare_input(
            name="IK Handles",
            value=[],
            description="The IK handles whose spring-angle-bias data will be captured by Snapshot Bias Data. Not used at apply time — the cache itself drives apply.",
        )

        self.declare_option(
            name="Bias Data",
            value=dict(),
            hidden=True,
            description="The persisted bias-data cache applied to IK handles at build time. Populated via Snapshot Bias Data or Load Bias Data File.",
        )

        self.declare_option(
            name="Snapshot Bias Data",
            value=None,
            description="Button. Captures spring-angle-bias data from every handle in IK Handles and stores it in Bias Data.",
        )

        self.declare_option(
            name="Clear Bias Data",
            value=None,
            description="Button. Empties the Bias Data cache after confirmation.",
        )

        self.declare_option(
            name="Save Bias Data File",
            value=None,
            description="Button. Writes the current cache to a JSON file on disk.",
        )

        self.declare_option(
            name="Load Bias Data File",
            value=None,
            description="Button. Replaces Bias Data with the contents of a JSON file on disk.",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "IK Handles":
            return aniseed.widgets.ObjectList()
        return None

    def option_widget(self, option_name):
        if option_name == "Snapshot Bias Data":
            return aniseed.widgets.ButtonWidget(
                button_name="Snapshot Bias Data",
                func=functools.partial(self.snapshot_bias_data),
            )

        if option_name == "Clear Bias Data":
            return aniseed.widgets.ButtonWidget(
                button_name="Clear Bias Data",
                func=functools.partial(self.clear_bias_data),
            )

        if option_name == "Save Bias Data File":
            return aniseed.widgets.ButtonWidget(
                button_name="Save Bias Data File",
                func=functools.partial(self.save_bias_data_file),
            )

        if option_name == "Load Bias Data File":
            return aniseed.widgets.ButtonWidget(
                button_name="Load Bias Data File",
                func=functools.partial(self.load_bias_data_file),
            )

        return None

    def run(self) -> bool:
        if not self.option("Apply Data").get():
            return True

        stored_bias_data = self.option("Bias Data").get()

        if not stored_bias_data:
            print("no stored bias data")
            return True

        for ikh, bias_data in stored_bias_data.items():
            if not cmds.objExists(ikh):
                continue
            self._apply_bias_data(ikh, bias_data)

        return True

    def snapshot_bias_data(self):
        data = {}
        for ikh in self.input("IK Handles").get():
            if not cmds.objExists(ikh):
                continue
            data[ikh] = self._read_bias_data(ikh)
        self.option("Bias Data").set(data)

    def clear_bias_data(self):
        confirmation = qtility.request.confirmation(
            title="Clear Bias Data",
            message="Are you sure you want to clear the bias data?",
        )
        if not confirmation:
            return
        self.option("Bias Data").set(dict())

    def save_bias_data_file(self):
        filepath = qtility.request.filepath(
            title="Save Bias Data File",
            path=os.path.dirname(cmds.file(query=True, sceneName=True)),
            save=True,
        )
        if not filepath:
            return

        bias_data = self.option("Bias Data").get()
        with open(filepath, "w") as f:
            json.dump(bias_data, f, sort_keys=True, indent=4)

    def load_bias_data_file(self):
        filepath = qtility.request.filepath(
            title="Load Bias Data File",
            path=os.path.dirname(cmds.file(query=True, sceneName=True)),
            save=False,
        )
        if not filepath:
            return

        with open(filepath, "r") as f:
            self.option("Bias Data").set(json.load(f))

    @staticmethod
    def _read_bias_data(ikh):
        point_count = cmds.getAttr(f"{ikh}.springAngleBias", size=True)
        output = []
        for i in range(point_count):
            entry = {}
            for recordable_attribute in ApplyIKBiasData._RECORDABLE_ATTRIBUTES:
                attribute = f"{ikh}.springAngleBias[{i}].{recordable_attribute}"
                entry[recordable_attribute] = cmds.getAttr(attribute)
            output.append(entry)
        return output

    @staticmethod
    def _apply_bias_data(ikh, data):
        for idx, entry in enumerate(data):
            for name, value in entry.items():
                attribute_address = f"{ikh}.springAngleBias[{idx}].{name}"
                cmds.setAttr(attribute_address, lock=False)
                cmds.setAttr(attribute_address, value)