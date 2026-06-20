import mref
import aniseed
import qtility
import aniseed_toolkit
from Qt import QtCore, QtWidgets
from maya import cmds


class TransformMixer(aniseed.RigComponent):

    identifier = "Utility : Transform Mixer"

    def __init__(self, *args, **kwargs):
        super(TransformMixer, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
        )

        self.declare_option(
            name="Data",
            value={},
            hidden=True,
        )

        self.declare_option(
            name="Node",
            value="",
            hidden=True,
        )

        self.declare_option(
            name="Constraint Mapping",
            value=[],
        )

        self.declare_option(name="Add Pose", value=None)
        self.declare_option(name="Remove Pose", value=None)
        self.declare_option(name="Add Deformer", value=None)
        self.declare_option(name="Remove Deformer", value=None)
        self.declare_option(name="Store Data", value=None)

    def input_widget(self, requirement_name: str):
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector()

    def option_widget(self, requirement_name: str):
        if requirement_name == "Constraint Mapping":
            return ConstraintMappingWidget(component=self)

        if requirement_name == "Add Pose":
            return aniseed.widgets.ButtonWidget(button_name="Add Pose", func=self.add_pose)

        if requirement_name == "Remove Pose":
            return aniseed.widgets.ButtonWidget(button_name="Remove Pose", func=self.remove_pose)

        if requirement_name == "Add Deformer":
            return aniseed.widgets.ButtonWidget(button_name="Add Deformer", func=self.add_deformer)

        if requirement_name == "Remove Deformer":
            return aniseed.widgets.ButtonWidget(button_name="Remove Deformer", func=self.remove_deformer)

        if requirement_name == "Store Data":
            return aniseed.widgets.ButtonWidget(button_name="Store Setup", func=self.snapshot)

    def run(self) -> bool:
        mixer = aniseed_toolkit.transformation.TransformMixer.deserialise(
            self.option("Data").get(),
        )
        mixer.node.set_parent(self.input("Parent").get())

        self.option("Node").set(mixer.node.name())

        for constraint_data in self.option("Constraint Mapping").get():
            deformer_name = constraint_data[0]
            node_to_drive = mref.get(constraint_data[-1])
            deformer_node = mixer.get_deformer(deformer_name=deformer_name)

            deformer_node.translate.connect(node_to_drive.translate)
            deformer_node.rotate.connect(node_to_drive.rotate)
            deformer_node.scale.connect(node_to_drive.scale)




    def add_deformer(self):

        mixer = self.mixer()

        if not mixer:
            return
        pre_selection = mref.selected()

        deformer_name = qtility.request.text(
            title="Add Deformer",
            message="Give a name for the deformer",
        )

        if not deformer_name:
            return

        deformer_node = mixer.add_deformer(name=deformer_name)

        constraint_mapping = self.option("Constraint Mapping").get()

        if pre_selection:
            deformer_node.parent().match_to(pre_selection[0])
            constraint_mapping.append(
                [
                    deformer_node.deformer_name.get(),
                    pre_selection[0].name(),
                ],
            )

        self.option("Constraint Mapping").set(constraint_mapping)
        mref.select(deformer_node)
    def remove_deformer(self):
        mixer = self.mixer()

        if not mixer:
            return

        deformer_names = [
            deformer.deformer_name.get()
            for deformer in mixer.deformers()
        ]
        deformer_name = qtility.request.item(
            items=deformer_names,
            editable=False,
            parent=None,
            title="Select Deformer",
            message="Select the deformer to remove",
        )

        if not deformer_name:
            return

        mixer.remove_deformer(deformer_name)

    def add_pose(self):

        mixer = self.mixer()

        if not mixer:
            return

        pose_name = qtility.request.text(
            title="Add Pose",
            message="Give a name for the pose",
        )

        if not pose_name:
            return

        mixer.add_pose(name=pose_name)

    def remove_pose(self):

        mixer = self.mixer()

        if not mixer:
            return

        pose_name = qtility.request.item(
            items=[
                pose["name"]
                for pose in mixer.poses()
            ],
            editable=False,
            parent=self,
            title="Select Pose",
            message="Select the pose to remove",
        )

        if not pose_name:
            return

        mixer.remove_pose(pose_name)

    def snapshot(self):

        mixer = self.mixer()

        if not mixer:
            return

        self.option("Data").set(mixer.serialise())

    def mixer(self) -> aniseed_toolkit.transformation.TransformMixer|None:

        mixer_node = self.option("Node").get()

        if not mixer_node or not cmds.objExists(mixer_node):
            qtility.request.message(
                title="Error",
                message="You must build the rig before interacting with the mixer",
                parent=self,
            )
            return None
        return aniseed_toolkit.transformation.TransformMixer(mixer_node)



class ConstraintMappingWidget(QtWidgets.QWidget):

    changed = QtCore.Signal()
    denominator = " -> "
    def __init__(self, component, parent=None):
        super(ConstraintMappingWidget, self).__init__(parent=parent)

        self.component = component
        self.setLayout(QtWidgets.QVBoxLayout())

        self.list_widget = QtWidgets.QListWidget()
        self.add_button = QtWidgets.QPushButton("Add")
        self.remove_button = QtWidgets.QPushButton("Remove")

        self.layout().addWidget(self.list_widget)
        self.layout().addWidget(self.add_button)
        self.layout().addWidget(self.remove_button)

        self.add_button.clicked.connect(self.add_constraint)
        self.remove_button.clicked.connect(self.remove_constraint)

    def add_constraint(self):
        selection = mref.selected()
        mixer = self.component.mixer()

        if not mixer:
            return

        driving_deformer = qtility.request.item(
            items=[
                deformer.deformer_name.get()
                for deformer in mixer.deformers()
            ],
            editable=False,
            parent=self,
            title="Select Deformer",
            message="Select the driving deformer",
        )

        if not driving_deformer:
            return

        existing_labels = [
            self.list_widget.item(idx).text()
            for idx in range(self.list_widget.count())
        ]
        for node in selection:
            label = f"{driving_deformer}{self.denominator}{node.name()}"
            if label not in existing_labels:
                self.list_widget.addItem(label)
        self.changed.emit()
    def remove_constraint(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
            # row = self.list_widget.row(item)
            # self.list_widget.takeAt(row)
        self.changed.emit()
    def set_value(self, data):
        for pairing in data:
            self.list_widget.addItem(f"{pairing[0]}{self.denominator}{pairing[1]}")

    def get_value(self):
        results = []

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            results.append(item.text().split(self.denominator))
        # return [
        #     item.text().split(self.denominator)
        #     for item in self.list_widget.items()
        # ]
        return results

    def update_mixer_data(self, data):
        self.mixer_data = data
