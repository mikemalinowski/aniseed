import os
import uuid
import aniseed
import qtility
import collections
import aniseed_toolkit

from Qt import QtCore, QtWidgets, QtGui
import maya.cmds as mc


class SpaceSwitchComponent(aniseed.RigComponent):

    identifier = "Augment : Space Switch"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(SpaceSwitchComponent, self).__init__(*args, **kwargs)

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
            value=None,
            group="Behaviour",
        )

    def option_widget(self, option_name: str):
        if option_name == "_Data":
            return SpaceSwitchUi(self)

    def input_widget(self, requirement_name: str):
        if requirement_name == "To Be Driven":
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

        if requirement_name == "Attribute Host":
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

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
                    "label": ""

                }
            ]
        }
        """

        data = self.option("_Data").get()
        node_to_drive = self.input("To Be Driven").get()
        host = self.input("Attribute Host").get()

        if not data:
            return

        if not node_to_drive:
            return

        if not host:
            return

        aniseed_toolkit.run(
            "Add Separator Attribute",
            host,
        )

        node_to_drive = aniseed_toolkit.run(
            "Get Control",
            node_to_drive,
        )

        labels = [
            space["label"]
            for space in data.get("spaces", list())
        ]

        mc.addAttr(
            host,
            shortName="spaces",
            at="enum",
            enumName=":".join(labels),
            k=True,
        )

        orientation_only = False
        position_only = False

        default_space_idx = 0
        all_constraints = []

        for idx, space in enumerate(data.get("spaces", list())):

            if space["orientation_only"]:
                orientation_only = True

            if space["position_only"]:
                position_only = True

            target = space["target"]

            target_transform = space["target_transform"]

            matrix_to_restore = None

            if space["label"] == data["default_space"]:
                default_space_idx = idx

            maintain_offset = True

            # -- Resolve any addresses
            target_attribute = self.rig.lookup_attribute(target)
            if target_attribute:
                target = target_attribute.get()

            target_transform_attribute = self.rig.lookup_attribute(target_transform)
            if target_transform_attribute:
                target_transform = target_transform_attribute.get()

            # -- If we're given a target transform, we should move the
            # -- node to drive to this transform before constraining
            if target_transform:
                target = mc.createNode("transform")
                target = mc.rename(
                    target,
                    self.config.generate_name(
                        classification="loc",
                    description="target_point",
                        location=self.config.middle,
                    ),
                )

                matrix_to_restore = mc.xform(
                    node_to_drive.org,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                )

                mc.xform(
                    target,
                    matrix=mc.xform(
                        target_transform,
                        query=True,
                        matrix=True,
                        worldSpace=True,
                    ),
                    worldSpace=True,
                )

                maintain_offset = False

            constraints = list()

            constraints.append(
                mc.parentConstraint(
                    target,
                    node_to_drive.org,
                    # skipTranslate=["x", "y", "z"] if space["orientation_only"] else [],
                    # skipRotate=["x", "y", "z"] if space["position_only"] else [],
                    maintainOffset=maintain_offset,
                )[0]
            )

            scale_cns = None
            if space["include_scale"]:
                constraints.append(
                    mc.scaleConstraint(
                        target,
                        node_to_drive.org,
                        maintainOffset=maintain_offset,
                    )[0]
                )

            for constraint in constraints:

                condition = mc.createNode("condition")

                mc.setAttr(
                    f"{condition}.secondTerm",
                    idx,
                )

                mc.setAttr(
                    f"{condition}.colorIfTrueR",
                    1,
                )

                mc.setAttr(
                    f"{condition}.colorIfFalseR",
                    0,
                )

                mc.connectAttr(
                    f"{host}.spaces",
                    f"{condition}.firstTerm",
                )

                func = mc.parentConstraint

                if "scale" in constraint:
                    func = mc.scaleConstraint

                mc.connectAttr(
                    f"{condition}.outColorR",
                    constraint + "." + func(
                        constraint,
                        query=True,
                        weightAliasList=True
                    )[-1]
                )

            if matrix_to_restore:
                mc.xform(
                    node_to_drive.org,
                    matrix=matrix_to_restore,
                    worldSpace=True,
                )

            all_constraints.extend(constraints)

        if position_only:
            for constraint in all_constraints:
                for axis in ["X", "Y", "Z"]:
                    try:
                        mc.disconnectAttr(
                            f"{constraint}.constraintRotate.constraintRotate{axis}",
                            f"{node_to_drive.org}.rotate.rotate{axis}",
                        )

                    except: pass

        if orientation_only:
            for constraint in all_constraints:
                for axis in ["X", "Y", "Z"]:
                    try:
                        mc.disconnectAttr(
                            f"{constraint}.constraintTranslate.constraintTranslate{axis}",
                            f"{node_to_drive.org}.translate.translate{axis}",
                        )

                    except:
                        # import traceback
                        # print(traceback.print_exc())
                        # print("couldnt orient")
                        pass

        mc.setAttr(
            f"{host}.spaces",
            default_space_idx,
        )

        return True

    @classmethod
    def space_template(cls):
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

        data = self.option("_Data").get()

        if not data:
            return dict(
                default_space="",
                spaces=list(),
            )

        return data

    def get_uuids(self):

        data = self.get_data()

        return [
            n["uuid_"]
            for n in data["spaces"]
        ]

    def get_space_data(self, uuid_) -> dict:
        for data in self.get_data()["spaces"]:
            if data["uuid_"] == uuid_:
                return data

    def remove_space(self, uuid_):

        data = self.get_data()

        for idx, space_data in enumerate(data["spaces"]):
            if space_data["uuid_"] == uuid_:
                data["spaces"].pop(idx)
                break

        self.option("_Data").set(data)

    def set_default_space(self, label):
        data = self.get_data()
        data["default_space"] = label

        self.option("_Data").set(data)

    def get_default_space(self):
        return self.get_data().get("default_space", "")

    def add_space(self, space_data):

        uuid_ = space_data["uuid_"]

        if uuid_ in self.get_uuids():
            self.remove_space(uuid_)

        data = self.get_data()
        data["spaces"].append(space_data)
        self.option("_Data").set(data)
        return data

    def move_space(self, uuid_, move_by):

        data = self.get_data()

        if uuid_ not in self.get_uuids():
            return

        for idx, space_data in enumerate(data["spaces"]):

            if space_data["uuid_"] == uuid_:
                data["spaces"].pop(idx)
                data["spaces"].insert(idx + move_by, space_data)

                self.option("_Data").set(data)
                return


# noinspection PyUnresolvedReferences,DuplicatedCode
class SpaceList(QtWidgets.QWidget):
    """
    This shows a list of items where the user can add to it and define the order
    the items appear in the list
    """

    changed = QtCore.Signal()
    uuid_selected = QtCore.Signal(str)

    def __init__(self, component, button_size=30, parent=None):
        super(SpaceList, self).__init__(parent=parent)

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

        self.list_widget.currentItemChanged.connect(self.propogate_uuid_change)

    def propogate_uuid_change(self, item):
        if item:
            self.uuid_selected.emit(item.uuid_)

    def populate(self):

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
        self.list_widget.clear()

    def add(self, label=None, uuid_=None):
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
        if not self.list_widget.currentItem():
            return

        item = self.list_widget.takeItem(
            self.list_widget.currentRow(),
        )

        self.component.remove_space(item.uuid_)
        self.changed.emit()

    def move_up(self):

        if not self.list_widget.currentItem():
            return

        # -- Get the index of the process we want to shift
        index_to_shift = self.list_widget.currentRow()

        # -- Remove the process from the list
        item = self.list_widget.takeItem(index_to_shift)

        # -- Re-insert it one level less (or the same level if its at the top
        # -- of the list already)
        shift_by = min(
            index_to_shift - 1,
            self.list_widget.count(),
        )

        self.list_widget.insertItem(
            shift_by,
            item,
        )

        self.component.move_space(item.uuid_, -1)

        self.list_widget.setCurrentRow(shift_by)
        self.changed.emit()

    def move_down(self):

        if not self.list_widget.currentItem():
            return

        # -- Get the index of the process we want to shift
        index_to_shift = self.list_widget.currentRow()

        # -- Remove the process from the list
        item = self.list_widget.takeItem(index_to_shift)

        # -- Re-insert it one level less (or the same level if its at the top
        # -- of the list already)
        shift_by = max(
            index_to_shift + 1,
            0,
        )
        self.list_widget.insertItem(
            shift_by,
            item,
        )
        self.component.move_space(item.uuid_, 1)

        self.list_widget.setCurrentRow(shift_by)
        self.changed.emit()

    def update_size(self):
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
        self.list_widget.currentItem().setText(new_name)

    def get_value(self):

        result = list()

        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            result.append(item.text())

        return result

    def set_value(self, v):

        for item in v or list():
            self.list_widget.addItem(item)

        self.changed.emit()


# noinspection PyUnresolvedReferences
class OptionsBlock(QtWidgets.QWidget):

    label_changed = QtCore.Signal(str)

    def __init__(self, component, parent=None):
        super(OptionsBlock, self).__init__(parent=parent)

        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout()
            )
        )

        self.component = component
        self._ignore_serialisation = False
        self._active_uuid = None

        self.target = aniseed.widgets.everywhere.ObjectSelector(component=component)
        self.label = QtWidgets.QLineEdit()
        self.target_transform = aniseed.widgets.everywhere.ObjectSelector(component=component)
        self.position_only = QtWidgets.QCheckBox()
        self.orientation_only = QtWidgets.QCheckBox()
        self.include_scale = QtWidgets.QCheckBox()
        self.is_default = QtWidgets.QCheckBox()

        widgets_to_wrap = collections.OrderedDict()

        widgets_to_wrap["Label"] = self.label
        widgets_to_wrap["Target"] = self.target
        widgets_to_wrap["Snap To"] = self.target_transform
        widgets_to_wrap["-"] = None
        widgets_to_wrap["Position Only"] = self.position_only
        widgets_to_wrap["Orientation Only"] = self.orientation_only
        widgets_to_wrap["Include Scale"] = self.include_scale
        widgets_to_wrap["--"] = None
        widgets_to_wrap["Is Default Space"] = self.is_default

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
        self._ignore_serialisation = True

        self.label.setText("")
        self.target.set_value("")
        self.target_transform.set_value("")
        self.position_only.setChecked(False)
        self.orientation_only.setChecked(False)
        self.include_scale.setChecked(True)

        self._active_uuid = None
        self._ignore_serialisation = False

    def populate_options(self, uuid_):

        self._ignore_serialisation = True

        self._active_uuid = uuid_

        if not self._active_uuid:
            self._ignore_serialisation = False
            return

        space_data = self.component.get_space_data(self._active_uuid)

        self.label.setText(space_data["label"])
        self.target.set_value(space_data["target"])
        self.target_transform.set_value(space_data["target_transform"])
        self.position_only.setChecked(space_data["position_only"])
        self.orientation_only.setChecked(space_data["orientation_only"])
        self.include_scale.setChecked(space_data["include_scale"])
        self.is_default.setChecked(space_data["label"] == self.component.get_default_space())

        self._ignore_serialisation = False

    def serialise(self, *args, **kwargs):

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

        if self.is_default.isChecked():
            self.component.set_default_space(data["label"])


# noinspection PyUnresolvedReferences
class SpaceSwitchUi(QtWidgets.QWidget):

    changed = QtCore.Signal()
    dont_label = True

    def __init__(self, component, parent=None):
        super(SpaceSwitchUi, self).__init__(parent=parent)

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
        # self.layout().setStretch(0, 1)

        self.text_list.uuid_selected.connect(self.options_block.populate_options)
        self.options_block.label_changed.connect(self.text_list.rename_current_item)
