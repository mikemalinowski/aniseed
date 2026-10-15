"""
Deprecated parts of aniseed_toolkit which have been removed from the public
modules but are kept importable until aniseed_toolkit 4.0.

Public modules forward unknown attribute lookups here (via a module level
``__getattr__``), so existing code such as ``aniseed_toolkit.guide.create_multi``
keeps working, but logs a DeprecationWarning the first time each name is used.
"""
import warnings
import importlib

# -- Maps (public module name, attribute name) to (legacy module, attribute)
_REDIRECTS = {
    ("aniseed_toolkit.lib.guide", "create_ik_guide"): ("guide", "create_ik_guide"),
    ("aniseed_toolkit.lib.guide", "create_multi"): ("guide", "create_multi"),
    ("aniseed_toolkit.lib.transformation", "TransformMixerUi"): ("transform_mixer_ui", "TransformMixerUi"),
    ("aniseed_toolkit.lib.rigging", "TransformMixer"): ("rigging_transform_mixer", "TransformMixer"),
    ("aniseed_toolkit.lib.rigging", "transform_mixer"): ("rigging_transform_mixer", None),
}

_WARNED = set()


def resolve(module_name: str, attribute: str):
    """
    Returns the deprecated attribute which used to live on the given module,
    or raises AttributeError if there is no such legacy attribute.

    Args:
        module_name: The __name__ of the module the attribute was requested from
        attribute: The attribute being requested

    Returns:
        The legacy object
    """
    try:
        legacy_module, legacy_attribute = _REDIRECTS[(module_name, attribute)]
    except KeyError:
        raise AttributeError(f"module {module_name!r} has no attribute {attribute!r}") from None

    if (module_name, attribute) not in _WARNED:
        _WARNED.add((module_name, attribute))
        warnings.warn(
            f"{module_name}.{attribute} is deprecated and will be removed in aniseed_toolkit 4.0",
            DeprecationWarning,
            stacklevel=3,
        )

    module = importlib.import_module(f"{__name__}.{legacy_module}")
    return getattr(module, legacy_attribute) if legacy_attribute else module
