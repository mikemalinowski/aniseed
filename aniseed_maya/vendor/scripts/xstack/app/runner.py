from Qt import QtCore, QtWidgets


class ThreadedRun(QtCore.QThread):
    """
    This is a Qt thread which can run the given stack to allow the ui to not
    be blocked.
    """

    # -- This will emit a Qt threading safe signal as the stack
    # -- progresses through its build
    build_progressed = QtCore.Signal(float)

    def __init__(self, stack, build_up_to=None, build_below=None, build_only=None, validate_only=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stack = stack
        self.build_up_to = build_up_to
        self.build_below = build_below
        self.build_only = build_only
        self.validate_only = validate_only

        self.finished.connect(self.disconnect_signals)

    def run(self):
        self.stack.build_progressed.connect(self.build_progressed.emit)

        self.stack.build(
            build_up_to=self.build_up_to,
            build_below=self.build_below,
            build_only=self.build_only,
            validate_only=self.validate_only,
        )

    def disconnect_signals(self):
        self.stack.build_progressed.disconnect(self.build_progressed.emit)
