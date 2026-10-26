"""
Provides the "Utility : Blendshape Connector" component, which drives
blendshape weights from driver attributes, each divided by a value and
optionally clamped to a zero to one range. Also provides the BlendShapeEditor
table widget used to author the connection data.
"""
import logging
import mref
import aniseed
import qtility

from Qt import QtCore, QtWidgets
from maya import cmds

log = logging.getLogger(__name__)


class BlendShapeConnectorComponent(aniseed.RigComponent):
    """
    Drives blendshape weights from driver attributes. Each driver is divided
    by a value and optionally clamped to a zero to one range before driving
    the shape.

    The connection data takes the form of:

        [
            {
                "driver": "bone.rotateX",
                "shape": "blendshape_node.shape_track_name",
                "divide_by": 1.0,
                "clamp": True
            }
        ]
    """

    identifier = "Utility : Blendshape Connector"

    def __init__(self, *args, **kwargs):
        """
        Declares the "BlendShape Node" input and the "BlendShape Connection Data"
        option, which holds the list of driver to shape connections.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="BlendShape Node",
            value="",
            validate=False,
            description="The BlendShape Node",
        )
        self.declare_option(
            name="BlendShape Connection Data",
            value=[],
            group="Behaviour",
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the "BlendShape Node" input.

        Args:
            requirement_name: The name of the input to return a widget for.
        """
        if requirement_name == "BlendShape Node":
            return aniseed.widgets.ObjectSelector()

    def option_widget(self, option_name: str):
        """
        Returns a BlendShapeEditor bound to this component for the
        "BlendShape Connection Data" option.

        Args:
            option_name: The name of the option to return a widget for.
        """
        if option_name == "BlendShape Connection Data":
            return BlendShapeEditor(component=self)

    def run(self):
        """
        For each connection entry, divides the driver by its divide_by value
        through a floatMath node, optionally clamps the result to zero to one
        through a clamp node, and force-connects it into the shape weight.
        Entries whose driver or shape does not exist are skipped with a message.
        """

        for data in self.option("BlendShape Connection Data").get():

            if not mref.objExists(data["shape"]):
                log.warning(f'{data["shape"]} does not exist, skipping')
                continue

            if not mref.objExists(data["driver"]):
                log.warning(f'{data["driver"]} does not exist, skipping')
                continue

            # -- connectAttr is used rather than Attribute.connect so that
            # -- a failed connection still raises
            math_node = mref.create("floatMath")
            mref.connectAttr(data["driver"], math_node.floatA)
            math_node.floatB.set(data["divide_by"])
            math_node.attr("operation").set(3)  # -- Divide

            output = math_node.outFloat

            if data["clamp"]:
                clamp = mref.create("clamp")
                mref.connectAttr(output, clamp.inputR)
                clamp.minR.set(0)
                clamp.maxR.set(1)
                output = clamp.outputR

            mref.connectAttr(output, data["shape"], force=True)

        return True


# noinspection PyUnresolvedReferences
class BlendShapeEditor(QtWidgets.QWidget):

    changed = QtCore.Signal()

    def __init__(self, component, parent=None):
        """
        Builds a four column table (driver, shape, divide by, clamp) with add
        and remove buttons. Edits to the table emit the changed signal.

        Args:
            component: The BlendShapeConnectorComponent being edited.
            parent: Optional parent widget.
        """
        super().__init__(parent=parent)

        self.component = component

        self.setLayout(
            QtWidgets.QVBoxLayout(),
        )

        # -- Columns are: Driver, Shape, Divide By, Clamp
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)

        self.add_button = QtWidgets.QPushButton("+")
        self.remove_button = QtWidgets.QPushButton("-")

        self.layout().addWidget(self.table)
        self.layout().addWidget(self.add_button)
        self.layout().addWidget(self.remove_button)

        self.add_button.clicked.connect(self.add_connection_flow)
        self.remove_button.clicked.connect(self.remove_connection)

        self.table.itemChanged.connect(self.changed)

    def add_connection_flow(self):
        """
        Prompts the user for a shape on the component's blendshape node, a
        driver attribute (defaulting to the name of the first selected node),
        a divide by value and whether to clamp, then adds the connection.
        Relies on the current selection for the default driver. Cancelling any
        prompt, or giving a divide by value that is not a number, aborts.
        """

        blendshape_node = self.component.input("BlendShape Node").get()

        selection = mref.selected()
        default_driver = selection[0].name() if selection else ""

        if not blendshape_node or not cmds.objExists(blendshape_node):
            qtility.request.message(
                title="Blend Shape",
                message="Please set the BlendShape Node input to an existing blendShape node first.",
                parent=self,
            )
            return

        # -- cmds rather than mref, as mref would try to wrap the returned
        # -- attribute names as nodes
        try:
            shape_names = cmds.listAttr(
                f"{blendshape_node}.w",
                multi=True,
            )

        except (RuntimeError, ValueError):
            shape_names = None

        if not shape_names:
            qtility.request.message(
                title="Blend Shape",
                message=f"{blendshape_node} has no shapes to connect.",
                parent=self,
            )
            return

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

        if division is None:
            return

        try:
            division = float(division)

        except ValueError:
            qtility.request.message(
                title="Specify Divide_by",
                message=f"{division!r} is not a number.",
                parent=self,
            )
            return

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
            f"{blendshape_node}.{blendshape_name}",
            division,
            clamp,
        )

    def add_connection(self, driver, shape, division, clamp):
        """
        Inserts a connection as a new row at the top of the table and emits
        changed. Because rows go in at the top, loading data via set_value
        reverses its order.

        Args:
            driver: The driver attribute, such as "bone.rotateX".
            shape: The blendshape weight attribute to drive.
            division: The value the driver is divided by.
            clamp: Whether the result is clamped to a zero to one range.
        """

        # -- Note that new connections are inserted at the top, so loading
        # -- data via set_value reverses its order
        self.table.insertRow(0)

        for column, value in enumerate([driver, shape, str(division), str(clamp)]):
            self.table.setItem(
                0,
                column,
                QtWidgets.QTableWidgetItem(value),
            )

        self.changed.emit()

    def remove_connection(self):
        """
        Removes the currently selected row from the table and emits changed.
        """

        self.table.removeRow(
            self.table.currentRow()
        )
        self.changed.emit()

    def set_value(self, value):
        """
        Adds a table row for each connection dictionary given. Existing rows are
        not cleared, and the rows end up in reverse order (see add_connection).

        Args:
            value: List of connection dictionaries with driver, shape, divide_by
                and clamp keys.
        """
        for connection_data in value:
            self.add_connection(
                connection_data["driver"],
                connection_data["shape"],
                connection_data["divide_by"],
                connection_data["clamp"],
            )

    def get_value(self):
        """
        Reads the table back into a list of connection dictionaries. Note that
        the completeness check tests the first row rather than each row, so every
        row is skipped if the first row is incomplete.

        Returns:
            List of dictionaries with driver, shape, divide_by and clamp keys.
        """
        data = list()

        for row_idx in range(self.table.rowCount()):

            # -- Note this tests the first row rather than row_idx, so
            # -- every row is skipped if the first row is incomplete
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
