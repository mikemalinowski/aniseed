"""
The "Matrix Mixer Pose Editor" Rigging Toolkit tool. It lists every pose of
a matrix mixer with its live weight. To edit a pose, dial it in, move the
driven objects, and press Update: the moves are baked into the pose (see
au.rig.matrix_mixer_editing) and the objects zeroed. Poses can also be
added, soloed, mirrored, reset and removed, driven objects added and
removed, and the whole mixer saved to and loaded from json. Every change is
stored straight back into the owning component, so it survives a rebuild.

Any component can own a mixer the editor stores into, by giving its class a
mixer_options attribute: (the option naming the mixer node, the option the
mixer data is stored in). See "Utility : Matrix Mixer". It may also give a
mixer_driven_option naming the option which lists the driven objects, a
pose_list of the poses it always builds, which the editor will not remove,
and mixer_fixed_driven = True if its driven objects are set by the component
itself (as the face's are), which hides adding and removing them.

The Rigging Toolkit finds this tool because it is in the tools folder of the
aniseed_utilities package.
"""
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

matrix_mixer = au.rig.matrix_mixer
editing = au.rig.matrix_mixer_editing

log = logging.getLogger(__name__)

# -- How often the weights and edited objects are re-read (milliseconds)
REFRESH_INTERVAL_MS = 300

# -- The open window, so running the tool again replaces it
_WINDOW = None

# -- Where the editor's preferences are kept (apart from the window geometry,
# -- which the window stores under its own identifier)
SETTINGS_IDENTIFIER = "MatrixMixerPoseEditorSettings"


class MatrixMixerPoseEditor(toolkits.Tool):
    """
    Opens the pose editor on a matrix mixer, closing any one already open.
    Its icon is _res/icons/Matrix Mixer Pose Editor.png in this package.
    """

    identifier = "Matrix Mixer Pose Editor"
    toolkit = "Rigging"
    categories = ["Matrix Mixer"]

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
    to the mixer are stored into that component.

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
        Returns a MatrixMixer on the node. The owning component's mixer() is
        preferred, as it gives the mixer the component's namer, so nodes made
        here are named as the component would name them.
        """
        if self.component and callable(getattr(self.component, "mixer", None)):
            mixer = self.component.mixer(silent=True)
            if mixer:
                return mixer

        return matrix_mixer.MatrixMixer(self.node)

    def label(self):
        """
        Returns the mixer's node name, followed by its owning component's label.
        """
        if self.component:
            return f"{self.node.name()} ({self.component.label()})"
        return f"{self.node.name()} (no component)"

    def built_in_poses(self):
        """
        Returns the poses the owning component always builds, which cannot be
        removed.
        """
        return list(getattr(self.component, "pose_list", list()))

    def reload(self):
        """
        Binds a new MatrixMixer to the node.
        """
        self.mixer = self._bind()

    def stored_data(self):
        """
        Returns the data stored in the owning component, or an empty
        dictionary if there is no component.
        """
        if not self.component:
            return dict()

        return self.component.option(self.component.mixer_options[1]).get() or dict()

    def data(self):
        """
        Returns the mixer's data, including the stored poses of driven
        objects which are not built, so nothing is lost when it is saved.
        """
        return matrix_mixer.merge_unbound(self.mixer.serialise(), self.stored_data())

    def store(self, keep_unbound=True, previous=None):
        """
        Writes the mixer into the owning component's data option (and its
        driven objects into its driven option), so it is rebuilt the same way.

        Args:
            keep_unbound: Keep the poses of driven objects which are not
                built. False when a driven object was removed on purpose.
            previous: The data to keep those poses from (such as a loaded
                file). If not given, the component's stored data is used.
        """
        if not self.component:
            return

        if previous is None:
            previous = self.stored_data()

        data = self.mixer.serialise()
        if keep_unbound:
            data = matrix_mixer.merge_unbound(data, previous)

        self.component.option(self.component.mixer_options[1]).set(data)

        driven_option = getattr(self.component, "mixer_driven_option", "")
        driven_list = getattr(self.component, "driven_list", None)
        if driven_option and callable(driven_list):
            self.component.option(driven_option).set(driven_list(self.mixer))


def find_mixers():
    """
    Returns a MixerSource for every matrix mixer node in the scene.
    """
    owners = dict()
    for rig in aniseed.Rig.all_rigs():
        for component in rig.components():
            options = getattr(component, "mixer_options", None)

            if not options:
                continue

            node_name = component.option(options[0]).get()
            if matrix_mixer.MatrixMixer.is_mixer(node_name):
                owners[mref.get(node_name)] = component

    return [
        MixerSource(node, owners.get(node))
        for node in matrix_mixer.find_mixers()
    ]


class PoseEditorWindow(qtility.windows.MemorableWindow):
    """
    The window hosting the PoseEditorWidget.
    """

    def __init__(self, parent=None):
        super().__init__(storage_identifier="MatrixMixerPoseEditor", parent=parent)

        self.setWindowTitle("Matrix Mixer Pose Editor")
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
    Update, Solo, Select, Mirror, Reset and Remove for each, plus Add Pose
    and the driven objects panel.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.sources = list()
        self.source = None
        self.links = list()
        self.rows = dict()
        self.row_order = tuple()

        # -- While a pose is soloed: (its name, {pose name: weight before})
        self.solo = None

        self.setLayout(QtWidgets.QVBoxLayout())

        # -- Mixer selection
        mixer_layout = QtWidgets.QHBoxLayout()
        self.mixer_combo = QtWidgets.QComboBox()
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        mixer_layout.addWidget(QtWidgets.QLabel("Mixer"))
        mixer_layout.addWidget(self.mixer_combo, stretch=1)
        mixer_layout.addWidget(self.refresh_button)
        self.layout().addLayout(mixer_layout)

        # -- Filtering, and the objects with edits not yet baked into a pose
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
        self.edited_button = QtWidgets.QPushButton("Edited: 0")
        self.edited_button.setToolTip("Driven objects away from rest. Click to select them.")
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

        # -- The driven objects, collapsed by default
        self.driven_group = QtWidgets.QGroupBox("Driven Objects")
        self.driven_group.setCheckable(True)
        self.driven_group.setChecked(False)
        self.driven_group.setLayout(QtWidgets.QVBoxLayout())

        self.driven_list = QtWidgets.QListWidget()
        self.driven_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        driven_buttons = QtWidgets.QHBoxLayout()
        self.add_driven_button = QtWidgets.QPushButton("Add Selected")
        self.remove_driven_button = QtWidgets.QPushButton("Remove")
        self.select_driven_button = QtWidgets.QPushButton("Select")
        driven_buttons.addWidget(self.add_driven_button)
        driven_buttons.addWidget(self.remove_driven_button)
        driven_buttons.addWidget(self.select_driven_button)
        driven_buttons.addStretch()

        self.driven_contents = QtWidgets.QWidget()
        self.driven_contents.setLayout(qtility.layouts.slimify(QtWidgets.QVBoxLayout()))
        self.driven_contents.layout().addWidget(self.driven_list)
        self.driven_contents.layout().addLayout(driven_buttons)
        self.driven_contents.setVisible(False)
        self.driven_group.layout().addWidget(self.driven_contents)
        self.layout().addWidget(self.driven_group)

        # -- Adding poses, and storing, saving and loading the data
        bottom_layout = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add Pose")
        self.not_editable_label = QtWidgets.QLabel()
        self.store_button = QtWidgets.QPushButton("Store to Component")
        self.store_button.setToolTip(
            "Store the mixer into its component, so it rebuilds this way. Every edit made here is "
            "already stored; use this after changing the mixer by other means.",
        )
        self.save_button = QtWidgets.QPushButton("Save JSON...")
        self.save_button.setToolTip("Save the mixer's poses to a json file")
        self.load_button = QtWidgets.QPushButton("Load JSON...")
        self.load_button.setToolTip(
            "Replace the mixer's poses with those in a json file",
        )
        self.mirror_mixer_button = QtWidgets.QPushButton("Mirror to Other Side")
        bottom_layout.addWidget(self.add_button)
        bottom_layout.addWidget(self.not_editable_label, stretch=1)
        bottom_layout.addWidget(self.mirror_mixer_button)
        bottom_layout.addWidget(self.store_button)
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(self.load_button)
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
        self.edited_button.clicked.connect(self.select_edited)
        self.add_button.clicked.connect(self.add_pose)
        self.driven_group.toggled.connect(self.driven_contents.setVisible)
        self.add_driven_button.clicked.connect(self.add_selected_driven)
        self.remove_driven_button.clicked.connect(self.remove_driven)
        self.select_driven_button.clicked.connect(self.select_driven)
        self.mirror_mixer_button.clicked.connect(self.mirror_to_other_side)
        self.store_button.clicked.connect(self.store_to_component)
        self.save_button.clicked.connect(self.save_json)
        self.load_button.clicked.connect(self.load_json)

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
        Ends any solo, stops the refresh timer and kills the script jobs.
        """
        self.end_solo()
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
        self.end_solo()
        self.source = self.sources[index] if 0 <= index < len(self.sources) else None
        self.build_rows()

        # -- A component whose driven objects come from its own structure
        # -- (such as the face's skeleton) cannot store added or removed ones
        fixed = bool(self.source and getattr(self.source.component, "mixer_fixed_driven", False))
        self.add_driven_button.setVisible(not fixed)
        self.remove_driven_button.setVisible(not fixed)

        self.update_mirror_mixer_button()

        if not self.source:
            self.set_status("There is no matrix mixer in the scene. Build the rig, then press Refresh.")
        elif not self.source.component:
            self.set_status(
                "This mixer has no owning component, so changes are not stored and are lost on rebuild.",
            )
        else:
            self.set_status("")

    # ----------------------------------------------------------------------
    def build_rows(self):
        """
        Recreates a row for each pose of the current mixer, and lists its
        driven objects.
        """
        for row in self.rows.values():
            row.deleteLater()
        self.rows = dict()
        self.row_order = tuple()
        self.links = list()
        self.driven_list.clear()

        if not self.source:
            self.not_editable_label.setText("")
            return

        mixer = self.source.mixer
        self.links = editing.resolve_links(mixer)
        built_in_poses = self.source.built_in_poses()
        pose_names = mixer.pose_names()

        for link in self.links:
            item = QtWidgets.QListWidgetItem(
                link.key if link.node.name() == link.key else f"{link.key}  ({link.node.name()})",
            )
            item.setData(QtCore.Qt.UserRole, link.index)
            if not link.editable:
                item.setToolTip(f"Cannot be edited: {link.problem}")
            self.driven_list.addItem(item)

        for pose_name in pose_names:
            mirror_pose = editing.mirror_name(pose_name)

            row = PoseRow(
                pose_name=pose_name,
                driven=bool(mixer.weight_attribute(pose_name).inputs()),
                removable=pose_name not in built_in_poses,
                custom=bool(built_in_poses) and pose_name not in built_in_poses,
                mirror_pose=mirror_pose if mirror_pose in pose_names else "",
            )
            row.set_mirroring(self.mirror_check.isChecked())
            row.update_requested.connect(self.update_pose)
            row.solo_requested.connect(self.toggle_solo)
            row.select_requested.connect(self.select_pose_driven)
            row.mirror_requested.connect(self.mirror_pose)
            row.reset_requested.connect(self.reset_pose)
            row.remove_requested.connect(self.remove_pose)
            row.weight_edited.connect(self.set_weight)
            self.rows[pose_name] = row

        not_editable = [
            f"{link.key}: {link.problem}"
            for link in self.links
            if not link.editable
        ]
        self.not_editable_label.setText(
            f"{len(not_editable)} driven object(s) cannot be edited" if not_editable else "",
        )
        self.not_editable_label.setToolTip("\n".join(not_editable))

        self.refresh_values()

    # ----------------------------------------------------------------------
    def refresh_values(self):
        """
        Re-reads every pose weight and the edited objects, and rearranges
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
            if not self.source.node.has_attribute(pose_name):
                continue
            row.set_weight(self.source.mixer.weight_attribute(pose_name).get())
            row.set_soloed(bool(self.solo) and self.solo[0] == pose_name)

        edited = editing.edited_nodes(self.links)
        self.edited_button.setText(f"Edited: {len(edited)}")

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
        Bakes the moved driven objects into the given pose and stores the
        result.
        """
        try:
            result = editing.update_pose(
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
            status = f"Updated {pose_name}: {len(result.updated)} object(s) baked in."

            if result.mirrored:
                status += f" Mirrored {len(result.mirrored)} into {result.mirror_pose}."
            self.set_status(status)
        else:
            self.set_status(f"Nothing to update in {pose_name}: no driven object is away from rest.")

        self.show_details(f"Updated {pose_name}", result)
        self.refresh_values()

    # ----------------------------------------------------------------------
    def show_details(self, title, result):
        """
        Shows the skipped objects and warnings of an UpdateResult, if any.
        """
        details = [
            f"{key} skipped: {reason}"
            for key, reason in result.skipped
        ] + result.warnings

        if details:
            qtility.request.message(title=title, message="\n".join(details), parent=self)

    # ----------------------------------------------------------------------
    def toggle_solo(self, pose_name):
        """
        Solos the given pose (its weight to one, every other undriven pose to
        zero), or ends the solo if it is already soloed. Ending a solo puts
        the weights back.
        """
        soloed = self.solo[0] if self.solo else None
        self.end_solo()

        if soloed == pose_name:
            return

        mixer = self.source.mixer
        weights = {}

        for name in mixer.pose_names():
            attribute = mixer.weight_attribute(name)
            if attribute.inputs():
                continue

            weights[name] = attribute.get()
            attribute.set(1.0 if name == pose_name else 0.0)

        self.solo = (pose_name, weights)
        self.set_status(f"Soloing {pose_name}. Press Solo again to put the other weights back.")
        self.refresh_values()

    # ----------------------------------------------------------------------
    def end_solo(self):
        """
        Puts back the weights changed by a solo, if one is active.
        """
        if not self.solo:
            return

        _, weights = self.solo
        self.solo = None

        if not self.source or not self.source.node.exists():
            return

        for name, weight in weights.items():
            if self.source.node.has_attribute(name):
                attribute = self.source.mixer.weight_attribute(name)
                if not attribute.inputs():
                    attribute.set(weight)

    # ----------------------------------------------------------------------
    def select_pose_driven(self, pose_name):
        """
        Selects the driven objects the given pose moves.
        """
        nodes = self.source.mixer.pose_driven(pose_name)

        if nodes:
            mref.select(nodes)
        else:
            self.set_status(f"{pose_name} does not move anything yet.")

    # ----------------------------------------------------------------------
    def select_edited(self):
        """
        Selects the driven objects holding edits which are not baked into a
        pose.
        """
        nodes = editing.edited_nodes(self.links)

        if nodes:
            mref.select(nodes)
        else:
            self.set_status("No driven object is away from rest.")

    # ----------------------------------------------------------------------
    def mirror_pose(self, pose_name):
        """
        Writes the whole pose, mirrored, into its mirror pose, after
        confirming.
        """
        target = editing.mirror_name(pose_name)

        confirmed = qtility.request.confirmation(
            title="Paste Mirror",
            message=f"Overwrite {target} with a mirror of {pose_name}?",
            parent=self,
        )
        if not confirmed:
            return

        try:
            result = editing.mirror_pose(self.source.mixer, pose_name, self.links)

        except ValueError as error:
            qtility.request.message(title="Cannot Paste Mirror", message=str(error), parent=self)
            return

        self.source.store()
        self.set_status(f"Mirrored {pose_name} into {target}.")
        self.show_details(f"Mirrored {pose_name}", result)

    # ----------------------------------------------------------------------
    def opposite_source(self):
        """
        Returns the MixerSource whose node name is the current mixer's with
        its side tokens swapped (left/right, lf/rt), or None if there is none.
        """
        if not self.source:
            return None

        name = editing.mirror_name(self.source.node.name())
        if name == self.source.node.name():
            return None

        for source in self.sources:
            if source.node.name() == name:
                return source
        return None

    # ----------------------------------------------------------------------
    def update_mirror_mixer_button(self):
        """
        Enables Mirror to Other Side only when there is a mixer on the other
        side, and describes what it will do.
        """
        opposite = self.opposite_source()
        self.mirror_mixer_button.setEnabled(bool(opposite))

        if opposite:
            self.mirror_mixer_button.setToolTip(
                f"Overwrite the poses of {opposite.node.name()} with a mirror of this mixer's poses, "
                f"creating any it does not have",
            )
        elif self.source and editing.mirror_name(self.source.node.name()) != self.source.node.name():
            self.mirror_mixer_button.setToolTip(
                f"There is no mixer called {editing.mirror_name(self.source.node.name())}",
            )
        else:
            self.mirror_mixer_button.setToolTip("This mixer has no side (left/right, lf/rt) in its name")

    # ----------------------------------------------------------------------
    def mirror_to_other_side(self):
        """
        Writes every pose of this mixer, mirrored, into the mixer on the
        other side, after confirming, and stores that mixer into its
        component.
        """
        target = self.opposite_source()
        if not target:
            return

        confirmed = qtility.request.confirmation(
            title="Mirror to Other Side",
            message=f"Overwrite the poses of {target.node.name()} with a mirror of {self.source.node.name()}?",
            parent=self,
        )
        if not confirmed:
            return

        self.end_solo()

        try:
            result = editing.mirror_to_mixer(self.source.mixer, target.mixer, source_links=self.links)

        except ValueError as error:
            qtility.request.message(title="Cannot Mirror", message=str(error), parent=self)
            return

        target.store()

        status = f"Mirrored {len(result.poses)} pose(s) into {target.node.name()}"
        if result.created:
            status += f", creating {len(result.created)}"
        if not target.component:
            status += ". It has no owning component, so this is lost on rebuild"
        self.set_status(status + ".")

        details = [
            f"{key} skipped: {reason}"
            for key, reason in result.skipped
        ] + result.warnings
        if result.created:
            details.append("Created poses: " + ", ".join(result.created))

        if details:
            qtility.request.message(title="Mirrored to Other Side", message="\n".join(details), parent=self)

    # ----------------------------------------------------------------------
    def reset_pose(self, pose_name):
        """
        Empties the given pose, after confirming.
        """
        confirmed = qtility.request.confirmation(
            title="Reset Pose",
            message=f"Reset {pose_name}, so that it no longer moves anything?",
            parent=self,
        )
        if not confirmed:
            return

        editing.reset_pose(self.source.mixer, pose_name)
        self.source.store()
        self.set_status(f"Reset {pose_name}.")

    # ----------------------------------------------------------------------
    def remove_pose(self, pose_name):
        """
        Removes the given pose, after confirming.
        """
        confirmed = qtility.request.confirmation(
            title="Remove Pose",
            message=f"Remove {pose_name}?",
            parent=self,
        )
        if not confirmed:
            return

        if self.solo and self.solo[0] == pose_name:
            self.end_solo()

        editing.remove_pose(self.source.mixer, pose_name)

        self.source.store()
        self.build_rows()
        self.set_status(f"Removed {pose_name}.")

    # ----------------------------------------------------------------------
    def add_pose(self):
        """
        Prompts for a name and adds an empty pose of that name.
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

        try:
            editing.add_pose(self.source.mixer, pose_name)

        except ValueError as error:
            qtility.request.message(title="Cannot Add Pose", message=str(error), parent=self)
            return

        self.source.store()
        self.build_rows()
        self.set_status(f"Added {pose_name}. Dial in its weight, move the driven objects, then press Update.")

    # ----------------------------------------------------------------------
    def add_selected_driven(self):
        """
        Makes the mixer drive the selected nodes.
        """
        if not self.source:
            return

        selected = mref.selected()
        if not selected:
            self.set_status("Select the nodes to drive.")
            return

        problems = editing.add_driven(self.source.mixer, selected)

        self.source.store()
        self.build_rows()
        mref.select(selected)

        if problems:
            qtility.request.message(
                title="Add Driven",
                message="\n".join(f"{name}: {reason}" for name, reason in problems),
                parent=self,
            )

    # ----------------------------------------------------------------------
    def remove_driven(self):
        """
        Stops the mixer driving the driven objects selected in the list,
        after confirming. Their poses are removed with them.
        """
        links = self.selected_links()
        if not links:
            return

        confirmed = qtility.request.confirmation(
            title="Remove Driven",
            message=f"Stop driving {len(links)} object(s)? Their poses are removed with them.",
            parent=self,
        )
        if not confirmed:
            return

        editing.remove_driven(self.source.mixer, [link.node for link in links])

        self.source.store(keep_unbound=False)
        self.build_rows()

    # ----------------------------------------------------------------------
    def select_driven(self):
        """
        Selects the driven objects selected in the list (or all of them).
        """
        links = self.selected_links() or self.links
        if links:
            mref.select([link.node for link in links])

    # ----------------------------------------------------------------------
    def selected_links(self):
        """
        Returns the DrivenLinks selected in the driven objects list.
        """
        indices = [
            item.data(QtCore.Qt.UserRole)
            for item in self.driven_list.selectedItems()
        ]
        return [
            link
            for link in self.links
            if link.index in indices
        ]

    # ----------------------------------------------------------------------
    def store_to_component(self):
        """
        Stores the mixer into its owning component.
        """
        if not self.source:
            return

        if not self.source.component:
            self.set_status("This mixer has no owning component to store into.")
            return

        self.source.store()
        self.set_status(f"Stored the mixer into {self.source.component.label()}.")

    # ----------------------------------------------------------------------
    def save_json(self):
        """
        Asks for a file and saves the mixer's data to it as json.
        """
        if not self.source:
            return

        path = qtility.request.filepath(
            title="Save Matrix Mixer",
            save=True,
            path=self.last_json_path(),
            filter_="JSON (*.json)",
            parent=self,
        )
        if not path:
            return

        try:
            editing.write_data_file(path, self.source.data())

        except OSError as error:
            qtility.request.message(title="Cannot Save", message=str(error), parent=self)
            return

        self.remember_json_path(path)
        self.set_status(f"Saved {len(self.source.mixer.pose_names())} pose(s) to {path}.")

    # ----------------------------------------------------------------------
    def load_json(self):
        """
        Asks for a json file and, after confirming, replaces the mixer's
        poses with those in it, storing the result into the component.
        Poses for objects the mixer does not drive are kept in the
        component, as they are on a rebuild.
        """
        if not self.source:
            return

        path = qtility.request.filepath(
            title="Load Matrix Mixer",
            save=False,
            path=self.last_json_path(),
            filter_="JSON (*.json)",
            parent=self,
        )
        if not path:
            return

        try:
            data = editing.read_data_file(path)

        except (OSError, ValueError) as error:
            qtility.request.message(title="Cannot Load", message=str(error), parent=self)
            return

        confirmed = qtility.request.confirmation(
            title="Load Matrix Mixer",
            message=(
                f"Replace the poses of {self.source.node.name()} with the "
                f"{len(data.get('poses', list()))} pose(s) in {path}?"
            ),
            parent=self,
        )
        if not confirmed:
            return

        self.end_solo()

        try:
            missing = editing.load_data(self.source.mixer, data, keep_poses=self.source.built_in_poses())

        except ValueError as error:
            qtility.request.message(title="Cannot Load", message=str(error), parent=self)
            self.build_rows()
            return

        self.source.store(previous=data)
        self.remember_json_path(path)
        self.build_rows()
        self.set_status(f"Loaded {path}.")

        if missing:
            kept = " (they are kept in the component)" if self.source.component else ""
            qtility.request.message(
                title="Loaded",
                message=(
                    f"These have poses in the file but are not driven by this mixer, so their poses "
                    f"were not applied{kept}:\n" + "\n".join(missing)
                ),
                parent=self,
            )

    # ----------------------------------------------------------------------
    @staticmethod
    def last_json_path():
        """
        Returns the json file last saved or loaded, or an empty string.
        """
        return scribble.get(SETTINGS_IDENTIFIER).get("last_json_path", "") or ""

    # ----------------------------------------------------------------------
    @staticmethod
    def remember_json_path(path):
        """
        Remembers the json file last saved or loaded, to start the next file
        dialog there.
        """
        settings = scribble.get(SETTINGS_IDENTIFIER)
        settings["last_json_path"] = path
        settings.save()

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
        self.source.mixer.weight_attribute(pose_name).set(value)

    # ----------------------------------------------------------------------
    def on_undo_or_redo(self, name_query):
        """
        When one of our edits has been undone or redone, the mixer has
        changed without the component being told, so the rows are rebuilt
        and the component data stored again. A step with no name (Maya does
        not always record one) is treated as ours.

        Args:
            name_query: The undoInfo query which names the step just undone
                ("redoName") or redone ("undoName")
        """
        if not self.source or not self.source.node.exists():
            return

        step_name = mref.undoInfo(query=True, **{name_query: True}) or ""
        if step_name and not step_name.startswith(editing.UNDO_CHUNK_PREFIX):
            return

        self.source.reload()
        self.source.store(keep_unbound=not step_name.endswith("Remove Driven"))
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
    slider when it is not) and its Update, Solo, Select, Mirror, Reset and
    Remove actions.

    Args:
        pose_name: The name of the pose
        driven: True if the pose weight has an input
        removable: True if the pose can be removed
        custom: True to mark the pose as custom
        mirror_pose: The pose Update mirrors into, or empty if there is none
    """

    update_requested = QtCore.Signal(str)
    solo_requested = QtCore.Signal(str)
    select_requested = QtCore.Signal(str)
    mirror_requested = QtCore.Signal(str)
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
        self.solo_button = QtWidgets.QPushButton("Solo")
        self.solo_button.setCheckable(True)
        self.solo_button.setToolTip(
            "Set this pose to 100% and every other (undriven) pose to 0%. Press again to put them back.",
        )
        self.solo_button.setEnabled(not driven)
        select_button = QtWidgets.QPushButton("Select")
        select_button.setToolTip("Select the driven objects this pose moves")

        menu_button = QtWidgets.QToolButton()
        menu_button.setText("...")
        menu_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(menu_button)

        mirror_action = menu.addAction(
            f"Paste Mirror into {mirror_pose}" if mirror_pose and mirror_pose != pose_name else "Paste Mirror",
            lambda: self.mirror_requested.emit(self.pose_name),
        )
        mirror_action.setEnabled(bool(mirror_pose) and mirror_pose != pose_name)

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
        self.layout().addWidget(self.solo_button)
        self.layout().addWidget(select_button)
        self.layout().addWidget(menu_button)

        self.update_button.clicked.connect(lambda: self.update_requested.emit(self.pose_name))
        self.solo_button.clicked.connect(lambda: self.solo_requested.emit(self.pose_name))
        select_button.clicked.connect(lambda: self.select_requested.emit(self.pose_name))

    def is_active(self):
        """
        Returns True if the pose has a weight high enough to edit.
        """
        return abs(self.weight) >= editing.MINIMUM_WEIGHT

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

    def set_soloed(self, value):
        """
        Shows whether this pose is the soloed one.
        """
        self.solo_button.blockSignals(True)
        self.solo_button.setChecked(value)
        self.solo_button.blockSignals(False)

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
                f"The pose is at {self.weight:.0%}. Push it above {editing.MINIMUM_WEIGHT:.0%} to edit it.",
            )
            return

        tooltip = "Bake the moved driven objects into this pose"

        if self.mirroring and self.mirror_pose == self.pose_name:
            tooltip += ", mirroring each edit onto the other side of this pose"
        elif self.mirroring and self.mirror_pose:
            tooltip += f", and their mirror into {self.mirror_pose}"
        elif self.mirroring:
            tooltip += f" (there is no {editing.mirror_name(self.pose_name)} pose to mirror into)"

        self.update_button.setToolTip(tooltip)

    def _on_slider_changed(self, value):
        """
        Passes a slider change on as a weight edit.
        """
        self.weight_edited.emit(self.pose_name, value / 100.0)
