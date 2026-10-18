# Components

Files in this folder are plugin loaded: aniseed discovers and imports them
at runtime, through the component factory, rather than importing them when
aniseed itself is imported.

The components in this folder are part of the aniseed core, so they must be
application agnostic. Application specific components (such as the Maya
components in `aniseed_maya_standard`) belong in an aniseed package, which
is any folder containing an `aniseed_package.json` file. See
`aniseed/packages.py`.

Nothing in the aniseed core may import an application specific library. Use
`crosswalk` for the little scene interaction the framework needs.
