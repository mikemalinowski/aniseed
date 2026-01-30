import os
from Qt import QtWidgets, QtGui, QtCore

from . import resources


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class ComponentItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    This delegate defines how we draw out components in the tree view.
    """

    bfr = 5
    STATUS_WIDTH = 10

    # ----------------------------------------------------------------------------------
    def __init__(self, stack: "xstack.Stack", app_config, parent=None):
        super(ComponentItemDelegate, self).__init__(parent)

        # -- When we instance this class, we need to construct all our brushes
        self.icon_pixmap = QtGui.QPixmap(
            app_config.component_icon or resources.get("component.png")
        )

        self.root_icon_pixmap = QtGui.QPixmap(
            app_config.icon or resources.get("icon.png"),
        )

        self.app_config = app_config
        self.stack: "xstack.Stack" = stack

        self.item_size = self.app_config.item_size
        self.border_pen = QtGui.QPen(QtGui.QColor(*self.app_config.border_color))
        self.text_pen = QtGui.QPen(QtGui.QColor(*self.app_config.default_text_color))
        self.drag_target_pen = QtGui.QPen(QtGui.QColor(*self.app_config.drag_target_color))
        self.drag_target_pen.setWidth(self.app_config.drop_target_width)

        self.success_brush = QtGui.QBrush(QtGui.QColor(*self.app_config.status_success_color))
        self.failed_brush = QtGui.QBrush(QtGui.QColor(*self.app_config.status_failed_color))
        self.invalid_brush = QtGui.QBrush(QtGui.QColor(*self.app_config.status_invalid_color))
        self.unknown_brush = QtGui.QBrush(QtGui.QColor(*self.app_config.status_unknown_color))
        self.disabled_brush = QtGui.QBrush(QtGui.QColor(*self.app_config.status_disabled_color))

        self.text_font = QtGui.QFont(
            self.app_config.text_font,
            self.app_config.text_size,
            QtGui.QFont.Normal,
        )
        self.descriptive_pen = QtGui.QPen(
            QtGui.QColor(
                self.app_config.default_text_color[0],
                self.app_config.default_text_color[1],
                self.app_config.default_text_color[2],
                150.
            )
        )
    # ----------------------------------------------------------------------------------
    def paint_status(self, component, painter, option, index):
        """
        Draws the status section of the widget
        """
        status = component.status()

        if status == self.stack.status.Success:
            status_color = self.success_brush

        elif status == self.stack.status.Failed:
            status_color = self.failed_brush

        elif status == self.stack.status.Invalid:
            status_color = self.invalid_brush

        elif status == self.stack.status.Disabled:
            status_color = self.disabled_brush

        else:
            status_color = self.unknown_brush

        painter.setBrush(status_color)
        painter.setPen(self.border_pen)

        painter.drawRect(
            QtCore.QRect(
                option.rect.x(),
                option.rect.y(),
                self.STATUS_WIDTH,
                option.rect.height(),
            ),
        )

    # ----------------------------------------------------------------------------------
    def paint_border(self, component, painter, option, index):
        """
        Draws the border
        """
        painter.setPen(self.border_pen)
        painter.setBrush(QtCore.Qt.transparent)
        painter.drawRect(
            option.rect,
        )

    # ----------------------------------------------------------------------------------
    def paint_text(self, component, painter, option, index):
        """
        Draws the text label
        """
        painter.setFont(self.text_font)
        painter.setPen(self.text_pen)

        start_point = sum(
            [
                option.rect.x(),
                self.item_size,
                self.bfr,
                self.STATUS_WIDTH,
                self.bfr,
            ],
        )
        # -- Draw the main entry name
        painter.drawText(
            start_point,
            option.rect.y() + 25,
            f"{component.label()}"
        )
        start_point += QtGui.QFontMetrics(self.text_font).horizontalAdvance(component.label())

        version_info = ""

        if component.forced_version():
            version_info = f" v{component.forced_version()}"

        painter.setPen(self.descriptive_pen)
        painter.drawText(
            start_point + self.bfr,
            option.rect.y() + 25,
            f"({component.identifier}{version_info})"
        )
    # ----------------------------------------------------------------------------------
    def paint_icon(self, component, painter, option, index):
        """
        Paints the icon
        """
        # -- Build the pixmap
        if component.icon and os.path.exists(component.icon):
            pixmap = QtGui.QPixmap(component.icon).scaled(
                self.item_size,
                self.item_size,
                mode=QtCore.Qt.SmoothTransformation,
            )

        else:
            pixmap = self.icon_pixmap.scaled(
                self.item_size,
                self.item_size,
                mode=QtCore.Qt.SmoothTransformation,
            )

        # -- Draw the icon
        painter.drawPixmap(
            QtCore.QRect(
                option.rect.x() + self.STATUS_WIDTH + self.bfr,
                option.rect.y(),
                self.item_size,
                self.item_size,
            ),
            pixmap,
        )

    # ----------------------------------------------------------------------------------
    def paint_highlight(self, component, painter, option, index):
        """
        Paints the background based on the overlay state
        """
        gradient = QtGui.QLinearGradient(
            QtCore.QPoint(
                option.rect.x(),
                option.rect.y(),
            ),
            QtCore.QPoint(
                option.rect.x() + option.rect.width(),
                option.rect.y(),
            ),
        )

        # -- Add extra details for the selected item
        if option.state & QtWidgets.QStyle.State_Selected:
            gradient.setColorAt(0, QtGui.QColor(255, 255, 255, a=75))
            gradient.setColorAt(1, QtGui.QColor(255, 255, 255, a=0))

        elif option.state & QtWidgets.QStyle.State_MouseOver:
            gradient.setColorAt(0, QtGui.QColor(255, 255, 255, a=50))
            gradient.setColorAt(1, QtGui.QColor(255, 255, 255, a=0))

        else:
            gradient.setColorAt(0, QtGui.QColor(255, 255, 255, a=25))
            gradient.setColorAt(1, QtGui.QColor(255, 255, 255, a=0))

        painter.fillRect(
            option.rect,
            gradient
        )

    # ----------------------------------------------------------------------------------
    def paint_stack_node(self, painter, option, index):
        """
        The only item we paint differently is the stack node
        """
        # -- Paint the icon
        pixmap = self.root_icon_pixmap.scaled(
            self.item_size,
            self.item_size,
            mode=QtCore.Qt.SmoothTransformation,
        )

        # -- Draw the icon
        painter.drawPixmap(
            QtCore.QRect(
                option.rect.x(),
                option.rect.y(),
                self.item_size,
                self.item_size,
            ),
            pixmap,
        )

        painter.setFont(self.text_font)
        painter.setPen(self.text_pen)

        # -- Draw the main entry name
        if self.app_config.header_label is not None:
            label = self.app_config.header_label
        else:
            label =  f"{self.app_config.label} : {self.stack.label}"

        painter.drawText(
            option.rect.x() + self.item_size + self.bfr + self.STATUS_WIDTH,
            option.rect.y() + 25,
            label
        )

        gradient = QtGui.QLinearGradient(
            QtCore.QPoint(
                option.rect.x(),
                option.rect.y(),
            ),
            QtCore.QPoint(
                option.rect.x(),
                option.rect.y() + option.rect.height(),
            ),
        )

        gradient.setColorAt(0, QtGui.QColor(255, 255, 255, a=25))
        gradient.setColorAt(1, QtGui.QColor(255, 255, 255, a=0))

        painter.setBrush(
            gradient
        )
        painter.setPen(QtGui.QPen(QtCore.Qt.transparent))
        painter.drawRect(
            option.rect,
        )

    # ----------------------------------------------------------------------------------
    def paint(self, painter, option, index):
        """
        This is called when the item requires repainting
        """

        if not index.column() == 0:
            return

        component_uuid = index.data(role=QtCore.Qt.DisplayRole)
        component = self.stack.component(component_uuid)

        if not component:
            self.paint_stack_node(painter, option, index)
            return

        self.paint_highlight(component, painter, option, index)

        self.paint_status(component, painter, option, index)

        self.paint_icon(component, painter, option, index)

        self.paint_text(component, painter, option, index)

        self.paint_border(component, painter, option, index)

        painter.setPen(self.drag_target_pen)
    # ----------------------------------------------------------------------------------
    def sizeHint(self, option, index):
        return QtCore.QSize(1, self.item_size)
