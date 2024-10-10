"""
The xstack_app is a Qt based ui application which allows a user to create
new stack instances and populate them with components as well as executing
the stack.

xstack is considered a library rather than a tool, so the likelyhood is that
you will want to import this module into your own and then tailor the ui to
look at your own locations for components.

This can be done using the AppConfig class. You can subclass this and use it
to tell the AppWindow/AppWidget where it should look for components. The config
class also allows you to alter the terminology used in the application to be
more meaningful to your use cases.

To test this module you can simply run:

```
    import xstack_app
    xstack_app.launch()
```

Alternatively, if you want to test the app with some example components which are
used by the unit tests of xstack, you can run this:

```
    import xstack_app
    xstack_app.launch_demo()
```
"""
from .application import launch
from .application import AppWindow
from .application import AppWidget

from .config import AppConfig
from . import application
from . import resources

# -- Expose the demo app
from .demo import launch_demo

__version__ = "0.1.12"