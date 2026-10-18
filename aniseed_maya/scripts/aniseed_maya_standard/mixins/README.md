# Mixins

Mixins add optional capabilities to a component. A component uses one by
inheriting from it, so the mixins in this folder are imported directly
rather than plugin loaded:

```python
from aniseed_maya_standard.mixins import MirrorMixin


class Arm(aniseed.RigComponent, MirrorMixin):
    ...
```

This folder is part of the `aniseed_maya_standard` aniseed package, so the
mixins can import application specific libraries, such as `maya`, `mref` or
`aniseed_toolkit`.
