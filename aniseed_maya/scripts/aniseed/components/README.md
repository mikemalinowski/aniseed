# Components

Files in this folder are plugin loaded: aniseed discovers and imports them
at runtime, through the component factory, rather than importing them when
aniseed itself is imported.

Because of that, components can import application specific libraries,
such as `maya`, `mref` or `aniseed_toolkit`.

The rest of aniseed must stay application agnostic. Outside of the
`components`, `hosts` and `mixins` folders, nothing in aniseed may import an
application specific library. Use `crosswalk` for the little scene
interaction the framework needs.
