"""
The toolkit window: an xstack app showing a ToolkitStack, set up so the user
can run tools and set their options, but cannot change the stack.

    * the structure is read only (no dragging, adding, removing or renaming)
    * double clicking a tool runs it, and double clicking an organiser
      expands or collapses it
    * the right click menu only offers running the tool itself, never a
      build of the whole stack (or of everything up to a tool), and adding
      it to (or removing it from) the favourites
    * a Run button beneath the options runs the selected tool
    * a filter above the tree shows only the tools whose names match

Each toolkit's config gives the window its own icon and stack background.
How the window is shown (floating, docked, parented) is up to the host: see
EmbeddedHost.launch_toolkit, which uses launch_window by default.
"""
import re

import qtility
import xstack
from Qt import QtWidgets, QtGui

try:
    from shiboken6 import isValid

except ImportError:
    from shiboken2 import isValid

from xstack.app import tree
from xstack.app import delegate
from xstack.constants import Status

from .. import app
from .. import resources
from . import core

# -- The open toolkit windows, by toolkit name
_WINDOWS = dict()

# -- What separates the terms of a filter
_FILTER_SEPARATORS = re.compile(r"[,;]")


# --------------------------------------------------------------------------------------
class ToolkitDelegate(delegate.ComponentItemDelegate):
    """
    Draws a tool's name alone. The stack's default delegate follows it with
    the component type, which for a tool is its name again. Organisers and
    tools are filled with the config's colours, and organiser names are bold.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.organiser_font = QtGui.QFont(self.text_font)
        self.organiser_font.setBold(True)

    def paint_highlight(self, component, painter, option, index):
        if isinstance(component, core.Organiser):
            color = self.app_config.organiser_color
            alpha = self.app_config.organiser_alpha

        else:
            color = self.app_config.tool_color
            alpha = self.app_config.tool_alpha

        # -- Without a colour, keep xstack's own gradient
        if color is None:
            super().paint_highlight(component, painter, option, index)
            return

        if option.state & QtWidgets.QStyle.State_Selected:
            alpha += self.app_config.selected_alpha_increase

        elif option.state & QtWidgets.QStyle.State_MouseOver:
            alpha += self.app_config.hover_alpha_increase

        painter.fillRect(option.rect, QtGui.QColor(*color, min(alpha, 255)))

    def paint_text(self, component, painter, option, index):
        is_organiser = isinstance(component, core.Organiser)
        painter.setFont(self.organiser_font if is_organiser else self.text_font)
        painter.setPen(self.text_pen)
        painter.drawText(
            option.rect.x() + self.item_size + self.bfr + self.STATUS_WIDTH + self.bfr,
            option.rect.y() + (25 * self.factor),
            component.label(),
        )


# --------------------------------------------------------------------------------------
class ToolkitTree(tree.BuildTreeWidget):
    """
    The toolkit's tree, where double clicking runs a tool, and which can be
    filtered to the tools whose names match.
    """

    def __init__(self, stack, app_config, app=None):
        # -- The filter is applied whenever the tree is populated, which the
        # -- base class does on construction
        self.filter_terms = []

        super().__init__(stack, app_config, app=app)

        self._delegate = ToolkitDelegate(stack, app_config)
        self.setItemDelegateForColumn(0, self._delegate)

    # ----------------------------------------------------------------------------------
    def populate(self, *args, **kwargs):
        super().populate(*args, **kwargs)
        self.apply_filter()

    # ----------------------------------------------------------------------------------
    def set_filter(self, text: str) -> None:
        """
        Shows only the tools whose names contain any of the comma (or semi
        colon) separated terms, ignoring case. An empty filter shows them all.
        """
        self.filter_terms = [
            term.strip().lower()
            for term in _FILTER_SEPARATORS.split(text or "")
            if term.strip()
        ]
        self.apply_filter()

    # ----------------------------------------------------------------------------------
    def apply_filter(self) -> None:
        """
        Hides the tools which do not match the filter, and the organisers left
        without a tool to show. While filtering, organisers are expanded so
        the matching tools can be seen.
        """
        for index in range(self.topLevelItemCount()):
            organiser_item = self.topLevelItem(index)
            any_shown = False

            for child_index in range(organiser_item.childCount()):
                tool_item = organiser_item.child(child_index)
                component = getattr(tool_item, "component", None)
                label = component.label().lower() if component else ""

                shown = not self.filter_terms or any(term in label for term in self.filter_terms)
                tool_item.setHidden(not shown)
                any_shown = any_shown or shown

            # -- Without a filter every organiser shows, even an empty
            # -- Favourites, so the user can see where favourites go
            organiser_item.setHidden(bool(self.filter_terms) and not any_shown)

            if self.filter_terms and any_shown:
                organiser_item.setExpanded(True)

    # ----------------------------------------------------------------------------------
    def on_item_double_clicked(self, item, column):
        """
        Runs a tool, or expands/collapses an organiser.
        """
        if not self.allow_interaction:
            return

        component = getattr(item, "component", None)
        if component is None:
            return

        if isinstance(component, core.Organiser):
            item.setExpanded(not item.isExpanded())
            return

        self.app.build(build_only=component)


# --------------------------------------------------------------------------------------
class ToolkitConfig(app.AppConfig):
    """
    The app configuration for a toolkit. Each toolkit subclasses it, giving
    its name (matched against Tool.toolkit), label and settings prefix.
    """

    # -- The name of the toolkit
    toolkit = ""

    # -- The start of the scribble ids the tools' option values and the
    # -- favourites are stored under. Use the toolkit package's name, so
    # -- toolkits in different applications do not share them. If empty,
    # -- aniseed_<toolkit>_toolkit is used.
    settings_prefix = ""

    # -- Folders searched for category icons (<category>.png) and for the
    # -- icons of tools which do not give one (<identifier>.png)
    icon_folders = []

    # -- Whether a filter is shown above the tree
    show_filter = True

    # -- The background (rgb) of organiser and tool items, and how opaque it
    # -- is (0-255). Hovered and selected items are drawn more opaque than
    # -- this. A colour of None keeps xstack's default white gradient.
    organiser_color = [60, 90, 120]
    organiser_alpha = 140

    tool_color = [50, 200, 75]
    tool_alpha = 20

    # -- How much more opaque (0-255) hovered and selected items are
    hover_alpha_increase = 30
    selected_alpha_increase = 60

    label = "Toolkit"
    component_label = "Tool"
    execute_label = "Run"

    show_menu_bar = False
    show_tree_header = False
    forced_orientation = "vertical"

    read_only_structure = True
    component_build_actions = ("only",)
    show_stack_build_actions = False
    tree_widget = ToolkitTree

    status_unknown_color = [200, 100, 255, 0]

    log_logger_names = app.AppConfig.log_logger_names + [
        "aniseed.toolkits",
    ]

    settings_id = "aniseed_toolkit_settings"


# --------------------------------------------------------------------------------------
class ToolkitAppWidget(xstack.app.AppWidget):
    """
    The xstack app, with a filter above the tree and a Run button beneath the
    tool's options which runs the selected tool, reporting how each tool run
    went in the window's status bar.
    """

    def __init__(self, *args, **kwargs):
        self.run_button = None
        self.filter_field = None
        super().__init__(*args, **kwargs)

    # ----------------------------------------------------------------------------------
    def build_layout(self):
        super().build_layout()

        # -- Give the options a fair share of the window
        self.splitter.setSizes([550, 450])

        if self.app_config.show_filter:
            self.filter_field = QtWidgets.QLineEdit()
            self.filter_field.setPlaceholderText("Filter (separate terms with commas)")
            self.filter_field.setClearButtonEnabled(True)
            self.filter_field.textChanged.connect(self.tree_widget.set_filter)
            self.stack_layout().insertWidget(0, self.filter_field)

        self.run_button = QtWidgets.QPushButton(self.app_config.execute_label)
        self.run_button.setMinimumHeight(30)
        self.run_button.clicked.connect(self.run_selected_tool)
        self.stack_layout().addWidget(self.run_button)

        self.tree_widget.currentItemChanged.connect(self.update_run_button)
        self.update_run_button()

    # ----------------------------------------------------------------------------------
    def selected_tool(self):
        """
        Returns the selected tool, or None if an organiser (or nothing) is
        selected.
        """
        component = self.tree_widget.current_component() if self.tree_widget else None

        if component is None or isinstance(component, core.Organiser):
            return None

        return component

    # ----------------------------------------------------------------------------------
    def update_run_button(self, *args, **kwargs):
        if self.run_button is not None:
            tool = self.selected_tool()
            self.run_button.setEnabled(tool is not None)
            self.run_button.setText(f"{self.app_config.execute_label} {tool.label()}" if tool else self.app_config.execute_label)

    # ----------------------------------------------------------------------------------
    def run_selected_tool(self):
        tool = self.selected_tool()
        if tool is not None:
            self.build(build_only=tool)

    # ----------------------------------------------------------------------------------
    def build(self, build_up_to=None, build_only=None, build_below=None, validate_only=False):
        super().build(
            build_up_to=build_up_to,
            build_only=build_only,
            build_below=build_below,
            validate_only=validate_only,
        )

        component = build_only or build_below or build_up_to
        window = self.window()

        if component is None or not isinstance(window, QtWidgets.QMainWindow):
            return

        status = component.status()

        if status == Status.Success:
            message = f"{component.label()} : done"

        elif status == Status.Invalid:
            message = f"{component.label()} : could not run (see the Log tab)"

        else:
            message = f"{component.label()} : failed (see the Log tab)"

        window.statusBar().showMessage(message, 6000)


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ToolkitWindow(QtWidgets.QMainWindow):
    """
    The window holding one toolkit. Hosts may mix other classes in front of
    it (such as Maya's dockable mixin), so it takes its config by keyword
    too.
    """

    def __init__(self, config=None, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)

        self.config = config

        self.setObjectName(object_name(config))
        self.setWindowTitle(config.label)
        self.setWindowIcon(QtGui.QIcon(config.icon))
        self.resize(380, 700)

        qtility.styling.apply(
            [resources.get("style.css")],
            apply_to=self,
            _ITEMHIGHLIGHT_=",".join(str(n) for n in config.item_highlight_color),
        )

        self.stack = core.ToolkitStack(
            config.toolkit,
            settings_prefix=config.settings_prefix,
            icon_folders=config.icon_folders,
        )
        self.stack.populate()

        self.app = ToolkitAppWidget(
            app_config=config,
            allow_threading=False,
            parent=self,
        )
        self.app.set_active_stack(self.stack)
        self.setCentralWidget(self.app)

        _WINDOWS[config.toolkit] = self


# --------------------------------------------------------------------------------------
def object_name(config) -> str:
    """
    Returns the Qt object name of the toolkit's window, such as
    AniseedRiggingToolkit.
    """
    return f"Aniseed{config.toolkit}Toolkit"


def window(toolkit: str):
    """
    Returns the open window of the given toolkit, or None.
    """
    existing = _WINDOWS.get(toolkit)

    if existing is not None and isValid(existing):
        return existing

    _WINDOWS.pop(toolkit, None)
    return None


def launch_window(config) -> ToolkitWindow:
    """
    Shows the toolkit's window as a floating window parented to the
    application, reusing it if it is already open. This is what hosts use
    unless they re-implement EmbeddedHost.launch_toolkit.
    """
    toolkit_window = window(config.toolkit)

    if toolkit_window is None:
        toolkit_window = ToolkitWindow(config, parent=qtility.windows.application())

    toolkit_window.show()
    toolkit_window.raise_()
    return toolkit_window


def close_all() -> None:
    """
    Closes every open toolkit window.
    """
    for toolkit in list(_WINDOWS):
        toolkit_window = window(toolkit)
        if toolkit_window is not None:
            toolkit_window.close()

    _WINDOWS.clear()
