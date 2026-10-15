"""
Provides the "Utility : Apply IK Bias Data" component, which stores the
spring angle bias data of a set of ik handles on the component and
re-applies it to those handles on every build. The data is captured from
the scene with the Snapshot Bias Data button, and can also be cleared or
saved to and loaded from json files.
"""
import os
import mref
import aniseed
import aniseed_toolkit


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
        """
        Declares the IK Handles input, the Apply Data toggle, the hidden Bias
        Data cache and the snapshot/clear/save/load button options.
        """
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
        """
        Returns an object list widget for the IK Handles input, and None for
        anything else.
        """
        if requirement_name == "IK Handles":
            return aniseed.widgets.ObjectList()
        return None

    def option_widget(self, option_name):
        """
        Returns a button widget for each of the snapshot, clear, save and load
        options (labelled with the option name), and None for anything else.
        """
        # -- Each button option shares its name with its button label
        buttons = {
            "Snapshot Bias Data": self.snapshot_bias_data,
            "Clear Bias Data": self.clear_bias_data,
            "Save Bias Data File": self.save_bias_data_file,
            "Load Bias Data File": self.load_bias_data_file,
        }
        if option_name in buttons:
            return aniseed.widgets.ButtonWidget(
                button_name=option_name,
                func=buttons[option_name],
            )

        return None

    def run(self) -> bool:
        """
        Applies the cached bias data to each ik handle in the cache that exists
        in the scene. Does nothing when Apply Data is off or the cache is empty.
        """
        if not self.option("Apply Data").get():
            return True

        stored_bias_data = self.option("Bias Data").get()

        if not stored_bias_data:
            print("no stored bias data")
            return True

        for ikh, bias_data in stored_bias_data.items():
            if not mref.objExists(ikh):
                continue
            self._apply_bias_data(ikh, bias_data)

        return True

    def snapshot_bias_data(self):
        """
        Reads the spring angle bias data from every existing handle in the IK
        Handles input and replaces the Bias Data cache with it.
        """
        data = {}
        for ikh in self.input("IK Handles").get():
            if not mref.objExists(ikh):
                continue
            data[ikh] = self._read_bias_data(ikh)
        self.option("Bias Data").set(data)

    def clear_bias_data(self):
        """
        Empties the Bias Data cache after asking the user for confirmation.
        """
        aniseed_toolkit.option_files.clear_option(
            self.option("Bias Data"),
            title="Clear Bias Data",
            message="Are you sure you want to clear the bias data?",
            empty_value=dict(),
        )

    def save_bias_data_file(self):
        """
        Prompts for a file path and writes the Bias Data cache to it as json.
        """
        aniseed_toolkit.option_files.save_json_file(
            title="Save Bias Data File",
            get_data=self.option("Bias Data").get,
        )

    def load_bias_data_file(self):
        """
        Prompts for a json file and replaces the Bias Data cache with its
        contents.
        """
        aniseed_toolkit.option_files.load_json_file(
            title="Load Bias Data File",
            option=self.option("Bias Data"),
        )

    @staticmethod
    def _read_bias_data(ikh):
        """
        Returns the spring angle bias entries of the given ik handle as a
        list of {attribute name: value} dictionaries.
        """
        point_count = mref.get(f"{ikh}.springAngleBias").get(size=True)
        return [
            {
                name: mref.get(f"{ikh}.springAngleBias[{idx}].{name}").get()
                for name in ApplyIKBiasData._RECORDABLE_ATTRIBUTES
            }
            for idx in range(point_count)
        ]

    @staticmethod
    def _apply_bias_data(ikh, data):
        """
        Applies the given spring angle bias entries to the given ik handle,
        unlocking each attribute before setting it.
        """
        for idx, entry in enumerate(data):
            for name, value in entry.items():
                attribute = mref.get(f"{ikh}.springAngleBias[{idx}].{name}")
                attribute.set(lock=False)
                attribute.set(value)
