"""
The Aniseed Rigging Toolkit: a window of tools for building rigs in Maya. Its
tools are the aniseed.toolkits tools whose toolkit is "Rigging", from this
package's tools folder or any other active package's.

    from aniseed import toolkits
    toolkits.launch("Rigging")
"""
TOOLKIT = "Rigging"


def launch():
    """
    Opens (or raises) the Rigging Toolkit, docked beside the Attribute Editor.
    """
    import aniseed
    from . import config

    return aniseed.host.get().launch_toolkit(config.RiggingToolkitConfig)
