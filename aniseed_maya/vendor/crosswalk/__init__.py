"""
Crosswalk is intended as a lightweight redirection wrapper around 3d application
api's.

It is not intended to replace an api for any given application, but it exposes just
enough functionality to make it feasible to write tools and frameworks in a way
which allows them to be easily imported and utilised in different applications.

As well as having application specific implementations it also implements a standalone
package, which allows for libraries and tools to be tested outside of the application
in order to speed up development iteration.

When implementing a new application, you should add a folder into the apps directory
and you MUST implement all the exposed functionality that is defined in the
"standalone" implemented. This is considered to be the authority.
"""
import sys
from . import _core
from .apps import standalone

# -- This group of imports will be replaced by the globals
# -- update. However, placing them here allows for IDE auto
# -- complete
from . import attributes
from . import items
from . import scene
from . import selection

# -- Always fall back to our standalone implementation
# -- if there is no option of an app implementation.
app = standalone
module_name = _core.get_usable_app()

# -- Providing we have an application, replace the app
# -- variable with it
if module_name:
    app = sys.modules[module_name]

__version__ = "2.0.1"

# -- Raise the app implementation up - this will
# -- replace the relative imports above.
globals().update(app.__dict__)
