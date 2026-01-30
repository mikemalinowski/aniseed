"""
# qtility

## Overview
PySide (a python wrapper around the Qt framework) is a brilliant libary which
allows for the development of rich user interfaces.

However, there are a lot of common pieces of functionality that is needed
reqularly which takes a fair amount of code to achieve. `qtility` exposes
a series of functions which minimises code replication between qt projects.

Examples of these are being able to blinding resolve widgets from values and values
from widgets (a mechanism which is great for building dynamic ui's to represent
data). Other examples are fast paths to user interaction, emptying layouts and
loading in ui files.

## Installation

You can either clone or download this github repo, or alternatively you can install this via pip:

pip install qtility
## Getting Started Quick

Here is an example of a small application which makes use of the qtility
library to remove some complexity from our code.

```python
import qtility
from PySide6 import QtWidgets


# -- Memorable Window is a QMainWindow which stores its geometry data
# -- whenever its moved or resized and will re-open at the same location
# -- on screen
class Window(qtility.windows.MemorableWindow):

    def __init__(self, parent=None, ):
        super(Window, self).__init__(parent=parent, storage_identifier="foobar")
        self._widget = Widget(self)
        self.setCentralWidget(self._widget)


class Widget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(Widget, self).__init__(parent)

        # -- When adding a layout, quite often we want it with no
        # -- margins. The slimify function does that for us
        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )

        self.some_arbitrary_values = {
            "An Int Value": int(1),
            "A Float Value": 12.0,
            "A String Value": "Hello",
            "A list of strings": ["A", "B", "C"],
            "A Checkbox": True,
        }
        self.dynamic_widgets = []

        for label, value in self.some_arbitrary_values.items():

            # -- Dynamically resolve the right widget based on the value
            widget = qtility.derive.qwidget(value)

            # -- Add a callback to trigger whenever that widget changes
            # -- without knowing what the widget is
            qtility.derive.connect(widget, self._react_to_change)

            self.layout().addWidget(widget)

        # -- Here we show how we can load a ui file as a child widget without
        # -- any overhead
        self.ui = qtility.designer.load(r"c:/path/to/ui_file.ui")
        self.layout().addWidget(self.ui)

    def _react_to_change(self, *args, **kwargs):
        print("Reacting to a widget change!")


if __name__ == "__main__":
    # -- Get the QApplication instance. This will create one for us
    # -- if there is not one available, but will return the running
    # -- instance if there is one. This is useful when working within
    # -- embedded environments.
    app = qtility.app.get()

    # -- Instance the window, but set the parent to the main window
    # -- of the running application. This is particularly useful if
    # -- running within embedded environments
    window = Window(parent=qtility.windows.application())
    window.show()

    app.exec_()

```
In this example we're using `qtility` which is a dynamic property which will
automatically resolve based on whether `PySide6` or `PySide2` is available.

This ensures that `qtility` supports being used in qapplications which are designed
to be used between different environments. However, if you explicitely want to use
qtility for `PySide2` or specifically for `PySide6` then you can use the following
code:

```python
import qtility.six as qtility6

app = qtility6.app.get()
```
```python
import qtility.two as qtuils2

app = qtuils2.app.get()
```

But generally it is better to allow qtility to resolve this for you using the example
below as your code is then more likely to work between Qt versions.

```python
import qtility

qtility.app.get()
```
"""
import traceback
__version__ = "1.0.8"

# -- "x" is the variable we use for "cross environment" and is
# -- the accessor for either two or six without the user caring
_resolved = False
tracebacks = []

# -- We priortise PySide6 over PySide2
if not _resolved:
    try:
        import PySide6
        from .six import *

        _resolved = True
    except:
        tracebacks.append(traceback.format_exc())

# -- If PySide6 is not available then we fall back to
# -- PySide2
if not _resolved:
    try:
        import PySide2
        from .two import *
        _resolved = True
    except:
        tracebacks.append(traceback.format_exc())

# -- If we could not find any supported qt version we
# -- raise an exception
if not _resolved:
    for logged_traceback in tracebacks:
        print(logged_traceback)
    raise Exception("Cannot import qutils into an environment where no supported PySide version is available")
