import unittest

import maya.standalone
import mref
from maya import cmds


# Names defined on mref that also exist in maya.cmds. Each entry must be
# a deliberate decision — mref's version overrides the cmds default for a
# specific reason (typically ReferencedItem-aware behaviour, or a
# submodule that intentionally takes the cmds name). Adding new entries
# should be rare; prefer renaming the mref symbol to avoid the shadow.
INTENTIONAL_SHADOWS = frozenset({
    "select",  # mref.select converts ReferencedItem -> full_name before cmds.select
    "time",    # mref.time is a submodule of frame-range helpers
})


class TestNameClashes(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass

    def test_mref_does_not_accidentally_shadow_cmds(self):
        """
        Any name defined on the mref package that also exists in
        maya.cmds is a potential source of confusion: a caller may
        believe they are calling cmds via the auto-wrapper, but
        instead hit the mref-specific definition. New clashes must
        be added to INTENTIONAL_SHADOWS so the override is explicit.
        """
        cmds_names = {
            name
            for name in dir(cmds)
            if not name.startswith("_")
        }
        mref_real_attrs = {
            name
            for name in vars(mref)
            if not name.startswith("_")
        }

        clashes = (cmds_names & mref_real_attrs) - INTENTIONAL_SHADOWS

        self.assertFalse(
            clashes,
            (
                f"mref defines names that clash with maya.cmds: "
                f"{sorted(clashes)}. If a clash is intentional, add the "
                f"name to INTENTIONAL_SHADOWS in this test."
            ),
        )


if __name__ == "__main__":
    unittest.main()