"""
This aniseed toolkit is a tool which exposes various
useful rigging tools and features.
"""
from .registry import Tool
from .registry import ToolBox
from .registry import run
from .registry import register
from .registry import tool
from .resources import register_resource_path
from .lib import *
from .lib import rigging

from . import resources
from .app.widgets import launch

__version__ = "3.0.1"

# -- Most code will want to access the toolbox tools directly. This is the
# -- shared instance, so the tools are only discovered once.
tools = ToolBox.singleton()
