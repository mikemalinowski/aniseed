# Hosts

Files in this folder are plugin loaded: aniseed discovers and imports them
at runtime, through the host factory, rather than importing them when
aniseed itself is imported. Only the host whose application is available
is used.

Because of that, hosts can import application specific libraries, such as
`maya`, `mref` or `aniseed_toolkit`. A host is where application specific
behaviour is plugged into the framework, for example the control shapes
offered by the shape selector, or the tools in the app's Tools menu (see
`aniseed.host.EmbeddedHost`).

The rest of aniseed must stay application agnostic. Outside of the
`components`, `hosts` and `mixins` folders, nothing in aniseed may import an
application specific library. Use `crosswalk` for the little scene
interaction the framework needs.
