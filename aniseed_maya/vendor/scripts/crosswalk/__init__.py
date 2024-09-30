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
from . import core
from .apps import standalone


app = standalone
module_name = core.get_usable_app()

if module_name:
    app = sys.modules[module_name]

__version__ = "0.1.0"