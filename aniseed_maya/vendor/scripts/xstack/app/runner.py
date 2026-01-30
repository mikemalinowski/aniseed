from Qt import QtCore, QtWidgets


class ThreadedRun(QtCore.QThread):
    """
    This is a Qt thread which can run the given stack to allow the ui to not
    be blocked.
    """

    # -- This will emit a Qt threading safe signal as the stack
    # -- progresses through its build
    build_progressed = QtCore.Signal(float)

    def __init__(self, stack, build_below=None, validate_only=False, *args, **kwargs):
        super(ThreadedRun, self).__init__(*args, **kwargs)
        self.stack = stack
        self.build_below = build_below
        self.validate_only = validate_only

        self.finished.connect(self.disconnect_signals)

    def run(self):
        self.stack.build_progressed.connect(self.build_progressed.emit)

        result = self.stack.build(
            build_below=self.build_below,
            validate_only=self.validate_only,
        )
        return result

    def disconnect_signals(self):
        self.stack.build_progressed.disconnect(self.build_progressed.emit)
