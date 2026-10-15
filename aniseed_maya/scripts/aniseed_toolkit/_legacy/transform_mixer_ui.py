"""
Deprecated, empty widget stub which used to live in
aniseed_toolkit.transformation. It was never implemented and was the only
reason the transformation module imported PySide6.
"""
from Qt import QtWidgets


class TransformMixerUi(QtWidgets.QWidget):
    """
    Unimplemented placeholder widget for a TransformMixer
    """

    def __init__(self, mixer, parent=None):
        super().__init__(parent=parent)

        # -- Store a reference to the mixer class
        self.mixer = mixer
