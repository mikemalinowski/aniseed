"""
The app configuration of the Animation Toolkit window. Kept apart from the
package's __init__, as it needs Qt.
"""
import os

from aniseed.toolkits import app

from . import TOOLKIT

RESOURCES = os.path.join(os.path.dirname(__file__), "_res")


class AnimationToolkitConfig(app.ToolkitConfig):
    toolkit = TOOLKIT
    label = "Aniseed Animation Toolkit"
    settings_prefix = "aniseed_maya_animation_toolkit"

    icon = os.path.join(RESOURCES, "icon.png")
    splash_image = icon
    stack_background = os.path.join(RESOURCES, "stack_background.png")
    icon_folders = [os.path.join(RESOURCES, "icons")]

    log_logger_names = app.ToolkitConfig.log_logger_names + [__package__]
