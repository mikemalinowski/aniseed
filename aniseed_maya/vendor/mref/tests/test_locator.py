import unittest

import maya.standalone
import mref
from maya import cmds


class TestLocator(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_locator(self):
        transform = cmds.spaceLocator(name="loc")[0]
        shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        return mref.get(shape), transform

    def _assert_vectors_equal(self, a, b, places=4):
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, places=places)

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_locator_shape(self):
        ref, _ = self._make_locator()
        self.assertIn("Locator", ref.assigned_traits())
        self.assertIn("Shape", ref.assigned_traits())

    def test_does_not_bind_to_transform(self):
        _, transform = self._make_locator()
        self.assertNotIn("Locator", mref.get(transform).assigned_traits())

    # ------------------------------------------------------------------
    # local position / scale
    # ------------------------------------------------------------------

    def test_local_position_round_trip(self):
        ref, _ = self._make_locator()
        self._assert_vectors_equal(ref.local_position(), [0, 0, 0])
        ref.set_local_position([1.0, 2.0, 3.0])
        self._assert_vectors_equal(ref.local_position(), [1.0, 2.0, 3.0])

    def test_local_scale_round_trip(self):
        ref, _ = self._make_locator()
        self._assert_vectors_equal(ref.local_scale(), [1, 1, 1])
        ref.set_local_scale([2.0, 3.0, 4.0])
        self._assert_vectors_equal(ref.local_scale(), [2.0, 3.0, 4.0])

    def test_set_local_scale_uniform(self):
        ref, _ = self._make_locator()
        ref.set_local_scale(5.0)
        self._assert_vectors_equal(ref.local_scale(), [5.0, 5.0, 5.0])

    # ------------------------------------------------------------------
    # world position
    # ------------------------------------------------------------------

    def test_world_position_includes_transform_and_local_offset(self):
        ref, transform = self._make_locator()
        cmds.setAttr(f"{transform}.translate", 10, 0, 0)
        ref.set_local_position([0.0, 1.0, 0.0])
        self._assert_vectors_equal(ref.world_position(), [10.0, 1.0, 0.0])


if __name__ == "__main__":
    unittest.main()
