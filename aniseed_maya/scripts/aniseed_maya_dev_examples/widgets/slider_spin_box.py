"""
Provides SliderSpinBox, a slider and spin box pair for editing a float option
within a range. It is used by components/05_extending/ex12_custom_widget.py.

What this example teaches:
    * The contract aniseed expects from an option widget
      (changed, get_value, set_value)
    * Keeping two child widgets in step without feedback loops
"""
from Qt import QtWidgets, QtCore


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class SliderSpinBox(QtWidgets.QWidget):
    """
    A horizontal slider and a spin box which edit the same float value. The
    slider is quick to drag, while the spin box allows an exact value.
    """

    # -- Key idea: the app connects to this signal and, whenever it fires,
    # -- reads get_value and stores the result on the option. Without it the
    # -- option would never learn that the user changed anything.
    changed = QtCore.Signal()

    # -- QSlider only works in integers, so the range is split into this
    # -- many steps and converted to and from the float value
    SLIDER_STEPS = 1000

    # ----------------------------------------------------------------------------------
    def __init__(self, minimum=0.0, maximum=1.0, decimals=2, parent=None):
        """
        Args:
            minimum: The lowest value the widget allows.
            maximum: The highest value the widget allows.
            decimals: The number of decimal places the spin box shows.
            parent: The Qt parent of the widget.
        """
        super().__init__(parent=parent)

        self._minimum = float(minimum)
        self._maximum = float(maximum)

        # -- Set whenever we are updating one child widget from the other, so
        # -- that the update does not bounce back and forth between them
        self._syncing = False

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, self.SLIDER_STEPS)
        self.layout().addWidget(self.slider)

        self.spin_box = QtWidgets.QDoubleSpinBox()
        self.spin_box.setRange(self._minimum, self._maximum)
        self.spin_box.setDecimals(decimals)
        self.spin_box.setSingleStep((self._maximum - self._minimum) / 100.0)
        self.layout().addWidget(self.spin_box)

        self.slider.valueChanged.connect(self._slider_changed)
        self.spin_box.valueChanged.connect(self._spin_box_changed)

    # ----------------------------------------------------------------------------------
    def get_value(self) -> float:
        """
        Returns the current value. The app calls this whenever changed is
        emitted, and stores the result on the option.
        """
        return self.spin_box.value()

    # ----------------------------------------------------------------------------------
    def set_value(self, value) -> None:
        """
        Shows the given value. The app calls this once, with the option's
        stored value, when the widget is first shown.

        Args:
            value: The value to show. It is clamped to the widget's range.
        """
        # -- Setting the spin box updates the slider (and emits changed)
        # -- through _spin_box_changed
        self.spin_box.setValue(float(value))

    # ----------------------------------------------------------------------------------
    def _slider_changed(self, slider_value: int) -> None:
        """
        Updates the spin box when the slider is dragged.
        """
        if self._syncing:
            return

        span = self._maximum - self._minimum
        value = self._minimum + (span * slider_value / self.SLIDER_STEPS)

        self._syncing = True
        self.spin_box.setValue(value)
        self._syncing = False

        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def _spin_box_changed(self, value: float) -> None:
        """
        Updates the slider when the spin box is edited.
        """
        if self._syncing:
            return

        span = (self._maximum - self._minimum) or 1.0

        self._syncing = True
        self.slider.setValue(round((value - self._minimum) / span * self.SLIDER_STEPS))
        self._syncing = False

        self.changed.emit()
