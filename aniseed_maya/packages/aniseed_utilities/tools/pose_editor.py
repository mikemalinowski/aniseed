"""
The "Transform Mixer Pose Editor" Rigging Toolkit tool. It lists every pose
of a transform mixer with its live weight. Update on a pose bakes the edited
controls into that pose (see au.rig.pose_editing), and poses can be added,
reset and removed. Every change is stored straight back into the owning
component, so it survives a rebuild.

Any component can own a mixer the editor stores into, by giving its class a
mixer_options attribute: (the option naming the mixer node, the option the
mixer data is stored in). See "Utility : Transform Mixer" and "Limb : Face".
A component may also give a pose_list of the poses it always builds, which
the editor will not remove.

The Rigging Toolkit finds this tool because it is in the tools folder of the
aniseed_utilities package.
"""
import re
import logging
import functools

import mref
import qtility
import scribble
import aniseed
import aniseed_utilities as au
from aniseed import toolkits
from Qt import QtCore, QtWidgets

try:
    from shiboken6 import isValid
except ImportError:
    from shiboken2 import isValid

pose_editing = au.rig.pose_editing

log = logging.getLogger(__name__)

# -- How often the weights and edited controls are re-read (milliseconds)
REFRESH_INTERVAL_MS = 300

# -- Pose names become attribute names on the mixer node
POSE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# -- The open window, so running the tool again replaces it
_WINDOW = None

# -- Where the editor's preferences are kept (apart from the window geometry,
# -- which the window stores under its own identifier)
SETTINGS_IDENTIFIER = "TransformMixerPoseEditorSettings"


class TransformMixerPoseEditor(toolkits.Tool):
    """
    Opens the pose editor on a transform mixer, closing any one already open.
    Its icon is _res/icons/Transform Mixer Pose Editor.png in this package.
    """

    identifier = "Transform Mixer Pose Editor"
    toolkit = "Rigging"
    categories = ["Transform Mixer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Mixer Node",
            value="",
            description="The mixer node to open on. The first mixer found is used when this is empty",
        )

    def run(self) -> None:
        show(self.option("Mixer Node").get())


def show(mixer_node=""):
    """
    Opens the pose editor window, closing any one already open, and returns it.

    Args:
        mixer_node: The mixer node to open on. The first mixer found is used
            when this is empty.
    """
    global _WINDOW

    if _WINDOW is not None and isValid(_WINDOW):
        _WINDOW.close()

    _WINDOW = PoseEditorWindow(parent=qtility.windows.application())
    if mixer_node:
        _WINDOW.editor.select_mixer(mixer_node)
    _WINDOW.show()
    return _WINDOW


class MixerSource:
    """
    A mixer in the scene and the component which owns it (if any). Changes
    to the mixer are stored into that component's data option.

    Args:
        node: The mixer node (mref item)
        component: The owning component, or None
    """

    def __init__(self, node, component=None):
        self.node = node
        self.component = component
        self.mixer = self._bind()

    def _bind(self):
        """
        Returns a TransformMixer on the node. The owning component's mixer()
        is preferred, as it gives the mixer the component's namer, so poses
        added here are named as the component would name them.
        """
        if self.component and callable(getattr(self.component, "mixer", None)):
            mixer = self.component.mixer()
            if mixer:
                return mixer

        return au.rig.pose_mixer.TransformMixer(self.node)

    def label(self):
        """
        Returns the mixer's node name, followed by its owning component's label.
        """
        if self.component:
            return f"{self.node.name()} ({self.component.label()})"
        return f"{self.node.name()} (no component)"

    def built_in_poses(self):
        """
        Returns the poses the owning component always builds. These are wired
        into its control rig, so they cannot be removed.
        """
        return list(getattr(self.component, "pose_list", list()))

    def reload(self):
        """
        Binds a new TransformMixer to the node, discarding the cached pose and
        target lookups (which are stale after an undo or redo).
        """
        self.mixer = self._bind()

    def store(self):
        """
        Writes the mixer into the owning component's data option, so it is
        rebuilt the same way.
        """
        if not self.component:
            return

        data_option = self.component.mixer_options[1]
        self.component.option(data_option).set(self.mixer.serialise())


def find_mixers():
    """
    Returns a MixerSource for every transform mixer node in the scene.
    """
    owners = dict()
    for rig in aniseed.Rig.all_rigs():
        for component in rig.components():
            options = getattr(component, "mixer_options", None)

            if not options:
                continue

            node_name = component.option(options[0]).get()
            if node_name and mref.objExists(node_name):
                owners[mref.get(node_name)] = component

    return [
        MixerSource(node, owners.get(node))
        for node in mref.ls("*.deformers", "*:*.deformers", objectsOnly=True) or list()
        if node.has_attribute("poses")
    ]


class PoseEditorWindow(qtility.windows.MemorableWindow):
    """
    The window hosting the PoseEditorWidget.
    """

    def __init__(self, parent=None):
        super().__init__(storage_identifier="TransformMixerPoseEditor", parent=parent)

        self.setWindowTitle("Transform Mixer Pose Editor")
        self.editor = PoseEditorWidget(parent=self)
        self.setCentralWidget(self.editor)

    def closeEvent(self, event):
        """
        Stops the editor's refresh timer and script jobs before closing.
        """
        self.editor.shutdown()
        super().closeEvent(event)


class PoseEditorWidget(QtWidgets.QWidget):
    """
    Lists the poses of the chosen mixer with their live weights, and exposes
    Update, Select, Reset and Remove for each, plus Add Pose.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.sources = list()
        self.source = None
        self.links = list()
        self.rows = dict()
        self.row_order = tuple()

        self.setLayout(QtWidgets.QVBoxLayout())

        # -- Mixer selection
        mixer_layout = QtWidgets.QHBoxLayout()
        self.mixer_combo = QtWidgets.QComboBox()
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        mixer_layout.addWidget(QtWidgets.QLabel("Mixer"))
        mixer_layout.addWidget(self.mixer_combo, stretch=1)
        mixer_layout.addWidget(self.refresh_button)
        self.layout().addLayout(mixer_layout)

        # -- Filtering, and the controls with edits not yet baked into a pose
        filter_layout = QtWidgets.QHBoxLayout()
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("Filter poses")
        self.active_first_check = QtWidgets.QCheckBox("Active first")
        self.active_first_check.setChecked(True)
        self.only_active_check = QtWidgets.QCheckBox("Only active")
        self.mirror_check = QtWidgets.QCheckBox("Always update mirror")
        self.mirror_check.setToolTip(
            "Update also writes the mirrored edits into the mirror pose (left/right, lf/rt swapped)",
        )
        self.mirror_check.setChecked(bool(scribble.get(SETTINGS_IDENTIFIER).get("always_update_mirror", False)))
        self.edited_button = QtWidgets.QPushButton("Edited controls: 0")
        self.edited_button.setToolTip("Controls away from rest. Click to select them.")
        filter_layout.addWidget(self.filter_edit, stretch=1)
        filter_layout.addWidget(self.active_first_check)
        filter_layout.addWidget(self.only_active_check)
        filter_layout.addWidget(self.mirror_check)
        filter_layout.addWidget(self.edited_button)
        self.layout().addLayout(filter_layout)

        # -- The pose rows
        self.rows_widget = QtWidgets.QWidget()
        self.rows_widget.setLayout(qtility.layouts.slimify(QtWidgets.QVBoxLayout()))
        self.rows_widget.layout().addStretch()

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.rows_widget)
        self.layout().addWidget(scroll_area, stretch=1)

        # -- Adding poses and status
        bottom_layout = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add Pose")
        self.not_editable_label = QtWidgets.QLabel()
        bottom_layout.addWidget(self.add_button)
        bottom_layout.addWidget(self.not_editable_label, stretch=1)
        self.layout().addLayout(bottom_layout)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        self.layout().addWidget(self.status_label)

        self.mixer_combo.currentIndexChanged.connect(self.set_source)
        self.refresh_button.clicked.connect(self.populate_mixers)
        self.filter_edit.textChanged.connect(self.arrange_rows)
        self.active_first_check.toggled.connect(self.arrange_rows)
        self.only_active_check.toggled.connect(self.arrange_rows)
        self.mirror_check.toggled.connect(self.set_always_mirror)
        self.edited_button.clicked.connect(self.select_edited_controls)
        self.add_button.clicked.connect(self.add_pose)

        # -- An undo or redo of one of our edits changes the mixer behind the
        # -- component's back, so the component data is stored again. There
        # -- are no script jobs (None is returned) without the Maya ui.
        self.script_jobs = [
            job
            for job in [
                mref.scriptJob(event=["Undo", functools.partial(self.on_undo_or_redo, "redoName")]),
                mref.scriptJob(event=["Redo", functools.partial(self.on_undo_or_redo, "undoName")]),
            ]
            if job is not None
        ]

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh_values)
        self.timer.start(REFRESH_INTERVAL_MS)

        self.populate_mixers()

    # ----------------------------------------------------------------------
    def shutdown(self):
        """
        Stops the refresh timer and kills the script jobs.
        """
        self.timer.stop()

        for job in self.script_jobs:
            if mref.scriptJob(exists=job):
                mref.scriptJob(kill=job, force=True)
        self.script_jobs = list()

    # ----------------------------------------------------------------------
    def populate_mixers(self):
        """
        Finds every mixer in the scene and lists it, keeping the current one
        selected where it still exists.
        """
        current_node = self.source.node if self.source else None
        self.sources = find_mixers()

        self.mixer_combo.blockSignals(True)
        self.mixer_combo.clear()
        for source in self.sources:
            self.mixer_combo.addItem(source.label())

        index = 0
        for idx, source in enumerate(self.sources):
            if source.node == current_node:
                index = idx
        self.mixer_combo.setCurrentIndex(index)
        self.mixer_combo.blockSignals(False)

        self.set_source(index)

    # ----------------------------------------------------------------------
    def select_mixer(self, mixer_node):
        """
        Makes the given mixer node the one being edited, if it is listed.
        """
        if not mref.objExists(mixer_node):
            return

        node = mref.get(mixer_node)
        for idx, source in enumerate(self.sources):
            if source.node == node:
                self.mixer_combo.setCurrentIndex(idx)
                return

    # ----------------------------------------------------------------------
    def set_source(self, index):
        """
        Makes the mixer at the given combo index the one being edited.
        """
        self.source = self.sources[index] if 0 <= index < len(self.sources) else None
        self.build_rows()

        if not self.source:
            self.set_status("There is no transform mixer in the scene. Build the rig, then press Refresh.")
        elif not self.source.component:
            self.set_status(
                "This mixer has no owning component, so changes are not stored and are lost on rebuild.",
            )
        else:
            self.set_status("")

    # ----------------------------------------------------------------------
    def build_rows(self):
        """
        Recreates a row for each pose of the current mixer, and resolves the
        controls its deformers drive.
        """
        for row in self.rows.values():
            row.deleteLater()
        self.rows = dict()
        self.row_order = tuple()
        self.links = list()

        if not self.source:
            self.not_editable_label.setText("")
            return

        self.links = pose_editing.resolve_links(self.source.mixer)
        built_in_poses = self.source.built_in_poses()
        pose_names = [
            pose.attr("pose_name").get()
            for pose in self.source.mixer.poses()
        ]

        for pose_name in pose_names:
            weight_attribute = self.source.node.attr(pose_name)
            mirror_pose = pose_editing.mirror_name(pose_name)

            row = PoseRow(
                pose_name=pose_name,
                driven=bool(weight_attribute.inputs()),
                removable=pose_name not in built_in_poses,
                custom=bool(built_in_poses) and pose_name not in built_in_poses,
                mirror_pose=mirror_pose if mirror_pose in pose_names else "",
            )
            row.set_mirroring(self.mirror_check.isChecked())
            row.update_requested.connect(self.update_pose)
            row.select_requested.connect(self.select_pose_controls)
            row.reset_requested.connect(self.reset_pose)
            row.remove_requested.connect(self.remove_pose)
            row.weight_edited.connect(self.set_weight)
            self.rows[pose_name] = row

        not_editable = [
            f"{link.deformer_name}: {link.problem}"
            for link in self.links
            if not link.control
        ]
        self.not_editable_label.setText(
            f"{len(not_editable)} deformer(s) cannot be edited" if not_editable else "",
        )
        self.not_editable_label.setToolTip("\n".join(not_editable))

        self.refresh_values()

    # ----------------------------------------------------------------------
    def refresh_values(self):
        """
        Re-reads every pose weight and the edited controls, and rearranges
        the rows if needed. Called by the timer.
        """
        if not self.isVisible():
            return

        if self.source and not self.source.node.exists():
            self.populate_mixers()
            return

        if not self.source:
            return

        for pose_name, row in self.rows.items():
            row.set_weight(self.source.node.attr(pose_name).get())

        edited = pose_editing.edited_controls(self.links)
        self.edited_button.setText(f"Edited controls: {len(edited)}")

        self.arrange_rows()

    # ----------------------------------------------------------------------
    def arrange_rows(self):
        """
        Orders the rows (active poses first, if chosen) and hides those
        which do not match the filter.
        """
        filter_text = self.filter_edit.text().lower()
        only_active = self.only_active_check.isChecked()

        names = list(self.rows)
        if self.active_first_check.isChecked():
            names.sort(key=lambda name: not self.rows[name].is_active())

        for name, row in self.rows.items():
            row.setVisible(
                filter_text in name.lower() and (row.is_active() or not only_active),
            )

        # -- Reordering is only done when the order changes, so the rows do
        # -- not flicker on every refresh
        if tuple(names) == self.row_order:
            return

        self.row_order = tuple(names)
        layout = self.rows_widget.layout()
        for idx, name in enumerate(names):
            layout.insertWidget(idx, self.rows[name])

    # ----------------------------------------------------------------------
    def update_pose(self, pose_name):
        """
        Bakes the edited controls into the given pose and stores the result.
        """
        try:
            result = pose_editing.update_pose(
                self.source.mixer,
                pose_name,
                self.links,
                mirror=self.mirror_check.isChecked(),
            )

        except ValueError as error:
            qtility.request.message(title="Cannot Update Pose", message=str(error), parent=self)
            return

        if result.updated:
            self.source.store()
            status = f"Updated {pose_name}: {len(result.updated)} control(s) baked in."

            if result.mirrored:
                status += f" Mirrored {len(result.mirrored)} into {result.mirror_pose}."
            self.set_status(status)
        else:
            self.set_status(f"Nothing to update in {pose_name}: no control is away from rest.")

        details = [
            f"{deformer_name} skipped: {reason}"
            for deformer_name, reason in result.skipped
        ] + result.warnings

        if details:
            qtility.request.message(
                title=f"Updated {pose_name}",
                message="\n".join(details),
                parent=self,
            )

        self.refresh_values()

    # ----------------------------------------------------------------------
    def select_pose_controls(self, pose_name):
        """
        Selects the controls the given pose moves.
        """
        controls = pose_editing.pose_controls(self.source.mixer, pose_name, self.links)

        if controls:
            mref.select(controls)
        else:
            self.set_status(f"{pose_name} does not move any control yet.")

    # ----------------------------------------------------------------------
    def select_edited_controls(self):
        """
        Selects the controls holding edits which are not baked into a pose.
        """
        controls = pose_editing.edited_controls(self.links)

        if controls:
            mref.select(controls)
        else:
            self.set_status("No control is away from rest.")

    # ----------------------------------------------------------------------
    def reset_pose(self, pose_name):
        """
        Returns every target of the given pose to rest, after confirming.
        """
        confirmed = qtility.request.confirmation(
            title="Reset Pose",
            message=f"Reset {pose_name}, so that it no longer moves anything?",
            parent=self,
        )
        if not confirmed:
            return

        pose_editing.reset_pose(self.source.mixer, pose_name)
        self.source.store()
        self.set_status(f"Reset {pose_name}.")

    # ----------------------------------------------------------------------
    def remove_pose(self, pose_name):
        """
        Removes the given pose, after confirming.
        """
        confirmed = qtility.request.confirmation(
            title="Remove Pose",
            message=f"Remove {pose_name} and all of its targets?",
            parent=self,
        )
        if not confirmed:
            return

        pose_editing.remove_pose(self.source.mixer, pose_name)

        self.source.store()
        self.build_rows()
        self.set_status(f"Removed {pose_name}.")

    # ----------------------------------------------------------------------
    def add_pose(self):
        """
        Prompts for a name and adds a pose of that name, at rest.
        """
        if not self.source:
            return

        pose_name = qtility.request.text(
            title="Add Pose",
            message="Give a name for the pose",
            parent=self,
        )
        if not pose_name:
            return

        if not POSE_NAME_PATTERN.match(pose_name):
            qtility.request.message(
                title="Cannot Add Pose",
                message="A pose name can only hold letters, digits and underscores, and cannot start with a digit.",
                parent=self,
            )
            return

        if self.source.node.has_attribute(pose_name) or self.source.node.has_attribute(f"show_{pose_name}_targets"):
            qtility.request.message(
                title="Cannot Add Pose",
                message=f"The mixer already has an attribute called {pose_name}.",
                parent=self,
            )
            return

        pose_editing.add_pose(self.source.mixer, pose_name)

        self.source.store()
        self.build_rows()
        self.set_status(f"Added {pose_name}. Dial in its weight, move the controls, then press Update.")

    # ----------------------------------------------------------------------
    def set_always_mirror(self, value):
        """
        Remembers whether Update mirrors, and shows it on every row.
        """
        settings = scribble.get(SETTINGS_IDENTIFIER)
        settings["always_update_mirror"] = value
        settings.save()

        for row in self.rows.values():
            row.set_mirroring(value)

    # ----------------------------------------------------------------------
    def set_weight(self, pose_name, value):
        """
        Sets the weight of a pose whose weight is not driven.
        """
        self.source.node.attr(pose_name).set(value)

    # ----------------------------------------------------------------------
    def on_undo_or_redo(self, name_query):
        """
        When one of our edits has been undone or redone, the mixer has
        changed without the component being told, so the cached lookups are
        dropped, the rows rebuilt and the component data stored again. A step
        with no name (Maya does not always record one) is treated as ours.

        Args:
            name_query: The undoInfo query which names the step just undone
                ("redoName") or redone ("undoName")
        """
        if not self.source or not self.source.node.exists():
            return

        step_name = mref.undoInfo(query=True, **{name_query: True}) or ""
        if step_name and not step_name.startswith(pose_editing.UNDO_CHUNK_PREFIX):
            return

        self.source.reload()
        self.source.store()
        self.build_rows()

    # ----------------------------------------------------------------------
    def set_status(self, message):
        """
        Shows the given message beneath the pose list.
        """
        self.status_label.setText(message)


class PoseRow(QtWidgets.QWidget):
    """
    A single pose: its name, its weight (a bar when the weight is driven, a
    slider when it is not) and its Update, Select, Reset and Remove actions.

    Args:
        pose_name: The name of the pose
        driven: True if the pose weight has an input
        removable: True if the pose can be removed
        custom: True to mark the pose as custom
        mirror_pose: The pose Update mirrors into, or empty if there is none
    """

    update_requested = QtCore.Signal(str)
    select_requested = QtCore.Signal(str)
    reset_requested = QtCore.Signal(str)
    remove_requested = QtCore.Signal(str)
    weight_edited = QtCore.Signal(str, float)

    def __init__(self, pose_name, driven, removable, custom, mirror_pose="", parent=None):
        super().__init__(parent=parent)

        self.pose_name = pose_name
        self.mirror_pose = mirror_pose
        self.mirroring = False
        self.weight = 0.0

        self.setLayout(qtility.layouts.slimify(QtWidgets.QHBoxLayout()))

        name_label = QtWidgets.QLabel(f"{pose_name}  (custom)" if custom else pose_name)
        name_label.setMinimumWidth(220)

        if driven:
            self.weight_widget = QtWidgets.QProgressBar()
            self.weight_widget.setTextVisible(False)
        else:
            self.weight_widget = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            self.weight_widget.valueChanged.connect(self._on_slider_changed)
        self.weight_widget.setRange(0, 100)
        self.weight_widget.setFixedWidth(120)

        self.percentage_label = QtWidgets.QLabel()
        self.percentage_label.setFixedWidth(45)
        self.percentage_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.update_button = QtWidgets.QPushButton("Update")
        select_button = QtWidgets.QPushButton("Select")
        select_button.setToolTip("Select the controls this pose moves")

        menu_button = QtWidgets.QToolButton()
        menu_button.setText("...")
        menu_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(menu_button)
        menu.addAction("Reset Pose", lambda: self.reset_requested.emit(self.pose_name))
        remove_action = menu.addAction("Remove Pose", lambda: self.remove_requested.emit(self.pose_name))
        remove_action.setEnabled(removable)
        if not removable:
            remove_action.setToolTip("Built-in poses are wired into the control rig and cannot be removed")
        menu_button.setMenu(menu)

        self.layout().addWidget(name_label, stretch=1)
        self.layout().addWidget(self.weight_widget)
        self.layout().addWidget(self.percentage_label)
        self.layout().addWidget(self.update_button)
        self.layout().addWidget(select_button)
        self.layout().addWidget(menu_button)

        self.update_button.clicked.connect(lambda: self.update_requested.emit(self.pose_name))
        select_button.clicked.connect(lambda: self.select_requested.emit(self.pose_name))

    def is_active(self):
        """
        Returns True if the pose has a weight high enough to edit.
        """
        return abs(self.weight) >= pose_editing.MINIMUM_WEIGHT

    def set_weight(self, weight):
        """
        Shows the given weight, and enables Update only when it is high
        enough to edit.
        """
        self.weight = weight

        self.weight_widget.blockSignals(True)
        self.weight_widget.setValue(max(0, min(100, int(round(abs(weight) * 100)))))
        self.weight_widget.blockSignals(False)

        self.percentage_label.setText(f"{weight * 100:.0f}%")

        self.update_button.setEnabled(self.is_active())
        self.update_tooltip()

    def set_mirroring(self, value):
        """
        Sets whether Update mirrors, which the Update tooltip describes.
        """
        self.mirroring = value
        self.update_tooltip()

    def update_tooltip(self):
        """
        Describes what Update will do, or why it is disabled.
        """
        if not self.is_active():
            self.update_button.setToolTip(
                f"The pose is at {self.weight:.0%}. Push it above {pose_editing.MINIMUM_WEIGHT:.0%} to edit it.",
            )
            return

        tooltip = "Bake the edited controls into this pose"

        if self.mirroring and self.mirror_pose == self.pose_name:
            tooltip += ", mirroring each edit onto the other side of this pose"
        elif self.mirroring and self.mirror_pose:
            tooltip += f", and their mirror into {self.mirror_pose}"
        elif self.mirroring:
            tooltip += f" (there is no {pose_editing.mirror_name(self.pose_name)} pose to mirror into)"

        self.update_button.setToolTip(tooltip)

    def _on_slider_changed(self, value):
        """
        Passes a slider change on as a weight edit.
        """
        self.weight_edited.emit(self.pose_name, value / 100.0)
