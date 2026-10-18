# Hosts

Files in this folder are plugin loaded: aniseed discovers and imports them
at runtime, through the host factory, rather than importing them when
aniseed itself is imported. Only the host whose application is available
is used.

This folder only holds the standalone host, which is the fallback used when
no application host loads. Application hosts (such as the Maya host) live in
the `hosts` folder of an aniseed package, where they can import application
specific libraries. A host is where application specific behaviour is
plugged into the framework, for example the control shapes offered by the
shape selector, or the tools in the app's Tools menu (see
`aniseed.host.EmbeddedHost`).

A host's `name` is matched against the `hosts` listed in each package's
`aniseed_package.json`, which decides which packages are used in that host.

Nothing in the aniseed core may import an application specific library. Use
`crosswalk` for the little scene interaction the framework needs.
