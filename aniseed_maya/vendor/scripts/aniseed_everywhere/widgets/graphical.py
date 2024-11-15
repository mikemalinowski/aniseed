import os
import json
import typing
import functools
import collections

import qute
from crosswalk import app


# --------------------------------------------------------------------------------------
class PickerModes:
    EDIT = 1
    USER = 2


# --------------------------------------------------------------------------------------
class VariableType:
    Options = "option"
    Requirements = "requirement"


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class GraphicalItemSelectorEditor(qute.QWidget):
    """
    This is the editing tool for creating a Graphical Item Selector. It allows a user
    to author a json file which can than be loaded.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(GraphicalItemSelectorEditor, self).__init__(parent=parent)

        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )

        # -- Add in the view, specifically in editor mode
        self.view = PickerView(mode=PickerModes.EDIT)
        self.layout().addWidget(self.view)

        self.h_layout = qute.utilities.layouts.slimify(
            qute.QHBoxLayout(),
        )
        self.layout().addLayout(self.h_layout)

        self.load_button = qute.QPushButton("Load")
        self.save_button = qute.QPushButton("Save")
        self.h_layout.addWidget(self.load_button)
        self.h_layout.addWidget(self.save_button)

        self.load_button.clicked.connect(self.load)
        self.save_button.clicked.connect(self.save)

    # ----------------------------------------------------------------------------------
    def save(self):
        """
        Saves the current view into a json file which can be later loaded
        """
        filepath = qute.utilities.request.filepath(
            title="Load Picker Graph",
            save=True,
            filter_="*.json (*.json)",
            parent=self,
        )

        if not filepath:
            return

        self.view.save(filepath)

    # ----------------------------------------------------------------------------------
    def load(self):
        """
        Loads the given json file into the view
        """
        filepath = qute.utilities.request.filepath(
            title="Load Picker Graph",
            save=False,
            filter_="*.json (*.json)",
            parent=self,
        )

        if not filepath:
            return

        self.view.load(filepath)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class GraphicalItemSelector(qute.QWidget):
    """
    This is a view which shows nodes and lines and allows the user to select and
    set the values of them.

    It is essentially a visual/graphical version of an object selector.
    """

    # -- We dont want to show the labels when this widget type is
    # -- displayed in any tools, so we use this hint
    HIDE_LABEL = True

    # ----------------------------------------------------------------------------------
    def __init__(
            self,
            component: "aniseedx.Component" = None,
            filepath: str = None,
            parent: qute.QWidget = None,
    ):
        super(GraphicalItemSelector, self).__init__(parent=parent)

        # -- Store a reference to the component we're representing
        self._component = component

        # -- Declare our layout
        self.setLayout(qute.QHBoxLayout())

        self.layout().setContentsMargins(
            30,
            30,
            30,
            30,
        )

        self.layout().addSpacerItem(
            qute.QSpacerItem(
                0,
                0,
                qute.QSizePolicy.Expanding,
                qute.QSizePolicy.Minimum,
            ),
        )

        # -- Add in our item view, specifically in user mode (not editor mode)
        self.view = PickerView(
            component,
            mode=PickerModes.USER,
        )
        self.layout().addWidget(self.view)

        # -- Ensure we're always aligning the view
        self.layout().addSpacerItem(
            qute.QSpacerItem(
                0,
                0,
                qute.QSizePolicy.Expanding,
                qute.QSizePolicy.Minimum,
            ),
        )

        # -- If we're given a filepath, load it in
        if filepath:
            self.load(filepath)

    # ----------------------------------------------------------------------------------
    def get_component(self) -> "aniseedx.Component":
        """
        Returns the active component for this widget
        """
        return self._component

    # ----------------------------------------------------------------------------------
    def load(self, file_path: str):
        """
        Loads the given file into the view
        """
        self.view.load(file_path)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class PickerView(qute.QGraphicsView):
    """
    The view manages the building of the graphics scene and the background of the view
    """

    # ----------------------------------------------------------------------------------
    def __init__(
            self,
            component: "aniseedx.Component" = None,
            mode=PickerModes.USER,
            parent=None,
    ):
        super(PickerView, self).__init__(parent=parent)

        # -- Store a reference to the component
        self._component = component

        # -- Add the scene and apply it to the view
        self.scene = PickerScene(mode=mode)
        self.setScene(self.scene)

        # -- Define our running properties
        self.background_file = None
        self.mode = mode

        # -- Ensure we're always aligning top left
        self.setAlignment(qute.Qt.AlignLeft | qute.Qt.AlignTop)

        # -- Make it pretty!
        self.setRenderHints(
            qute.QPainter.Antialiasing |
            qute.QPainter.TextAntialiasing
        )

    # ----------------------------------------------------------------------------------
    def get_component(self) -> "aniseedx.Component":
        """
        Returns the active component we're representing
        """
        return self._component

    # ----------------------------------------------------------------------------------
    def save(self, filepath: str):
        """
        Serialise the state of the view into the given filepath
        """
        data = list()
        data.append(
            {
                "background": os.path.basename(self.background_file),
                "type": "view",
            }
        )

        for item in self.scene.items():

            if isinstance(item, Clickable):
                blob = {
                    "name": item.get_label(),
                    "location": [item.scenePos().x(), item.scenePos().y()],
                    "radius": item.get_radius(),
                    "color": item.get_color(),
                    "variable_type": item.get_variable_type(),
                    "type": "circle",
                }
                data.append(blob)

            if isinstance(item, GuideLine):
                blob = {
                    "location": [item.start, item.end],
                    "thickness": item.get_thickness(),
                    "color": item.get_color(),
                    "type": "line",
                }
                data.append(blob)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

    # ----------------------------------------------------------------------------------
    def set_background(self, filepath: str):
        """
        Sets the background image of the view to the passed image (must be png)
        """
        if not os.path.exists(filepath):
            return

        # -- Store the filepath
        self.background_file = filepath

        # -- Ensure we're transparent by default
        self.setBackgroundBrush(qute.QBrush(qute.Qt.transparent))

        # -- Load in the pixmap
        background_pixmap = qute.QPixmap(self.background_file)  # .scaled(100, 100)
        self.scene.addPixmap(background_pixmap)

        # -- Set the size of the scene to match the pixmap
        self.scene.setSceneRect(
            0,
            0,
            background_pixmap.width(),
            background_pixmap.height(),
        )

        # -- Apply our sizing policy
        size_policy = qute.QSizePolicy()
        size_policy.setHorizontalPolicy(qute.QSizePolicy.Fixed)
        size_policy.setVerticalPolicy(qute.QSizePolicy.Fixed)
        size_policy.setHeightForWidth(True)
        self.setSizePolicy(size_policy)

        # -- Set our minimum size with some buffer room
        self.setMinimumWidth(background_pixmap.width() + 10)
        self.setMinimumHeight(background_pixmap.height() + 10)

    # ----------------------------------------------------------------------------------
    def load(self, file_path):
        """
        This will initialise the scene with the given filepath
        """

        # -- Clear the current scene
        self.scene.clear()

        # -- Check the filepath exists
        if not os.path.exists(file_path):
            print(f"{file_path} does not exist")
            return False

        # -- Read the data from the file
        with open(file_path, 'r') as f:
            data = json.load(f)

        # -- Resolve the background
        self.setBackgroundBrush(qute.QBrush(qute.QColor(50, 50, 50)))
        background_file = ".".join(file_path.split(".")[:-1]) + ".png"
        self.set_background(background_file)

        # -- If we're a view type then its giving us information about
        # -- how to draw the background
        for item in data:
            if item["type"] == "view":
                self.set_background(
                    os.path.join(
                        os.path.dirname(file_path),
                        item["background"],
                    ),
                )

        # -- If we're a line type we draw the lines. Note that we're doing
        # -- all the items in different passes, so we ensure the z ordering
        for item in data:

            if item["type"] == "line":
                line = GuideLine(
                    item["location"][0],
                    item["location"][1],
                    mode=self.mode,
                )
                self.scene.addItem(
                    line,
                )

                if item.get("color"):
                    line.set_color(item["color"])

                if item.get("thickness"):
                    line.set_thickness(item["thickness"])

        # -- If we're a circle type we need to draw the selector widgets
        for item in data:

            pen = qute.QPen(qute.Qt.black)
            brush = qute.QBrush(qute.Qt.red)

            if item["type"] == "circle":
                clickable = self.scene.add_clickable(
                    label=item["name"],
                    location=item["location"],
                    radius=item["radius"],
                    variable_type=item["variable_type"]
                )
                if item.get("color"):
                    clickable.set_color(item["color"])

                if item.get("variable_type"):
                    clickable.set_variable_type(item["variable_type"])


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class PickerScene(qute.QGraphicsScene):

    item_clicked = qute.Signal(str)

    # ----------------------------------------------------------------------------------
    def __init__(self, mode, parent=None):
        super(PickerScene, self).__init__(parent=parent)

        self.mode = mode
        self._opacity = 1

        self._drawing_line = None
        self._drawing_marker = None

    # ----------------------------------------------------------------------------------
    def add_clickable(
            self,
            label: str,
            location: typing.List[int],
            radius: int,
            variable_type: str
    ):
        """
        Function for adding a clickable selector element to the view.

        Note, for variable_type the entry should be either 'option' or 'requirement'
        """
        clickable = Clickable(
            label,
            location,
            radius,
            self.mode,
            variable_type,
        )
        self.addItem(clickable)

        return clickable

    # ----------------------------------------------------------------------------------
    def mousePressEvent(self, event: qute.QEvent):
        """
        Triggered when the user clicks on the clickable
        """
        super(PickerScene, self).mousePressEvent(event)

        if self._drawing_line:
            self.complete_user_line(event.pos())
            return

        if self.mouseGrabberItem():
            return

        if self.mode == PickerModes.EDIT and event.button() == qute.Qt.RightButton:
            menu = collections.OrderedDict()
            menu["Add Pick Node"] = functools.partial(
                self.user_adding_pick_node,
                event.pos(),
            )

            menu["Add Line"] = functools.partial(
                self.user_adding_line,
                event.pos(),
            )

            menu["Set Background"] = functools.partial(
                self.user_picking_background,
            )

            menu = qute.utilities.menus.menuFromDictionary(menu, parent=self.views()[0])

            menu.popup(qute.QCursor().pos())

    # ----------------------------------------------------------------------------------
    def get_view(self) -> qute.QGraphicsView:
        return self.views()[0]

    # ----------------------------------------------------------------------------------
    def user_picking_background(self):
        """
        This is a user flow that prompts the user to select an image to show
        as the background image
        """
        qute.utilities.request.message(
            title="Background Selection",
            label=(
                "Warning: Your background image MUST be in the same folder that "
                "you save your picker json too."
            ),
            parent=self.get_view(),
        )

        background_image = qute.utilities.request.filepath(
            title="Background Selection",
            filter_="*.png (*.png)",
            parent=self.get_view(),
            save=False,
        )

        self.get_view().set_background(background_image)

    # ----------------------------------------------------------------------------------
    def user_adding_line(self, pos: qute.QPoint):
        """
        This is triggered when the user wants to start adding a line. We mark the start
        point and draw a marker.
        """
        self._drawing_line = pos

        radius = 10
        self._drawing_marker = self.addEllipse(
            qute.QRectF(
                pos.x() - (radius * 0.5),
                pos.y() - (radius * 0.5),
                radius,
                radius,
            ),
            qute.QPen(qute.Qt.black),
            qute.QBrush(qute.Qt.red),
        )

    # ----------------------------------------------------------------------------------
    def complete_user_line(self, pos: qute.QPoint):
        """
        Triggered when the user has completed drawing a line, we remove the marker and
        add the line item
        """
        self.addItem(
            GuideLine(
                [
                    self._drawing_line.x(),
                    self._drawing_line.y(),
                ],
                [
                    pos.x(),
                    pos.y(),
                ],
                mode=self.mode,
            ),
        )
        self._drawing_line = None
        self.removeItem(self._drawing_marker)

    # ----------------------------------------------------------------------------------
    def user_adding_pick_node(self, pos: qute.QPoint):
        """
        This adds the user flow for when a user wants to add a pick node. It prompts
        for various input details before adding the node
        """

        label = qute.utilities.request.text(
            title="Please give a label",
            label="Please provide a label. This should be the requirement/option name",
            parent=self.views()[0],
        )

        if not label:
            return

        variable_type = qute.utilities.request.item(
            items=[
                VariableType.Requirements,
                VariableType.Options,
            ],
            label="Please select whether this is an option or a requirement",
            editable=False,
            parent=self.get_view(),
        )

        if not variable_type:
            return

        radius = qute.utilities.request.text(
            title="Node Size",
            label="Please give a node size",
            parent=self.views()[0],
        )

        radius = int(radius)

        if not radius:
            return

        self.add_clickable(
            label,
            location=[pos.x(), pos.y()],
            radius=radius,
            variable_type=variable_type,
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class GuideLine(qute.QGraphicsLineItem):
    """
    The guide line is a simple line that is drawn in the view
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, start, end, mode):
        super(GuideLine, self).__init__()

        self.start = start
        self.end = end
        self._color = [0, 0, 0]
        self._thickness = 5

        self.mode = mode
        self.setLine(
            start[0],
            start[1],
            end[0],
            end[1],
        )
        self.setPen(
            qute.QPen(
                qute.QColor(
                    self._color[0],
                    self._color[1],
                    self._color[2],
                ),
                self._thickness,
            ),
        )

    # ----------------------------------------------------------------------------------
    def update_pen(self):
        """
        Sets the pen to be the colour defined in the class properties
        """
        self.setPen(
            qute.QPen(
                qute.QColor(
                    self._color[0],
                    self._color[1],
                    self._color[2],
                    a=100,
                ),
                self._thickness,
            ),
        )
        self.update()

    # ----------------------------------------------------------------------------------
    def get_color(self) -> typing.List[int]:
        """
        Returns the colour of the line
        """
        return self._color

    # ----------------------------------------------------------------------------------
    def get_thickness(self) -> int:
        """
        Returns the thickness of the line
        """
        return self._thickness

    # ----------------------------------------------------------------------------------
    def set_color(self, color: typing.List[int]):
        """
        Sets the colour of the line
        """
        self._color = color
        self.update_pen()

    # ----------------------------------------------------------------------------------
    def set_thickness(self, thickness: int):
        """
        Sets the thickness of the line
        """
        self._thickness = thickness
        self.update_pen()

    # ----------------------------------------------------------------------------------
    def user_set_color(self):
        """
        This is the user flow where they are prompted for a colour. It is then
        applied to the line
        """
        color = qute.QColorDialog.getColor(
            parent=self.get_view(),
        )
        self.set_color(
            [
                color.red(),
                color.green(),
                color.blue(),
            ],
        )

    # ----------------------------------------------------------------------------------
    def user_set_thickness(self):
        """
        This is the user flow where they are prompted to give a line thickness
        """
        thickness = qute.utilities.request.text(
            title="Thickness",
            label="Set how many pixels thick the line should be",
            parent=self.scene().views()[0],
        )

        if not thickness:
            return

        thickness = int(thickness)

        if thickness < 1:
            return

        self.set_thickness(thickness)

    # ----------------------------------------------------------------------------------
    def user_delete(self):
        """
        This is the user flow for deleting a line
        """
        confirmation = qute.utilities.request.confirmation(
            title="Delete Line",
            label="Are you sure you want to delete this line?",
            parent=self.get_view(),
        )

        if confirmation:
            self.scene().removeItem(self)

    # ----------------------------------------------------------------------------------
    def get_view(self):
        """
        Returns the view this line belongs to
        """
        return self.scene().views()[0]

    # ----------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        """
        Triggered whenever the mouse is pressed on the node. This will also
        cause a trigger of the variou click signals

        :param event: The event information
        :type event: QMouseEvent

        :return: None
        """
        if self.mode == PickerModes.EDIT and event.button() == qute.Qt.RightButton:
            menu = collections.OrderedDict()
            menu["Set Thickness"] = functools.partial(
                self.user_set_thickness,
            )

            menu["Set Color"] = functools.partial(
                self.user_set_color,
            )

            menu["Delete"] = functools.partial(
                self.user_delete,
            )
            menu = qute.utilities.menus.menuFromDictionary(
                menu,
                parent=self.get_view(),
            )

            menu.popup(qute.QCursor().pos())


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class Clickable(qute.QGraphicsEllipseItem):
    """
    This is the main item type of the graphical view. It is used to represent an
    option or requirement
    """
    # ----------------------------------------------------------------------------------
    def __init__(
            self,
            label: str,
            location: typing.List[int],
            radius: int,
            mode: int = PickerModes.USER,
            variable_type: str = VariableType.Requirements,
    ):
        super(Clickable, self).__init__()

        self._label = label
        self._mode = mode
        self._radius = radius
        self._color = [55, 55, 255]
        self._variable_type = variable_type

        self.setPos(
            location[0],
            location[1],
        )

        self.set_label(label)

        self.set_radius(radius)
        self._is_hovering = False
        self.setAcceptHoverEvents(True)

        self._initialise_shadow()

        if self._mode == PickerModes.EDIT:
            self.setFlag(qute.QGraphicsItem.ItemIsMovable)

    # ----------------------------------------------------------------------------------
    def set_radius(self, radius: int):
        """
        Sets the clickables radius
        """
        self._radius = radius

        self.setRect(
            qute.QRectF(
                -(radius * 0.5),
                -(radius * 0.5),
                radius,
                radius,
            ),
        )

    # ----------------------------------------------------------------------------------
    def get_mode(self) -> int:
        """
        Returns the mode in which this is operating (i.e, User or Edit)
        """
        return self._mode

    # ----------------------------------------------------------------------------------
    def get_variable_type(self) -> str:
        """
        Returns the variable type defined for this clickable, such as option or
        requirement
        """
        return self._variable_type

    # ----------------------------------------------------------------------------------
    def set_variable_type(self, variable_type: str):
        """
        Sets whether this is an option or requirement
        """
        self._variable_type = variable_type

    # ----------------------------------------------------------------------------------
    def get_label(self) -> str:
        """
        Returns the label/name of this clickable
        """
        return self._label

    # ----------------------------------------------------------------------------------
    def get_radius(self) -> int:
        """
        Returns the radius if the clickable
        """
        return self._radius

    # ----------------------------------------------------------------------------------
    def get_color(self) -> typing.List[int]:
        """
        Returns the colour of the clickable
        """
        return self._color

    # ----------------------------------------------------------------------------------
    # noinspection PyUnresolvedReferences
    def paint(self, painter, option, widget):
        """
        This is where we draw the actual clickable
        """
        alpha = (0.5 if self._is_hovering else 0.2) * 255
        painter_path = qute.QPainterPath()
        painter_path.addEllipse(self.rect())

        if self._is_hovering:
            color = qute.QColor(
                self._color[0],
                self._color[1],
                self._color[2],
                a=0.8 * 255
            )

        else:
            color = qute.QColor(
                self._color[0],
                self._color[1],
                self._color[2],
                a=0.4 * 255
            )

        brush = qute.QBrush(color)
        painter.fillPath(painter_path, brush)

        color = qute.Qt.black

        if not self.get_value():
            color = qute.Qt.red

        painter.strokePath(
            painter_path,
            qute.QPen(
                color,
                3,
            ),
        )

    # ----------------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def hoverEnterEvent(self, *args, **kwargs):
        """
        Triggered when the mouse enters the bounds of the widget

        :return:
        """
        self._is_hovering = True
        self.update()
        qute.QToolTip.showText(qute.QCursor().pos(), self.tooltip_text())

    # ----------------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def hoverLeaveEvent(self, *args, **kwargs):
        """
        Triggered when the mouse leaves the bounds of a widget
        """
        self._is_hovering = False
        self.update()
        qute.QToolTip.hideText()

    # ----------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        """
        Triggered whenever the mouse is pressed on the node. This will also
        cause a trigger of the various click signals
        """
        button = event.button()
        mode = self.get_mode()

        if mode == PickerModes.USER and button == qute.Qt.LeftButton:

            menu = collections.OrderedDict()
            menu["Set from Selection"] = functools.partial(
                self.set_from_selection,
            )

            menu["Select in Scene"] = functools.partial(
                self.select,
            )

            menu = qute.utilities.menus.menuFromDictionary(
                menu,
                parent=self.get_view(),
            )

            menu.popup(qute.QCursor().pos())

        elif mode == PickerModes.EDIT and button == qute.Qt.RightButton:

            menu = collections.OrderedDict()

            menu["Set Variable Destination"] = functools.partial(
                self.user_set_label,
            )

            menu["Set Radius"] = functools.partial(
                self.user_set_radius,
            )

            menu["Set Color"] = functools.partial(
                self.user_set_color,
            )

            menu["Delete"] = functools.partial(
                self.user_delete,
            )

            menu = qute.utilities.menus.menuFromDictionary(
                menu,
                parent=self.get_view(),
            )

            menu.popup(qute.QCursor().pos())

    # ----------------------------------------------------------------------------------
    def get_value(self) -> typing.Any:
        """
        Returns the value of the option/requirement this represents
        """
        if not self.get_view():
            return None

        component = self.get_view().get_component()

        if not component:
            return None

        if self.get_variable_type() == VariableType.Options:
            return component.option(self.get_label()).get()

        elif self.get_variable_type() == VariableType.Requirements:
            return component.requirement(self.get_label()).get()

        return None

    # ----------------------------------------------------------------------------------
    def tooltip_text(self) -> str:
        """
        Returns a formatted text string to use as the tooltip
        """
        value = self.get_value() or ""
        return f"{self._label} {value} ({self.get_variable_type()})"

    # ----------------------------------------------------------------------------------
    def set_color(self, color: typing.List[int]):
        """
        Sets the colour of the clickable
        """
        self._color = color
        self.update()

    # ----------------------------------------------------------------------------------
    def set_label(self, label: str):
        """
        Sets the label of the clickable
        """
        self._label = label

    # ----------------------------------------------------------------------------------
    def user_set_label(self):
        """
        Defines the user flow for setting the label of the clickable
        """
        variable_name = qute.utilities.request.text(
            title="Change Label",
            label="Please provide a new variable name",
            parent=self.get_view(),
        )

        if not variable_name:
            return

        variable_type = qute.utilities.request.item(
            items=[
                VariableType.Requirements,
                VariableType.Options,
            ],
            label="Please select whether this is an option or a requirement",
            editable=False,
            parent=self.get_view(),
        )

        if not variable_type:
            return

        self.set_label(variable_name)
        self.set_variable_type(variable_type)

    # ----------------------------------------------------------------------------------
    def user_set_color(self):
        """
        Defines the user flow for setting the colour of the clickable
        """
        color = qute.QColorDialog.getColor(
            parent=self.get_view(),
        )

        self.set_color(
            [
                color.red(),
                color.green(),
                color.blue(),
            ]
        )

    # ----------------------------------------------------------------------------------
    def user_set_radius(self):
        """
        Defines the user flow for setting the radius of the clickable
        """
        radius = qute.utilities.request.text(
            title="Node Size",
            label="Please give a node size",
            parent=self.get_view(),
        )

        radius = int(radius)

        if not radius:
            return

        self.set_radius(radius)

    # ----------------------------------------------------------------------------------
    def user_delete(self):
        """
        This is the user flow for deleting the clickable
        """
        confirmation = qute.utilities.request.confirmation(
            title="Delete Line",
            label="Are you sure you want to delete this line?",
            parent=self.get_view(),
        )

        if confirmation:
            self.scene().removeItem(self)

    # ----------------------------------------------------------------------------------
    def get_view(self) -> qute.QGraphicsView or None:
        """
        Returns the view this item belongs to
        """
        try:
            return self.scene().views()[0]
        except: pass

        return None

    # ----------------------------------------------------------------------------------
    def set_from_selection(self):
        """
        Sets the value of the option/requirement based on the selection
        """
        component = self.get_view().get_component()

        if self.get_variable_type() == VariableType.Options:
            component.option(
                self.get_label()
            ).set(
                [
                    app.objects.get_name(n)
                    for n in app.selection.selected()
                ]
            )

        elif self.get_variable_type() == VariableType.Requirements:
            value = None

            if app.selection.selected():
                value = app.selection.selected()[0]

            component.requirement(self.get_label()).set(value)

        self.update()

    # ----------------------------------------------------------------------------------
    def select(self):
        """
        Selects the item in the scene with the name of the given label
        """
        if not mc:
            return

        component = self.get_view().get_component()
        result = None
        if self.get_variable_type() == VariableType.Requirements:
            result = component.requirement(self.get_label()).get()

        elif self.get_variable_type() == VariableType.Options:
            result = component.option(self.get_label()).get()

        if not result:
            return

        try:
            app.selection.select(result)

        except RuntimeError:
            print(f"Could not select {result}")

    # --------------------------------------------------------------------------
    def _initialise_shadow(self):
        """
        Allows a shadow to be drawn under the node

        :param enable: If true the shadow will be drawn, otherwise any shadow
            will be removed
        :type enable: bool

        :return: None
        """
        # -- Instance a new shadow effect
        effect = qute.QGraphicsDropShadowEffect()

        # -- Set the shadow properties
        effect.setBlurRadius(self._radius * 0.2)
        effect.setOffset(
            self._radius * 0.1,
            self._radius * 0.1,
        )
        effect.setColor(
            qute.QColor(
                0,
                0,
                0,
                a=100,
            )
        )

        # -- Apply the shadow
        self.setGraphicsEffect(effect)


# # --------------------------------------------------------------------------------------
# # noinspection PyUnresolvedReferences
# class DockableGrapgicalEditorApp(MayaQWidgetDockableMixin, qute.QMainWindow):
#     """
#     This is the main window for the editor - which allows it to be dockable
#     in maya
#     """
#     OBJECT_NAME = "DockableGraphgicalEditorApp"
#
#     def __init__(self, *args, **kwargs):
#         super(DockableGrapgicalEditorApp, self).__init__(*args, **kwargs)
#
#         # -- Set the window properties
#         self.setObjectName(self.OBJECT_NAME)
#         self.setWindowTitle('Graphical Editor')
#
#         # -- Apply our styling, defining some differences
#         qute.applyStyle(
#             [
#                 'space',
#             ],
#             self,
#         )
#
#         self.setCentralWidget(
#             GraphicalItemSelectorEditor(parent=self),
#         )


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnusedLocal
def launch(*args, **kwargs):
    """
    This function should be called to invoke the app ui in maya
    """
    #
    # # -- Clear out any pre-existing window
    # if mc.window(DockableGrapgicalEditorApp.OBJECT_NAME, exists=True):
    #     mc.deleteUI(DockableGrapgicalEditorApp.OBJECT_NAME)
    #     try:
    #         mc.deleteUI(f"{DockableGrapgicalEditorApp.OBJECT_NAME}WorkspaceControl")
    #
    #     except:
    #         pass

    # -- Instance the tool
    window = DockableGrapgicalEditorApp(
        parent=qute.utilities.windows.mainWindow(),
    )

    # -- Ensure its correctly docked in the ui
    window.show()
    #
    # mc.workspaceControl(
    #     f'{DockableGrapgicalEditorApp.OBJECT_NAME}WorkspaceControl',
    #     ttc=["AttributeEditor", -1],
    #     wp="preferred",
    #     mw=150,
    # )
