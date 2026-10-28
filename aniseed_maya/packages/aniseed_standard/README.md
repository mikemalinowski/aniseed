# aniseed_standard

This is an aniseed package holding the standard Maya rigging content for
aniseed. It builds on (and requires) `aniseed_utilities`:

* `components/` : the Maya rigging components (limbs, mechanics, the twister
  augment and the rig configurations)
* `rigging/` : the rig building blocks those components use, such as ik / ikfk
  setups, soft ik, foot roll, blend chains, twist, spline and ribbon setups,
  bone alignment and the facial control rig
* `tools/` : toolkit tools, such as the face skeleton load/save tools and the
  twist / ik alignment tools (shown in the Rigging Toolkit)

Components use the rig building blocks and the utility library as:

```python
import aniseed_utilities as au
from aniseed_standard import rigging

rigging.twist.create_twist_setup(...)
au.rig.control.create(...)
```

The modules in `rigging/` import `aniseed_utilities` (as `au`), and each other
relatively.

See `aniseed_utilities/README.md` for how aniseed packages work.
