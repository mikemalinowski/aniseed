"""
The Aniseed Animation Toolkit: a window of tools for animating aniseed rigs
in Maya. Its tools are the aniseed.toolkits tools whose toolkit is
"Animation", from this package's tools folder or any other active package's.

    from aniseed import toolkits
    toolkits.launch("Animation")
"""
TOOLKIT = "Animation"


def launch():
    """
    Opens (or raises) the Animation Toolkit, docked beside the Attribute Editor.
    """
    import aniseed
    from . import config

    return aniseed.host.get().launch_toolkit(config.AnimationToolkitConfig)
