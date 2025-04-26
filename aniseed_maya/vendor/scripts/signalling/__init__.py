"""
# Overview

This library exposes a mechanism for signalling in Python. Through this
mechanism you can create a Signal class and then connect that signal to
any number of callable end points. Upon that signal being emitted the
Signal class will then trigger a call to all the connected callables.

This pattern allows for events to be propagated to different classes/functions
when they occur.

## Install

```python
pip install signalling
```

## Example

This example shows how to use a basic signal:
```python
import signalling

# -- Declare some functions. This can be functions, methods
# -- or classsmethods
def do_something():
    print("doing something")

def do_something_else():
    print("doing something else")

# -- Create a singal
signal = signalling.Signal()

# -- Connect the signal to various end points
signal.connect(do_something)
signal.connect(do_something_else)

# -- Now we can emit the signal and all the end
# -- points will be called (in order they were
# -- connected)
signal.emit()
```

## WeakSignal

The standard `Signal` class will hold a direct reference to the callable its connected
to. This means the endpoint will never be garbage collected whilst the signal is alive.

However, there are times that we want to use the signalling mechanism but we dont want
to hold a direct reference. For this we can use `signalling.WeakSignal`. This version
of the signalling class will only hold a weak reference to the callable end point, so
it allows for the garbage collecting of end points if nothing else is holding a
reference to it outside of the Signal class.

The approach to using the `WeakSignal` is exactly the same, and all the weakref
management is carried out by the signal class itself.

```python
import signalling

# -- Declare some functions. This can be functions, methods
# -- or classsmethods
def do_something():
    print("doing something")

def do_something_else():
    print("doing something else")

# -- Create a singal
signal = signalling.WeakSignal()

# -- Connect the signal to various end points
signal.connect(do_something)
signal.connect(do_something_else)

# -- Now we can emit the signal and all the end
# -- points will be called (in order they were
# -- connected)
signal.emit()
```
"""
from .standard import Signal
from .weak import WeakSignal

__version__ = "1.0.1"
