import aniseed
import qtility
import maya.cmds as mc

from Qt import QtCore, QtWidgets, QtGui
"""
[
    {
        "driver": "bone.rotateX",
        "shape": "shape_track_name",
        "divide_by": 1.0,
        "clamp": True
    }
]
"""
class BlendShapeConnectorComponent(aniseed.RigComponent):

    identifier = "Utility : Blendshape Connector"

    def __init__(self, *args, **kwargs):
        super(BlendShapeConnectorComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="BlendShape Node",
            value="",
            description="The BlendShape Node",
        )
        self.declare_option(
            name="BlendShape Connection Data",
            value=[],
            group="Behaviour",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "BlendShape Node":
            return aniseed.widgets.ObjectSelector()

    def option_widget(self, option_name: str):
        if option_name == "BlendShape Connection Data":
            return BlendShapeEditor(component=self)

    def run(self):

        for data in self.option("BlendShape Connection Data").get():

            if not mc.objExists(data["shape"]):
                print(f'{data["shape"]} does not exist')
                continue

            if not mc.objExists(data["driver"]):
                print(f'{data["driver"]} does not exist')
                continue

            math_node = mc.createNode("floatMath")

            mc.connectAttr(
                data["driver"],
                f"{math_node}.floatA",
            )

            mc.setAttr(
                f"{math_node}.floatB",
                data["divide_by"],
            )

            mc.setAttr(
                f"{math_node}.operation",
                3,  # -- Divide
            )

            if not data["clamp"]:

                mc.connectAttr(
                    f"{math_node}.outFloat",
                    data["shape"],
                    force=True,
                )
                continue

            else:
                clamp = mc.createNode("clamp")

                mc.connectAttr(
                    f"{math_node}.outFloat",
                    f"{clamp}.inputR",
                )

                mc.setAttr(
                    f"{clamp}.minR",
                    0,
                )

                mc.setAttr(
                    f"{clamp}.maxR",
                    1,
                )

                mc.connectAttr(
                    f"{clamp}.outputR",
                    data["shape"],
                    force=True,
                )

# noinspection PyUnresolvedReferences
class BlendShapeEditor(QtWidgets.QWidget):

    changed = QtCore.Signal()

    def __init__(self, component, parent=None):
        super(BlendShapeEditor, self).__init__(parent=parent)

        self.component = component

        self.setLayout(
            QtWidgets.QVBoxLayout(),
        )

        self.table = QtWidgets.QTableWidget()

        self.table.insertColumn(0, )#"Clamp")
        self.table.insertColumn(0, )#"Multiplier")
        self.table.insertColumn(0, )#"Shape")
        self.table.insertColumn(0, )#"Driver")

        self.add_button = QtWidgets.QPushButton("+")
        self.remove_button = QtWidgets.QPushButton("-")

        self.layout().addWidget(self.table)
        self.layout().addWidget(self.add_button)
        self.layout().addWidget(self.remove_button)

        self.add_button.clicked.connect(self.add_connection_flow)
        self.remove_button.clicked.connect(self.remove_connection)

        self.table.itemChanged.connect(self.changed)

    def add_connection_flow(self):

        blendhsape_node = self.component.input("BlendShape Node").get()

        default_driver = ""
        if mc.ls(sl=True):
            default_driver = mc.ls(sl=True)[0]

        shape_names = mc.listAttr(
            f"{blendhsape_node}.w",
            multi=True,
        )

        blendshape_name = qtility.request.item(
            title="Blend Shape",
            message="Please select the shape to add",
            items=shape_names,
            parent=self,
            editable=False,
        )

        if not blendshape_name:
            return

        driver = qtility.request.text(
            title="Specify Driver",
            message=(
                "Please specify the driver, including the attribute. Such as: \n\n"
                "null.rotateX"
            ),
            text=default_driver,
            parent=self,
        )

        if not driver:
            return

        division = qtility.request.text(
            title="Specify Divide_by",
            message=(
                "You may give a value to divide_by. A value of 1 will result in a direct "
                "connection."
            ),
            text="1.0",
            parent=self,
        )

        division = float(division)

        clamp = qtility.request.confirmation(
            title="Clamp Range",
            message=(
                "Do you want to clamp this range so the shape does not exceed its "
                "zero to one value"
            ),
            parent=self,
        )

        self.add_connection(
            driver,
            f"{blendhsape_node}.{blendshape_name}",
            division,
            clamp,
        )

    def add_connection(self, driver, shape, division, clamp):

        new_row = self.table.insertRow(0)

        self.table.setItem(
            0,
            0,
            QtWidgets.QTableWidgetItem(driver),
        )
        self.table.setItem(
            0,
            1,
            QtWidgets.QTableWidgetItem(shape),
        )
        self.table.setItem(
            0,
            2,
            QtWidgets.QTableWidgetItem(str(division)),
        )
        self.table.setItem(
            0,
            3,
            QtWidgets.QTableWidgetItem(str(clamp)),
        )

        self.changed.emit()

    def remove_connection(self):

        self.table.removeRow(
            self.table.currentRow()
        )
        self.changed.emit()

    def set_value(self, value):
        for connection_data in value:
            self.add_connection(
                connection_data["driver"],
                connection_data["shape"],
                connection_data["divide_by"],
                connection_data["clamp"],
            )

    def get_value(self):
        data = list()

        for row_idx in range(self.table.rowCount()):

            if not self.table.item(0, 3):
                continue
                
            data.append(
                dict(
                    driver=self.table.item(row_idx, 0).text(),
                    shape=self.table.item(row_idx, 1).text(),
                    divide_by=float(self.table.item(row_idx, 2).text()),
                    clamp=self.table.item(row_idx, 3).text() == "True",
                )
            )

        return data
