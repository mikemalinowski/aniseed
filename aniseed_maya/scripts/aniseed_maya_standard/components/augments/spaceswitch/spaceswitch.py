"""
Provides the "Augment : Space Switch" component, which adds a "spaces" enum
attribute to a host node and switches the driven node between targets through
weighted parent (and optional scale) constraints. Also provides the widgets
used to author the spaces: SpaceList, OptionsBlock and SpaceSwitchUi. The
position only and orientation only flags apply to every space.
"""
import os
import uuid
import aniseed
import qtility
import collections
import aniseed_toolkit

from Qt import QtCore, QtWidgets


class SpaceSwitchComponent(aniseed.RigComponent):
    """
    Adds an enum "spaces" attribute to a host node and drives the
    target node through a stack of parent (and optional scale)
    constraints, switched by that attribute.

    Each "space" is a target the driven node can follow. The ``Snap
    To`` per-space option lets a space's rest pose be matched to a
    separate transform rather than the target itself. The
    ``Position Only`` / ``Orientation Only`` flags are *global* to
    the whole space switch (see :meth:`set_position_only` /
    :meth:`set_orientation_only`); they're stored per-space for
    schema-compatibility but applied across all constraints when the
    component builds.
    """

    identifier = "Augment : Space Switch"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the "To Be Driven" and "Attribute Host" inputs and the internal
        "_Data" option that stores the space configuration.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="To Be Driven",
            description="The root of the spine",
            validate=True,
            group="Required Entries",
        )
        self.declare_input(
            name="Attribute Host",
            description="What node to place the spaceswitch attribute on",
            validate=True,
            group="Required Entries",
        )

        self.declare_option(
            name="_Data",
            description=(
                "Internal storage for the space-switch configuration "
                "(list of spaces, default space, per-space target / "
                "snap-to / flags). Edited via the SpaceSwitchUi "
                "widget rather than directly."
            ),
            value=None,
            group="Behaviour",
        )

    def option_widget(self, option_name: str):
        """
        Returns the SpaceSwitchUi editor for the "_Data" option.

        Args:
            option_name: The name of the option to return a widget for.
        """
        if option_name == "_Data":
            return SpaceSwitchUi(self)

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the "To Be Driven" and "Attribute Host"
        inputs.

        Args:
            requirement_name: The name of the input to return a widget for.
        """
        if requirement_name in ("To Be Driven", "Attribute Host"):
            return aniseed.widgets.ObjectSelector(component=self)

    def run(self):
        """
        Data should take the form of:

        {
            "default_space": "",
            "spaces": [
                {
                    "target": "foobar",
                    "position_only": False,
                    "orientation_only": False,
                    "target_transform": None,
                    "label": "",
                    "include_scale": True,
                }
            ]
        }
        """

        data = self.option("_Data").get()
        node_to_drive = self.input("To Be Driven").get()
        host = self.input("Attribute Host").get()

        if not data or not node_to_drive or not host:
            return

        # -- Space targets may be addresses, so resolve them to node names
        spaces = [
            dict(
                space,
                target=self._resolve(space["target"]),
                target_transform=self._resolve(space["target_transform"]),
            )
            for space in data.get("spaces", list())
        ]

        aniseed_toolkit.rig.space.create_space_switch(
            driven=node_to_drive,
            host=host,
            spaces=spaces,
            default_space=data["default_space"],
            config=self.config,
        )

        return True

    @classmethod
    def add_to(cls, component, label: str, driven: str, default_space: str, spaces: list):
        """
        Adds a Space Switch component to the stack as a child of the given
        component. The driven node also hosts the space switch attribute.

        Other components can reach this without importing this module, via
        ``self.rig.component_library.request("Augment : Space Switch").add_to(...)``.

        Args:
            component: The component to add the space switch beneath
            label: The label for the space switch component
            driven: The address of the node to be driven
            default_space: The label of the space which should be active by default
            spaces: List of (label, target address) tuples, in the order they
                should appear

        Returns:
            The space switch component
        """
        space_switch = component.stack.add_component(
            component_type=cls.identifier,
            label=label,
            parent=component,
            inputs={
                "To Be Driven": driven,
                "Attribute Host": driven,
            },
        )
        space_switch.option("_Data").set(
            {
                "default_space": default_space,
                "spaces": [
                    {
                        "target": target,
                        "position_only": False,
                        "orientation_only": False,
                        "target_transform": "",
                        "label": space_label,
                        "include_scale": True,
                        "uuid_": str(uuid.uuid4()),
                    }
                    for space_label, target in spaces
                ]
            }
        )
        return space_switch

    def _resolve(self, value):
        """
        Returns the value of the attribute the given value addresses, or the
        value itself if it is not an address.
        """
        # -- An unset target transform is stored as None, which cannot be
        # -- resolved as an address
        if not value:
            return value

        attribute = self.rig.resolve_attribute(value)
        return attribute.get() if attribute else value

    @classmethod
    def space_template(cls):
        """
        Returns a new space dictionary with default values and a freshly
        generated uuid.
        """
        return dict(
            target="",
            label="",
            target_transform=None,
            position_only=False,
            orientation_only=False,
            include_scale=True,
            uuid_=str(uuid.uuid4()),
        )

    def get_data(self) -> dict:
        """
        Returns the stored space switch data, or an empty structure (no default
        space and no spaces) if nothing has been stored yet. The empty structure
        is not written back to the option.
        """

        data = self.option("_Data").get()

        if not data:
            return dict(
                default_space="",
                spaces=list(),
            )

        return data

    def get_uuids(self):
        """
        Returns the uuids of all stored spaces, in order.
        """

        data = self.get_data()

        return [
            n["uuid_"]
            for n in data["spaces"]
        ]

    def get_space_data(self, uuid_) -> dict:
        """
        Returns the data of the space with the given uuid, or None if there is
        no such space.

        Args:
            uuid_: The uuid of the space to look up.
        """
        for data in self.get_data()["spaces"]:
            if data["uuid_"] == uuid_:
                return data

    def remove_space(self, uuid_):
        """
        Removes the space with the given uuid and stores the result.

        Args:
            uuid_: The uuid of the space to remove.
        """

        data = self.get_data()

        for idx, space_data in enumerate(data["spaces"]):
            if space_data["uuid_"] == uuid_:
                data["spaces"].pop(idx)
                break

        self.option("_Data").set(data)

    def set_default_space(self, label):
        """
        Stores the given label as the default space.

        Args:
            label: The label of the space to make the default.
        """
        data = self.get_data()
        data["default_space"] = label

        self.option("_Data").set(data)

    def get_default_space(self):
        """
        Returns the label of the default space, or an empty string if none is set.
        """
        return self.get_data().get("default_space", "")

    def add_space(self, space_data):
        """
        Stores the given space. If a space with the same uuid already exists it
        is replaced in place, otherwise the space is appended to the end.

        Args:
            space_data: The space dictionary to store (see space_template).

        Returns:
            The updated space switch data.
        """

        uuid_ = space_data["uuid_"]
        uuids = self.get_uuids()

        if uuid_ in uuids:
            # -- Existing space — preserve its position in the list.
            index_at = uuids.index(uuid_)
            self.remove_space(uuid_)
        else:
            # -- New space — append to the end. A literal -1 here would
            # -- insert *before* the last element (list.insert(-1, x)
            # -- semantics), not append; that bug used to leave the
            # -- visible widget order out of sync with the stored order
            # -- once the option widget rebuilt itself.
            index_at = len(uuids)

        data = self.get_data()
        data["spaces"].insert(index_at, space_data)
        self.option("_Data").set(data)
        return data

    def move_space(self, uuid_, move_by):
        """
        Moves the space with the given uuid by the given number of positions and
        stores the result. Unknown uuids and moves past either end are ignored.

        Args:
            uuid_: The uuid of the space to move.
            move_by: The offset to move by, such as -1 for up or 1 for down.
        """

        data = self.get_data()

        if uuid_ not in self.get_uuids():
            return

        for idx, space_data in enumerate(data["spaces"]):

            if space_data["uuid_"] == uuid_:
                new_idx = idx + move_by

                # -- Clamp to valid range. Without this, moving the first
                # -- item up (new_idx = -1) would call list.insert(-1, x)
                # -- and silently slot it in before the last element
                # -- rather than no-op cleanly.
                if new_idx < 0 or new_idx >= len(data["spaces"]):
                    return

                data["spaces"].pop(idx)
                data["spaces"].insert(new_idx, space_data)

                self.option("_Data").set(data)
                return

    def set_position_only(self, value: bool) -> None:
        """
        Sets the ``position_only`` flag on every space at once.

        The space-switch build (see :meth:`run`) applies this flag
        globally to all constraints rather than per-space, so the
        per-space ``position_only`` entries are kept in sync by this
        helper so the UI matches what build does.
        """
        data = self.get_data()
        for space in data["spaces"]:
            space["position_only"] = bool(value)
        self.option("_Data").set(data)

    def set_orientation_only(self, value: bool) -> None:
        """
        Sets the ``orientation_only`` flag on every space at once.
        See :meth:`set_position_only` for the rationale.
        """
        data = self.get_data()
        for space in data["spaces"]:
            space["orientation_only"] = bool(value)
        self.option("_Data").set(data)


# noinspection PyUnresolvedReferences,DuplicatedCode
class SpaceList(QtWidgets.QWidget):
    """
    This shows a list of items where the user can add to it and define the order
    the items appear in the list
    """

    changed = QtCore.Signal()
    uuid_selected = QtCore.Signal(str)

    def __init__(self, component, button_size=30, parent=None):
        """
        Builds the list of spaces with add, remove, up and down buttons and
        populates it from the component's stored data.

        Args:
            component: The SpaceSwitchComponent being edited.
            button_size: The width and height of the buttons.
            parent: Optional parent widget.
        """
        super().__init__(parent=parent)

        self.component = component

        # -- Store our input values
        self._button_size = button_size

        # -- Define our base layout
        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QHBoxLayout(),
            ),
        )

        # -- Add our colour button
        self.list_widget = QtWidgets.QListWidget()
        self.layout().addWidget(self.list_widget)

        self.populate()

        self.button_layout = QtWidgets.QVBoxLayout()

        self.add_button = QtWidgets.QPushButton("+")
        self.remove_button = QtWidgets.QPushButton("-")
        self.up_button = QtWidgets.QPushButton("Up")
        self.down_button = QtWidgets.QPushButton("Dn")

        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.remove_button)
        self.button_layout.addWidget(self.up_button)
        self.button_layout.addWidget(self.down_button)
        self.layout().addLayout(self.button_layout)

        self.button_layout.addSpacerItem(
            QtWidgets.QSpacerItem(
                10,
                0,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            ),
        )

        self.layout().setStretch(0, 1)
        # -- Ensure we are initialized correctly
        self.update_size()

        # -- Hook up the events
        self.add_button.clicked.connect(self.add)
        self.remove_button.clicked.connect(self.remove)
        self.up_button.clicked.connect(self.move_up)
        self.down_button.clicked.connect(self.move_down)

        self.list_widget.currentItemChanged.connect(self.propagate_uuid_change)

    def propagate_uuid_change(self, item):
        """
        Emits uuid_selected with the uuid of the newly current item, if any.

        Args:
            item: The newly current list item.
        """
        if item:
            self.uuid_selected.emit(item.uuid_)

    def populate(self):
        """
        Clears the list and adds an item for each space stored on the component.
        """

        self.clear()
        data = self.component.option("_Data").get()

        if not data:
            return

        for space_data in data.get("spaces", list()):
            self.add(
                space_data["label"],
                space_data["uuid_"],
            )

    def clear(self):
        """
        Removes all items from the list widget. The stored data is not changed.
        """
        self.list_widget.clear()

    def add(self, label=None, uuid_=None):
        """
        Adds a space item to the list and emits changed. If no label is given
        the user is prompted for one, and if no uuid is given a new space is
        created on the component.

        Args:
            label: The label to display. Prompted for if not given.
            uuid_: The uuid of an existing space. A new space is created if not
                given.
        """
        if not label:
            label = qtility.request.text(
                title="Space Name",
                message="Please give a name for this space",
            )

        if not label:
            return

        if not uuid_:
            new_data = self.component.space_template()
            new_data["label"] = label
            uuid_ = new_data["uuid_"]
            self.component.add_space(new_data)

        item = QtWidgets.QListWidgetItem(label)
        item.uuid_ = uuid_
        self.list_widget.addItem(item)
        
        self.changed.emit()

    def remove(self):
        """
        Removes the current item from the list and its space from the component,
        then emits changed.
        """
        if not self.list_widget.currentItem():
            return

        item = self.list_widget.takeItem(
            self.list_widget.currentRow(),
        )

        self.component.remove_space(item.uuid_)
        self.changed.emit()

    def move_up(self):
        """
        Moves the current item, and its stored space, up one position and emits
        changed. Does nothing if the item is already at the top.
        """

        if not self.list_widget.currentItem():
            return

        index_to_shift = self.list_widget.currentRow()
        if index_to_shift <= 0:
            return  # already at the top

        item = self.list_widget.takeItem(index_to_shift)
        shift_by = index_to_shift - 1
        self.list_widget.insertItem(shift_by, item)
        self.component.move_space(item.uuid_, -1)
        self.list_widget.setCurrentRow(shift_by)
        self.changed.emit()

    def move_down(self):
        """
        Moves the current item, and its stored space, down one position and
        emits changed. Does nothing if the item is already at the bottom.
        """

        if not self.list_widget.currentItem():
            return

        index_to_shift = self.list_widget.currentRow()
        if index_to_shift >= self.list_widget.count() - 1:
            return  # already at the bottom

        item = self.list_widget.takeItem(index_to_shift)
        shift_by = index_to_shift + 1
        self.list_widget.insertItem(shift_by, item)
        self.component.move_space(item.uuid_, 1)
        self.list_widget.setCurrentRow(shift_by)
        self.changed.emit()

    def update_size(self):
        """
        Fixes every button to a square of the configured button size.
        """
        buttons = [
            self.add_button,
            self.remove_button,
            self.up_button,
            self.down_button,
        ]

        for button in buttons:
            button.setMinimumHeight(self._button_size)
            button.setMinimumWidth(self._button_size)
            button.setMaximumHeight(self._button_size)
            button.setMaximumWidth(self._button_size)

    def rename_current_item(self, new_name):
        """
        Sets the text of the current list item.

        Args:
            new_name: The new label to display.
        """
        self.list_widget.currentItem().setText(new_name)


# noinspection PyUnresolvedReferences
class OptionsBlock(QtWidgets.QWidget):

    label_changed = QtCore.Signal(str)

    def __init__(self, component, parent=None):
        """
        Builds the labelled widgets used to edit a single space (label, target,
        snap to, position only, orientation only, include scale and default) and
        connects each of them to serialise. Label edits also emit label_changed.

        Args:
            component: The SpaceSwitchComponent being edited.
            parent: Optional parent widget.
        """
        super().__init__(parent=parent)

        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout()
            )
        )

        self.component = component
        self._ignore_serialisation = False
        self._active_uuid = None

        self.target = aniseed.widgets.ObjectSelector(component=component)
        self.label = QtWidgets.QLineEdit()
        self.target_transform = aniseed.widgets.ObjectSelector(component=component)
        self.position_only = QtWidgets.QCheckBox()
        self.orientation_only = QtWidgets.QCheckBox()
        self.include_scale = QtWidgets.QCheckBox()
        self.is_default = QtWidgets.QCheckBox()

        widgets_to_wrap = collections.OrderedDict()

        widgets_to_wrap["Label"] = self.label
        widgets_to_wrap["Target"] = self.target
        widgets_to_wrap["Snap To"] = self.target_transform
        widgets_to_wrap["-"] = None
        widgets_to_wrap["Position Only (all spaces)"] = self.position_only
        widgets_to_wrap["Orientation Only (all spaces)"] = self.orientation_only
        widgets_to_wrap["Include Scale"] = self.include_scale
        widgets_to_wrap["--"] = None
        widgets_to_wrap["Is Default Space"] = self.is_default

        # -- Position-only / orientation-only flags are applied globally
        # -- by SpaceSwitchComponent.run (see ``set_position_only`` /
        # -- ``set_orientation_only``); the tooltip is here to make that
        # -- explicit so a user doesn't expect a per-space behaviour.
        self.position_only.setToolTip(
            "Applies to every space in this switch. Toggling here updates all spaces."
        )
        self.orientation_only.setToolTip(
            "Applies to every space in this switch. Toggling here updates all spaces."
        )

        for label, widget_to_wrap in widgets_to_wrap.items():

            if not widget_to_wrap:
                self.layout().addSpacerItem(
                    QtWidgets.QSpacerItem(
                        5,
                        5,
                        QtWidgets.QSizePolicy.Fixed,
                        QtWidgets.QSizePolicy.Fixed,
                    ),
                )

            else:
                self.layout().addLayout(
                    qtility.widgets.addLabel(
                        widget_to_wrap,
                        label,
                        150,
                        slim=False,
                    ),
                )

        qtility.derive.connect(self.label, self.serialise)
        qtility.derive.connect(self.label, self.label_changed.emit)
        qtility.derive.connect(self.target, self.serialise)
        qtility.derive.connect(self.target_transform, self.serialise)
        qtility.derive.connect(self.position_only, self.serialise)
        qtility.derive.connect(self.orientation_only, self.serialise)
        qtility.derive.connect(self.include_scale, self.serialise)
        qtility.derive.connect(self.is_default, self.serialise)

    def clear_options(self):
        """
        Resets every widget to its default value and clears the active space,
        without serialising the changes.
        """
        self._ignore_serialisation = True

        self.label.setText("")
        self.target.set_value("")
        self.target_transform.set_value("")
        self.position_only.setChecked(False)
        self.orientation_only.setChecked(False)
        self.include_scale.setChecked(True)
        self.is_default.setChecked(False)

        self._active_uuid = None
        self._ignore_serialisation = False

    def populate_options(self, uuid_):
        """
        Loads the space with the given uuid into the widgets, with serialisation
        suppressed. The position only and orientation only boxes show whether
        the flag is set on any space, since they are applied globally at build.

        Args:
            uuid_: The uuid of the space to display. Nothing is loaded if empty.
        """

        self._ignore_serialisation = True

        self._active_uuid = uuid_

        if not self._active_uuid:
            self._ignore_serialisation = False
            return

        space_data = self.component.get_space_data(self._active_uuid)

        self.label.setText(space_data["label"])
        self.target.set_value(space_data["target"])
        self.target_transform.set_value(space_data["target_transform"])

        # -- position_only and orientation_only are global at build
        # -- time; display the OR-aggregate across every space so the
        # -- UI matches build behaviour even when older saved data has
        # -- inconsistent per-space values.
        all_spaces = self.component.get_data()["spaces"]
        self.position_only.setChecked(any(s.get("position_only") for s in all_spaces))
        self.orientation_only.setChecked(any(s.get("orientation_only") for s in all_spaces))

        self.include_scale.setChecked(space_data["include_scale"])
        self.is_default.setChecked(space_data["label"] == self.component.get_default_space())

        self._ignore_serialisation = False

    def serialise(self, *args, **kwargs):
        """
        Writes the widget values back to the active space on the component,
        propagates the position only and orientation only flags to every space,
        and sets the default space if "Is Default Space" is ticked (unticking it
        does not clear the default). Does nothing while serialisation is
        suppressed or no space is active.
        """

        if self._ignore_serialisation:
            return

        if not self._active_uuid:
            return

        data = self.component.space_template()
        data["label"] = self.label.text()
        data["target"] = self.target.get_value()
        data["target_transform"] = self.target_transform.get_value()
        data["position_only"] = self.position_only.isChecked()
        data["orientation_only"] = self.orientation_only.isChecked()
        data["include_scale"] = self.include_scale.isChecked()
        data["uuid_"] = self._active_uuid

        self.component.add_space(data)

        # -- position_only and orientation_only are applied globally
        # -- across all constraints by SpaceSwitchComponent.run, so
        # -- propagate the toggle to every space's data here too.
        self.component.set_position_only(self.position_only.isChecked())
        self.component.set_orientation_only(self.orientation_only.isChecked())

        if self.is_default.isChecked():
            self.component.set_default_space(data["label"])


# noinspection PyUnresolvedReferences
class SpaceSwitchUi(QtWidgets.QWidget):

    changed = QtCore.Signal()
    dont_label = True

    def __init__(self, component, parent=None):
        """
        Combines a SpaceList with an OptionsBlock, so selecting a space shows its
        options and editing its label renames the list item. Edits are written
        directly to the component's "_Data" option by the child widgets.

        Args:
            component: The SpaceSwitchComponent being edited.
            parent: Optional parent widget.
        """
        super().__init__(parent=parent)

        self.component: SpaceSwitchComponent = component

        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout()
            )
        )

        self.text_list = SpaceList(component)
        self.options_block = OptionsBlock(component)

        self.layout().addWidget(self.text_list)

        self.layout().addSpacerItem(
            QtWidgets.QSpacerItem(
                10,
                20,
                QtWidgets.QSizePolicy.Fixed,
                QtWidgets.QSizePolicy.Fixed,
            ),
        )

        self.layout().addWidget(self.options_block)

        self.text_list.uuid_selected.connect(self.options_block.populate_options)
        self.options_block.label_changed.connect(self.text_list.rename_current_item)
