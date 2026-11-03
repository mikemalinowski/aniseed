"""
Provides the "Utility : Transform Mixer" component, which rebuilds an
aniseed_utilities TransformMixer from stored data and connects its deformers
to the nodes they are mapped to. Option buttons allow poses and deformers
to be added and removed on the built mixer and the result stored back.
Also provides the ConstraintMappingWidget used to edit the deformer to node
mappings.

Other components can attach a mixer beneath themselves with add_to, mapping
deformers to their own outputs (addresses), as the nodes only exist once
they have built. A mapped deformer which is not in the stored data is created
when the mixer builds, matched to the node it drives.
"""
import logging
import mref
import aniseed
import qtility
import aniseed_utilities as au
from Qt import QtCore, QtWidgets

log = logging.getLogger(__name__)


class TransformMixer(aniseed.RigComponent):
    """
    Builds a transform mixer (see au.rig.pose_mixer.TransformMixer)
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

        self.declare_option(
            name="Descriptive Prefix",
            description=(
                "If given, every node of the mixer is named with the rig configuration, with this in front "
                "of its description. If not, the nodes keep the mixer's own names (transformMixer etc)."
            ),
            value="",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            description="Location token (e.g. md/lf/rt) applied to the node names, when a Descriptive Prefix is given",
            value=self.config.middle,
            group="Naming",
        )

        self.declare_option(
            name="Proxy Hosts",
            description="Nodes (or addresses) which are given a proxy of every pose attribute when the mixer builds",
            value=[],
        )

        self.declare_option(
            name="Match Deformers To Mapping",
            description=(
                "If True, every mapped deformer's space is matched to the node it drives when the mixer "
                "builds, rather than taken from the stored data. This only changes where the targets are "
                "shown, not what the poses do."
            ),
            value=False,
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

        if requirement_name == "Proxy Hosts":
            return aniseed.widgets.ObjectList()

        if requirement_name == "Location":
            return aniseed.widgets.LocationSelector(self.config, self.option(requirement_name).get())

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

    def is_valid(self) -> bool:
        """
        Checks that every deformer in the Constraint Mapping is mapped to a
        node. A mapped deformer which has not been stored is created when the
        mixer builds, so it does not need to be in the stored Data.
        """
        for constraint_data in self.option("Constraint Mapping").get() or list():
            if not constraint_data[-1]:
                log.warning(f"{self.label()} : The deformer {constraint_data[0]!r} is not mapped to a node")
                return False

        return True

    def run(self) -> bool:
        """
        Rebuilds the mixer from the stored Data, parents it under the Parent
        input and records its node name. Each mapped deformer which was not
        stored is created, matched to the node it drives (as is every mapped
        deformer if Match Deformers To Mapping is set), and its translate,
        rotate and scale are connected to that node. Finally every pose
        attribute is proxied onto each of the Proxy Hosts.
        """
        mixer = au.rig.pose_mixer.TransformMixer.deserialise(
            self.option("Data").get() or dict(),
            namer=self._namer(),
        )
        mixer.node.set_parent(self.input("Parent").get())

        self.option("Node").set(mixer.node.name())

        match_all = self.option("Match Deformers To Mapping").get()

        for constraint_data in self.option("Constraint Mapping").get() or list():
            deformer_name = constraint_data[0]
            node_name = self._resolve(constraint_data[-1])

            if not node_name or not mref.objExists(node_name):
                log.warning(f"{self.label()} : The deformer {deformer_name!r} is mapped to {node_name!r}, which does not exist")
                continue

            node_to_drive = mref.get(node_name)
            deformer_node = mixer.get_deformer(deformer_name=deformer_name)

            if not deformer_node:
                deformer_node = mixer.add_deformer(name=deformer_name)
                deformer_node.parent().match_to(node_to_drive)

            elif match_all:
                deformer_node.parent().match_to(node_to_drive)

            for attribute_name in ["translate", "rotate", "scale"]:
                deformer_node.attr(attribute_name).connect(node_to_drive.attr(attribute_name))

        pose_names = [pose.attr("pose_name").get() for pose in mixer.poses()]

        for host in self.option("Proxy Hosts").get() or list():
            host_name = self._resolve(host)

            if not host_name or not mref.objExists(host_name):
                log.warning(f"{self.label()} : The proxy host {host_name!r} does not exist")
                continue

            m_host = mref.get(host_name)
            for pose_name in pose_names:
                if m_host.has_attribute(pose_name):
                    log.warning(f"{self.label()} : {host_name} already has a {pose_name!r} attribute, so it is not proxied")
                    continue

                m_host.add_proxy(pose_name, mixer.node.attr(pose_name))

        return True

    def _namer(self):
        """
        Returns the callable which names the mixer's nodes with the rig
        configuration (mechanical, the Descriptive Prefix and Location), or
        None if there is no Descriptive Prefix
        """
        prefix = self.option("Descriptive Prefix").get()
        if not prefix:
            return None

        location = self.option("Location").get()
        return lambda label: self.config.generate_name(
            classification=self.config.mechanical,
            description=f"{prefix}{label}",
            location=location,
        )

    def _resolve(self, value):
        """
        Returns the value of the attribute the given value addresses, or the
        value itself if it is not an address.
        """
        if not value:
            return value

        attribute = self.rig.resolve_attribute(value)
        return attribute.get() if attribute else value

    @classmethod
    def add_to(
            cls,
            component,
            label: str,
            parent: str,
            mapping: list,
            proxy_hosts: list = None,
            match_deformers_to_mapping: bool = True,
            prefix: str = "",
            location: str = None,
    ):
        """
        Adds a Transform Mixer component to the stack as a child of the given
        component, with no poses. Its deformers are created when it first
        builds, matched to the nodes they are mapped to.

        Other components can reach this without importing this module, via
        ``self.rig.component_library.request("Utility : Transform Mixer").add_to(...)``.

        Args:
            component: The component to add the mixer beneath
            label: The label for the mixer component
            parent: The node (or address) to parent the mixer under
            mapping: List of (deformer name, node or address) pairs, the node
                being what the deformer drives (typically a control's offset)
            proxy_hosts: Optional nodes (or addresses) to proxy every pose
                attribute onto
            match_deformers_to_mapping: Sets the Match Deformers To Mapping
                option, so the deformers follow the nodes they drive if the
                rig changes (or is mirrored)
            prefix: Sets the Descriptive Prefix option, which names the
                mixer's nodes with the rig configuration
            location: Sets the Location option. If not given, the given
                component's Location is used (if it has one).

        Returns:
            The transform mixer component
        """
        options = {
            "Constraint Mapping": [[deformer_name, node] for deformer_name, node in mapping],
            "Proxy Hosts": list(proxy_hosts or []),
            "Match Deformers To Mapping": match_deformers_to_mapping,
            "Descriptive Prefix": prefix,
        }

        if location is None and component.option("Location") is not None:
            location = component.option("Location").get()
        if location is not None:
            options["Location"] = location

        return component.stack.add_component(
            component_type=cls.identifier,
            label=label,
            parent=component,
            inputs={
                "Parent": parent,
            },
            options=options,
        )

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

    def mixer(self) -> au.rig.pose_mixer.TransformMixer|None:
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
        return au.rig.pose_mixer.TransformMixer(mixer_node, namer=self._namer())


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
        super().__init__(parent=parent)

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
