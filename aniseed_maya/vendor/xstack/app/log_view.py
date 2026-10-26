"""
The Log tab of the app. It shows log records and, while a build runs, everything
printed to stdout and stderr, with highlighting that makes the build report
easier to read. Printed output still reaches its normal destination (such as a
DCC's script editor) as well.

What is captured:

    * Log records from the loggers named in AppConfig.log_logger_names (and
      their children), at any time.
    * During a build of the watched stack: every log record, and everything
      printed. Component modules are loaded under generated module names, so
      their loggers can only be told apart by when they log.
"""
import re
import sys
import time
import logging
import functools
import threading

from Qt import QtCore, QtGui, QtWidgets

# -- The kinds of text the log shows. Log records use their logging level.
STDOUT = 0
STDERR = 1


# --------------------------------------------------------------------------------------
class _StreamTee:
    """
    Stands in for sys.stdout or sys.stderr. Everything written is passed on to
    the original stream unchanged, and also to the given callback.
    """

    def __init__(self, stream, callback):
        self.stream = stream
        self.callback = callback

    def write(self, text):
        result = self.stream.write(text)

        if text:
            self.callback(text)

        return result

    def flush(self):
        self.stream.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)


# --------------------------------------------------------------------------------------
class _StreamCapture:
    """
    Swaps sys.stdout and sys.stderr for tees while anything is subscribed, and
    puts the original streams back once nothing is. Several log views can
    capture at once without unwinding each other's streams.
    """

    _lock = threading.Lock()
    _subscribers = []
    _tees = None

    # ----------------------------------------------------------------------------------
    @classmethod
    def subscribe(cls, callback):
        with cls._lock:
            if callback in cls._subscribers:
                return

            cls._subscribers.append(callback)

            if cls._tees is None:
                cls._tees = (
                    _StreamTee(sys.stdout, cls._dispatch_stdout),
                    _StreamTee(sys.stderr, cls._dispatch_stderr),
                )
                sys.stdout, sys.stderr = cls._tees

    # ----------------------------------------------------------------------------------
    @classmethod
    def unsubscribe(cls, callback):
        with cls._lock:
            if callback in cls._subscribers:
                cls._subscribers.remove(callback)

            if cls._subscribers or cls._tees is None:
                return

            stdout_tee, stderr_tee = cls._tees
            cls._tees = None

            # -- Only put a stream back if nothing else has replaced it since.
            # -- Otherwise the tee stays in the chain, passing text straight
            # -- through, rather than cutting out whatever was put on top.
            if sys.stdout is stdout_tee:
                sys.stdout = stdout_tee.stream

            if sys.stderr is stderr_tee:
                sys.stderr = stderr_tee.stream

    # ----------------------------------------------------------------------------------
    @classmethod
    def _dispatch_stdout(cls, text):
        for callback in list(cls._subscribers):
            callback(text, STDOUT)

    # ----------------------------------------------------------------------------------
    @classmethod
    def _dispatch_stderr(cls, text):
        for callback in list(cls._subscribers):
            callback(text, STDERR)


# --------------------------------------------------------------------------------------
class _Bridge(QtCore.QObject):
    """
    Carries text and build events to the log view. Builds can run on a worker
    thread, and Qt queues signals emitted from another thread, so the view is
    only ever updated on the thread it lives on.
    """
    text_received = QtCore.Signal(str, int)
    build_started = QtCore.Signal()
    build_finished = QtCore.Signal(bool)
    component_reporting = QtCore.Signal(str, str)


# --------------------------------------------------------------------------------------
class _LogHandler(logging.Handler):
    """
    Passes log records to the log view. It sits on the root logger and lets a
    record through if it comes from one of the given loggers, or if a build is
    running.
    """

    def __init__(self, bridge: _Bridge, logger_names):
        super().__init__()
        self.bridge = bridge
        self.logger_names = list(logger_names)
        self.capturing = False
        self.setFormatter(logging.Formatter("%(levelname)s : %(name)s : %(message)s"))

    def emit(self, record):
        if not self.capturing and not self._is_watched(record.name):
            return

        try:
            self.bridge.text_received.emit(self.format(record) + "\n", record.levelno)

        except RuntimeError:
            # -- The view has been deleted without detaching
            logging.getLogger().removeHandler(self)

    def _is_watched(self, logger_name: str) -> bool:
        return any(
            logger_name == name or logger_name.startswith(name + ".")
            for name in self.logger_names
        )


# --------------------------------------------------------------------------------------
class _Colours:
    """
    The colours the log uses, chosen to read on both light and dark palettes.
    """
    warning = QtGui.QColor(230, 165, 40)
    error = QtGui.QColor(235, 85, 85)
    success = QtGui.QColor(95, 195, 95)
    accent = QtGui.QColor(90, 160, 235)


# --------------------------------------------------------------------------------------
class _ReportHighlighter(QtGui.QSyntaxHighlighter):
    """
    Highlights the build report that xstack prints: the header line of each
    component, its build status, and the names in its option, input and output
    listings. Lines that are already coloured (warnings, errors and stderr) are
    left as they are.
    """

    _ABOUT_TO_BUILD = re.compile(r"^(About to Build) : (.*)$")
    _ABOUT_TO_VALIDATE = re.compile(r"^About to Validate : ")
    _COMPONENT_TYPE = re.compile(r"^(Component Type) : (.*)$")
    _STATUS = re.compile(r"^Component Build Status : (\w+)")
    _SUCCEEDED = re.compile(r"^Build Succeeded")
    _SECTION = re.compile(r"^\s+(Identifier|Options|Inputs|Outputs)\s*:")
    _KEY_VALUE = re.compile(r"^(\s{8,})(\S.*?)(\s+: )")
    _MARKER = re.compile(r"^-{4} .* -{4}$")

    # ----------------------------------------------------------------------------------
    def __init__(self, document, dim_colour: QtGui.QColor):
        super().__init__(document)
        self.dim_colour = dim_colour

    # ----------------------------------------------------------------------------------
    def highlightBlock(self, text):  # noqa: N802 (Qt override)

        # -- Text inserted with a colour of its own is not report text. An empty
        # -- block has no fragments, and asking an end iterator for its fragment
        # -- is undefined (it can hang), so check for that first.
        fragments = self.currentBlock().begin()
        if fragments.atEnd():
            return

        if fragments.fragment().charFormat().foreground().style() != QtCore.Qt.NoBrush:
            return

        match = self._ABOUT_TO_BUILD.match(text)
        if match:
            self.setFormat(0, len(text), self._format(bold=True))
            self.setFormat(match.start(2), len(match.group(2)), self._format(colour=_Colours.accent, bold=True))
            return

        # -- Validation lists every component up front, so it is kept quiet to
        # -- let the build headers stand out
        if self._ABOUT_TO_VALIDATE.match(text):
            self.setFormat(0, len(text), self._format(colour=self.dim_colour))
            return

        match = self._COMPONENT_TYPE.match(text)
        if match:
            self.setFormat(0, len(match.group(1)) + 2, self._format(colour=self.dim_colour))
            return

        match = self._STATUS.match(text)
        if match:
            colours = {
                "success": _Colours.success,
                "failed": _Colours.error,
                "invalid": _Colours.warning,
            }
            colour = colours.get(match.group(1).lower())
            if colour:
                self.setFormat(0, len(text), self._format(colour=colour, bold=True))
            return

        if self._SUCCEEDED.match(text):
            self.setFormat(0, len(text), self._format(colour=_Colours.success, bold=True))
            return

        if self._MARKER.match(text):
            self.setFormat(0, len(text), self._format(colour=self.dim_colour, italic=True))
            return

        match = self._SECTION.match(text)
        if match:
            self.setFormat(0, match.end(), self._format(colour=self.dim_colour, italic=True))
            return

        match = self._KEY_VALUE.match(text)
        if match:
            self.setFormat(match.start(2), match.end(3) - match.start(2), self._format(colour=self.dim_colour))

    # ----------------------------------------------------------------------------------
    @staticmethod
    def _format(colour: QtGui.QColor = None, bold: bool = False, italic: bool = False):
        text_format = QtGui.QTextCharFormat()

        if colour is not None:
            text_format.setForeground(colour)

        if bold:
            text_format.setFontWeight(QtGui.QFont.Bold)

        text_format.setFontItalic(italic)
        return text_format


# --------------------------------------------------------------------------------------
class LogView(QtWidgets.QWidget):
    """
    The content of the app's Log tab. Call watch_stack with the stack the app
    is showing so the view can capture that stack's builds, and detach before
    the view is thrown away.

    The log is cleared when each build starts, so it always holds the whole of
    the latest build however long it is. It records where each component's part
    of the report starts, so show_component can scroll to it.

    Signals:
        counts_changed(warnings, errors): Emitted when the number of warnings
            or errors shown changes. Both are reset when a build starts.
        build_failed(): Emitted, on the view's thread, when a watched build
            fails.
    """

    counts_changed = QtCore.Signal(int, int)
    build_failed = QtCore.Signal()

    # ----------------------------------------------------------------------------------
    # -- How long show_component highlights a component's section for
    HIGHLIGHT_DURATION_MS = 2500

    # ----------------------------------------------------------------------------------
    def __init__(self, logger_names, parent=None):
        super().__init__(parent=parent)

        self.stack = None
        self.warnings = 0
        self.errors = 0
        self._build_start_time = None

        # -- The line each component's part of the report starts on, by uuid,
        # -- for the validation and build stages of the latest build
        self._sections = {
            "validate": {},
            "build": {},
        }

        self._bridge = _Bridge(self)
        self._bridge.text_received.connect(self.append)
        self._bridge.build_started.connect(self._on_build_started)
        self._bridge.build_finished.connect(self._on_build_finished)
        self._bridge.component_reporting.connect(self._on_component_reporting)

        self._handler = _LogHandler(self._bridge, logger_names)
        logging.getLogger().addHandler(self._handler)

        # -- Stop capturing if the view is deleted without being detached, such
        # -- as when the window it sits in is closed. detach only touches python
        # -- state, so it is safe to call once the widget itself has gone.
        self.destroyed.connect(functools.partial(LogView.detach, self))

        # -- The text area
        self.text_edit = QtWidgets.QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

        # -- A fixed width font keeps the report's columns aligned. It is set
        # -- through a style sheet as well as setFont, because a host's
        # -- application style sheet (Maya has one) overrides setFont.
        self.text_edit.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.text_edit.setStyleSheet(
            'QPlainTextEdit { font-family: Consolas, "Courier New", monospace; }'
        )

        # -- Owned by the view, so it cannot fire once the view has gone
        self._highlight_timer = QtCore.QTimer(self)
        self._highlight_timer.setSingleShot(True)
        self._highlight_timer.timeout.connect(self._clear_highlight)

        palette = self.text_edit.palette()
        dim_colour = QtGui.QColor(palette.color(QtGui.QPalette.Text))
        dim_colour.setAlphaF(0.55)
        self._highlighter = _ReportHighlighter(self.text_edit.document(), dim_colour)

        # -- The buttons
        self.auto_scroll = QtWidgets.QCheckBox("Auto Scroll", self)
        self.auto_scroll.setChecked(True)

        copy_button = QtWidgets.QPushButton("Copy", self)
        copy_button.clicked.connect(self.copy)

        clear_button = QtWidgets.QPushButton("Clear", self)
        clear_button.clicked.connect(self.clear)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.auto_scroll)
        button_layout.addStretch(1)
        button_layout.addWidget(copy_button)
        button_layout.addWidget(clear_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.text_edit)
        layout.addLayout(button_layout)

    # ----------------------------------------------------------------------------------
    def watch_stack(self, stack):
        """
        Captures the builds of the given stack from now on, and stops capturing
        the builds of the stack watched before. Pass None to watch nothing.

        This always reconnects, even to the stack already watched: an app can
        clear a stack's listeners without the view knowing (aniseed does each
        time it shows a rig, including the rig already shown).
        """
        if self.stack is not None:
            # -- disconnect returns False rather than raising if the callback
            # -- was already cleared
            self.stack.build_started.disconnect(self._on_stack_build_started)
            self.stack.build_finished.disconnect(self._on_stack_build_finished)
            self.stack.component_reporting.disconnect(self._on_stack_component_reporting)

        self.stack = stack

        if stack is not None:
            stack.build_started.connect(self._on_stack_build_started)
            stack.build_finished.connect(self._on_stack_build_finished)
            stack.component_reporting.connect(self._on_stack_component_reporting)

    # ----------------------------------------------------------------------------------
    def detach(self):
        """
        Stops all capturing. Call this before the view is thrown away.
        """
        self.watch_stack(None)
        self._stop_capturing()
        logging.getLogger().removeHandler(self._handler)

    # ----------------------------------------------------------------------------------
    def append(self, text: str, kind: int = STDOUT):
        """
        Adds the given text to the end of the log. Warnings, errors and stderr
        are coloured; anything else is left to the report highlighter.

        Args:
            text: The text to add
            kind: STDOUT, STDERR or a logging level
        """
        colour = None

        if kind == STDERR or kind >= logging.ERROR:
            colour = _Colours.error

        elif kind >= logging.WARNING:
            colour = _Colours.warning

        self._count(text, kind)
        self._insert(text, colour)

    # ----------------------------------------------------------------------------------
    def _insert(self, text: str, colour: QtGui.QColor = None):
        text_format = QtGui.QTextCharFormat()

        if colour is not None:
            text_format.setForeground(colour)

        cursor = QtGui.QTextCursor(self.text_edit.document())
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text, text_format)

        if self.auto_scroll.isChecked():
            scroll_bar = self.text_edit.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

    # ----------------------------------------------------------------------------------
    def clear(self):
        self.text_edit.clear()
        self._set_counts(0, 0)

        for sections in self._sections.values():
            sections.clear()

    # ----------------------------------------------------------------------------------
    def has_component(self, component) -> bool:
        """
        Returns True if the log holds part of the report for the given component
        """
        return any(
            component.uuid() in sections
            for sections in self._sections.values()
        )

    # ----------------------------------------------------------------------------------
    def show_component(self, component) -> bool:
        """
        Scrolls the log so the given component's part of the report is at the
        top, and highlights it for a moment. Its build section is preferred,
        falling back to its validation line where it never got to build (it
        was invalid, or the build stopped before it).

        Returns False if the log holds nothing for the component.
        """
        uuid = component.uuid()
        start = self._sections["build"].get(uuid)
        building = start is not None

        if not building:
            start = self._sections["validate"].get(uuid)

        if start is None:
            return False

        document = self.text_edit.document()
        first_block = document.findBlockByNumber(start)

        if not first_block.isValid():
            return False

        # -- A build section runs up to its status line; a validation entry is
        # -- just the one line
        last_block = first_block
        if building:
            block = first_block
            while block.isValid():
                last_block = block
                if block.text().startswith("Component Build Status"):
                    break
                block = block.next()

        self.text_edit.verticalScrollBar().setValue(first_block.blockNumber())

        selection = QtWidgets.QTextEdit.ExtraSelection()
        highlight = QtGui.QColor(_Colours.accent)
        highlight.setAlpha(60)
        selection.format.setBackground(highlight)
        selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        selection.cursor = QtGui.QTextCursor(first_block)
        selection.cursor.setPosition(
            last_block.position() + last_block.length() - 1,
            QtGui.QTextCursor.KeepAnchor,
        )
        self.text_edit.setExtraSelections([selection])
        self._highlight_timer.start(self.HIGHLIGHT_DURATION_MS)
        return True

    # ----------------------------------------------------------------------------------
    def _clear_highlight(self):
        self.text_edit.setExtraSelections([])

    # ----------------------------------------------------------------------------------
    def copy(self):
        QtWidgets.QApplication.clipboard().setText(self.text_edit.toPlainText())

    # ----------------------------------------------------------------------------------
    def _count(self, text: str, kind: int):
        warnings = self.warnings
        errors = self.errors

        if kind == STDERR:
            # -- A traceback arrives as many writes, so count the header only
            if "Traceback (most recent call last)" in text:
                errors += 1

        elif kind >= logging.ERROR:
            errors += 1

        elif kind >= logging.WARNING:
            warnings += 1

        self._set_counts(warnings, errors)

    # ----------------------------------------------------------------------------------
    def _set_counts(self, warnings: int, errors: int):
        if (warnings, errors) == (self.warnings, self.errors):
            return

        self.warnings = warnings
        self.errors = errors
        self.counts_changed.emit(warnings, errors)

    # ----------------------------------------------------------------------------------
    def _stdout_received(self, text: str, kind: int):
        try:
            self._bridge.text_received.emit(text, kind)

        except RuntimeError:
            # -- The view has been deleted without detaching
            _StreamCapture.unsubscribe(self._stdout_received)

    # ----------------------------------------------------------------------------------
    def _start_capturing(self):
        self._handler.capturing = True
        _StreamCapture.subscribe(self._stdout_received)

    # ----------------------------------------------------------------------------------
    def _stop_capturing(self):
        self._handler.capturing = False
        _StreamCapture.unsubscribe(self._stdout_received)

    # ----------------------------------------------------------------------------------
    def _on_stack_build_started(self):
        # -- This runs on the thread doing the build, so it only swaps the
        # -- streams (which is thread agnostic) and hands the rest to the bridge
        try:
            self._bridge.build_started.emit()

        except RuntimeError:
            # -- The view has been deleted without detaching
            self.watch_stack(None)
            return

        self._start_capturing()

    # ----------------------------------------------------------------------------------
    def _on_stack_build_finished(self, successful=True):
        self._stop_capturing()

        try:
            self._bridge.build_finished.emit(bool(successful))

        except RuntimeError:
            # -- The view has been deleted without detaching
            self.watch_stack(None)

    # ----------------------------------------------------------------------------------
    def _on_stack_component_reporting(self, component, stage: str):
        # -- Like the other stack callbacks, this runs on the thread doing the
        # -- build. Going through the bridge keeps it in order with the report
        # -- text, so the line recorded is the one the report starts on.
        try:
            self._bridge.component_reporting.emit(component.uuid(), stage)

        except RuntimeError:
            # -- The view has been deleted without detaching
            self.watch_stack(None)

    # ----------------------------------------------------------------------------------
    def _on_component_reporting(self, uuid: str, stage: str):
        if stage not in self._sections:
            return

        # -- The report text has not arrived yet, so it will start on the
        # -- (empty) last line of the document
        self._sections[stage][uuid] = self.text_edit.document().blockCount() - 1

    # ----------------------------------------------------------------------------------
    def _on_build_started(self):
        self._build_start_time = time.time()

        # -- Each build starts with an empty log, so the whole of the latest
        # -- build is always there however long it is
        self.clear()
        self._insert(f"---- Build started {time.strftime('%H:%M:%S')} ----\n")

    # ----------------------------------------------------------------------------------
    def _on_build_finished(self, successful: bool):
        duration = ""
        if self._build_start_time is not None:
            duration = f" ({time.time() - self._build_start_time:.3f}s)"

        if successful:
            self._insert(f"---- Build finished{duration} ----\n")
            return

        self._insert(f"---- Build failed{duration} ----\n", _Colours.error)
        self.build_failed.emit()
