import os
import aniseed
import maya.cmds as mc


class StoreIKBiasData(aniseed.RigComponent):

    identifier = "Utility : Store IK Bias Data"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(StoreIKBiasData, self).__init__(*args, **kwargs)

        self.declare_input(
            name="IK Handles",
            value=[],
            validate=True,
        )

        self.declare_option(
            name="Store",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Cache",
            value=dict(),
            hidden=True,
        )

    def input_widget(self, requirement_name: str) :
        if requirement_name == "IK Handles":
            return aniseed.widgets.ObjectList()
        return None

    def run(self) -> bool:

        data = dict()

        for node in self.input("IK Handles").get():
            if not mc.objExists(node):
                continue

            data[node] = self.read_bias_data(node)
        if data:
            self.option("Cache").set(data)

        return True

    @classmethod
    def read_bias_data(cls, ikh):
        point_count = mc.getAttr(f"{ikh}.springAngleBias", size=True)
        recordable_attributes = ['springAngleBias_Position',
                                 'springAngleBias_FloatValue',
                                 'springAngleBias_Interp']

        output = []

        for i in range(point_count):
            data = dict()
            for recordable_attribute in recordable_attributes:
                attribute = f"{ikh}.springAngleBias[{i}].{recordable_attribute}"
                data[recordable_attribute] = mc.getAttr(attribute)
            output.append(data)
        return output


class ApplyIKBiasData(aniseed.RigComponent):
    identifier = "Utility : Apply IK Bias Data"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(ApplyIKBiasData, self).__init__(*args, **kwargs)

    def input_widget(self, requirement_name: str):
        if requirement_name == "IK Handles":
            return aniseed.widgets.ObjectList()
        return None

    def run(self) -> bool:

        stored_bias_data = dict()

        # -- Find the store component so we can extract the data
        for component in self.rig.components():
            if isinstance(component, StoreIKBiasData):
                stored_bias_data: dict = component.option("Cache").get()

        if not stored_bias_data:
            print("no stored bias data")
            return True

        for node, bias_data in stored_bias_data.items():
            self.apply_bias_data(node, bias_data)

        return True

    @classmethod
    def apply_bias_data(cls, ikh, data):

        for idx, data in enumerate(data):
            for name, value in data.items():
                attribute_address = f"{ikh}.springAngleBias[{idx}].{name}"
                mc.setAttr(attribute_address, lock=False)
                mc.setAttr(f"{ikh}.springAngleBias[{idx}].{name}", value)
                # mc.setAttr(attribute_address, lock=True)