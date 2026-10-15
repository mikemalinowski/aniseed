"""
Provides the "Utility : Transform Mixer" component, which rebuilds an
aniseed_toolkit TransformMixer from stored data and connects its deformers
to the nodes they are mapped to. Option buttons allow poses and deformers
to be added and removed on the built mixer and the result stored back.
Also provides the ConstraintMappingWidget used to edit the deformer to node
mappings.
"""
import mref
import aniseed
import qtility
import aniseed_toolkit
from Qt import QtCore, QtWidgets


class TransformMixer(aniseed.RigComponent):
    """
    Builds a transform mixer (see aniseed_toolkit.transformation.TransformMixer)
    from the stored data, and connects its deformers to the nodes they are
    mapped to. The option buttons allow poses and deformers to be edited on
    the built mixer, and the result stored back into the component.
    """

    identifier = "Utility : Transform Mixer"

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent input, the hidden mixer Data and Node storage, the
        Constraint Mapping option and the pose/deformer editing button options.
        """
        super().__init__(*args, **kwargs)

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
        self.declare_option(name="Add Deformers", value=None)
        self.declare_option(name="Remove Deformer", value=None)
        self.declare_option(name="Store Data", value=None)

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the Parent input.
        """
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector()

    def option_widget(self, requirement_name: str):
        """
        Returns a ConstraintMappingWidget for the Constraint Mapping option and
        a button widget for each of the pose, deformer and Store Data options.
        """
        if requirement_name == "Constraint Mapping":
            return ConstraintMappingWidget(component=self)

        if requirement_name == "Add Pose":
            return aniseed.widgets.ButtonWidget(button_name="Add Pose", func=self.add_pose)

        if requirement_name == "Remove Pose":
            return aniseed.widgets.ButtonWidget(button_name="Remove Pose", func=self.remove_pose)

        if requirement_name == "Add Deformer":
            return aniseed.widgets.ButtonWidget(button_name="Add Deformer", func=self.add_deformer)

        if requirement_name == "Add Deformers":
            return aniseed.widgets.ButtonWidget(button_name="Add Deformers", func=self.add_deformers)

        if requirement_name == "Remove Deformer":
            return aniseed.widgets.ButtonWidget(button_name="Remove Deformer", func=self.remove_deformer)

        if requirement_name == "Store Data":
            return aniseed.widgets.ButtonWidget(button_name="Store Setup", func=self.snapshot)

    def run(self) -> bool:
        """
        Rebuilds the mixer from the stored Data, parents it under the Parent
        input, records its node name and connects the translate, rotate and
        scale of each mapped deformer to the node it drives.
        """
        mixer = aniseed_toolkit.transformation.TransformMixer.deserialise(
            self.option("Data").get(),
        )
        mixer.node.set_parent(self.input("Parent").get())

        self.option("Node").set(mixer.node.name())

        for constraint_data in self.option("Constraint Mapping").get():
            deformer_name = constraint_data[0]
            node_to_drive = mref.get(constraint_data[-1])
            deformer_node = mixer.get_deformer(deformer_name=deformer_name)

            for attribute_name in ["translate", "rotate", "scale"]:
                deformer_node.attr(attribute_name).connect(node_to_drive.attr(attribute_name))

    def add_deformers(self):
        """
        Adds a deformer for each selected node, matched to it, and adds a
        mapping from the deformer to that node. Relies on the current selection,
        which is restored afterwards.
        """

        mixer = self.mixer()

        if not mixer:
            return
        pre_selection = mref.selected()

        for selected in pre_selection:
            deformer_node = mixer.add_deformer(name="DEF_" + selected.name())

            constraint_mapping = self.option("Constraint Mapping").get()

            deformer_node.parent().match_to(selected)
            constraint_mapping.append(
                [
                    deformer_node.deformer_name.get(),
                    selected.name(),
                ],
            )

            self.option("Constraint Mapping").set(constraint_mapping)

        mref.select(pre_selection)

    def add_deformer(self):
        """
        Prompts for a name and adds a deformer of that name to the mixer. If
        something is selected, the deformer is matched to the first selected
        node and mapped to drive it. The new deformer is selected afterwards.
        """

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
        """
        Prompts the user to pick one of the mixer's deformers and removes it.
        """
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
        """
        Prompts for a name and adds a pose of that name to the mixer.
        """

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
        """
        Prompts the user to pick one of the mixer's poses and removes it.
        """

        mixer = self.mixer()

        if not mixer:
            return

        pose_name = qtility.request.item(
            items=[
                pose["name"]
                for pose in mixer.poses()
            ],
            editable=False,
            parent=None,
            title="Select Pose",
            message="Select the pose to remove",
        )

        if not pose_name:
            return

        mixer.remove_pose(pose_name)

    def snapshot(self):
        """
        Serialises the built mixer into the Data option so it rebuilds the same
        way next time.
        """

        mixer = self.mixer()

        if not mixer:
            return

        self.option("Data").set(mixer.serialise())

    def mixer(self) -> aniseed_toolkit.transformation.TransformMixer|None:
        """
        Returns the mixer built by the last build, or None (after showing an
        error message) if it does not exist.
        """

        mixer_node = self.option("Node").get()

        if not mixer_node or not mref.objExists(mixer_node):
            qtility.request.message(
                title="Error",
                message="You must build the rig before interacting with the mixer",
                parent=None,
            )
            return None
        return aniseed_toolkit.transformation.TransformMixer(mixer_node)


class ConstraintMappingWidget(QtWidgets.QWidget):
    """
    Lists the deformer -> node pairings of a Transform Mixer component,
    allowing the user to add and remove them.
    """

    changed = QtCore.Signal()
    denominator = " -> "

    def __init__(self, component, parent=None):
        """
        Builds the list widget and the Add and Remove buttons.

        Args:
            component: The Transform Mixer component the mappings belong to
            parent: Optional parent widget
        """
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
        """
        Prompts the user to pick a deformer from the built mixer and adds a
        mapping from it to each selected node, skipping any that already exist.
        Relies on the current selection.
        """
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
            parent=None,
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
        """
        Removes the selected mappings from the list.
        """
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.changed.emit()

    def set_value(self, data):
        """
        Adds a list entry for each [deformer, node] pairing in the given data.
        """
        for pairing in data:
            self.list_widget.addItem(f"{pairing[0]}{self.denominator}{pairing[1]}")

    def get_value(self):
        """
        Returns the listed mappings as [deformer, node] pairs.
        """
        return [
            self.list_widget.item(idx).text().split(self.denominator)
            for idx in range(self.list_widget.count())
        ]
