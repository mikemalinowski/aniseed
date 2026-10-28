# Mixins

Mixins add optional capabilities to a component. A component uses one by
inheriting from it, so the mixins in this folder are imported directly
rather than plugin loaded:

```python
import aniseed_utilities as au


class Arm(aniseed.RigComponent, au.mixins.MirrorMixin):
    ...
```

This folder is part of the `aniseed_utilities` aniseed package, so the
mixins can import application specific libraries, such as `maya` and `mref`,
and the rest of `aniseed_utilities` (relatively, as they are part of its
library).
