"""
This aniseed toolkit is a tool which exposes various
useful rigging tools and features.
"""
from .core import Tool
from .core import ToolBox
from .core import run

from . import resources
from .app.widgets import launch

__version__ = "1.0.1"

# -- Most code will want to access the toolbox
# -- tools directly.
tools = ToolBox()
