# Mixins

Files in this folder are loaded on demand: `aniseed.mixins` is only imported
when it is first used, typically when a component that composes a mixin is
loaded. It is not imported when aniseed itself is imported.

Because of that, mixins can import application specific libraries, such as
`maya`, `mref` or `aniseed_toolkit`.

The rest of aniseed must stay application agnostic. Outside of the
`components`, `hosts` and `mixins` folders, nothing in aniseed may import an
application specific library. Use `crosswalk` for the little scene
interaction the framework needs.
