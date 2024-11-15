"""
Aniseed is an application embedded (Maya) rigging tool. This is built upon AniseedX/StackX

To launch the tool in maya, open the script editor and add a python tab, then run
this code:

    import aniseed;aniseed.app.launch()

If you want to add your own rigging components you can either:

    Place your components within the aniseed/components folder (or subfolder). This
    is useful for small development studios or individuals.

    Place your components in a folder and declare that folder path in an environment
    variable called ANISEED_RIG_COMPONENT_PATHS. This option is particularly useful
    for larger development studio's whom have a requirement to keep open source code
    seperate from their internally developed code.

Note: All functionality available through the UI is also available in a headless/code-only
form as well.
"""
# -- Expose our app and utils
from . import app
from . import utils
from . import widgets
from . import initialize

# -- Expose some of the classes from aniseed_everywhere so that users
# -- developing in maya only have to import aniseed
from .rig import MayaRig
# noinspection PyUnresolvedReferences
from aniseed_everywhere import RigComponent
# noinspection PyUnresolvedReferences
from aniseed_everywhere import RigConfiguration

# -- The control creation is used a lot, so we raise that to the
# -- main ani level
from .utils import control
from .utils import joint

from . import environment

# -- Now we initialize the environment, which sets some environment
# -- variables for other dependent packages
if not environment.initialize_environment():
    print("Failed to initialize environment")

__version__ = "0.2.1"