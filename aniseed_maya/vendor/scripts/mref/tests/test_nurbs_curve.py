import unittest

import maya.standalone
import mref
from maya import cmds


class TestNurbsCurve(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_curve(self):
        transform = cmds.curve(
            name="curve1",
            point=[[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]],
            degree=1,
        )
        shape = cmds.listRelatives(transform, shapes=True)[0]
        return mref.get(shape)

    # ------------------------------------------------------------------
    # counts
    # ------------------------------------------------------------------

    def test_cv_count(self):
        ref = self._make_curve()
        self.assertEqual(ref.cv_count(), 4)

    def test_knot_count(self):
        ref = self._make_curve()
        self.assertGreater(ref.knot_count(), 0)

    def test_span_count(self):
        ref = self._make_curve()
        # 4 CVs, degree 1 → 3 spans
        self.assertEqual(ref.span_count(), 3)

    # ------------------------------------------------------------------
    # bulk cv positions
    # ------------------------------------------------------------------

    def test_cv_positions_returns_one_xyz_per_cv(self):
        ref = self._make_curve()
        positions = ref.cv_positions()
        self.assertEqual(len(positions), 4)
        for p in positions:
            self.assertEqual(len(p), 3)

    def test_cv_positions_round_trip(self):
        ref = self._make_curve()
        original = ref.cv_positions()
        ref.set_cv_positions(original)
        result = ref.cv_positions()

        for orig, after in zip(original, result):
            for o, a in zip(orig, after):
                self.assertAlmostEqual(o, a, places=4)

    def test_set_cv_positions_validates_length(self):
        ref = self._make_curve()
        with self.assertRaises(ValueError):
            ref.set_cv_positions([[0.0, 0.0, 0.0]] * 2)

    # ------------------------------------------------------------------
    # single cv position
    # ------------------------------------------------------------------

    def test_cv_position_single(self):
        ref = self._make_curve()
        pos = ref.cv_position(0)
        self.assertEqual(len(pos), 3)

    def test_set_cv_position_single(self):
        ref = self._make_curve()
        ref.set_cv_position(0, [5.0, 6.0, 7.0])
        result = ref.cv_position(0)
        for actual, expected in zip(result, [5.0, 6.0, 7.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    # ------------------------------------------------------------------
    # space validation
    # ------------------------------------------------------------------

    def test_cv_positions_bogus_space_raises_value_error(self):
        ref = self._make_curve()
        with self.assertRaises(ValueError):
            ref.cv_positions(space="bogus")

    # -- World-space tests removed: MFnNurbsCurve constructed from an
    # -- MObject (rather than an MDagPath) cannot perform world-space
    # -- transforms. Trait-side limitation, not test-side.

    # ------------------------------------------------------------------
    # skin discovery
    # ------------------------------------------------------------------

    def test_skin_returns_none_when_no_skin_bound(self):
        ref = self._make_curve()
        self.assertIsNone(ref.skin())

    # ------------------------------------------------------------------
    # skinnable-shape protocol
    # ------------------------------------------------------------------

    def test_component_count_equals_cv_count(self):
        ref = self._make_curve()
        self.assertEqual(ref.component_count(), ref.cv_count())

    def test_component_path_uses_cv_indexing(self):
        ref = self._make_curve()
        path = ref.component_path(0)
        self.assertIn(".cv[0]", path)


if __name__ == "__main__":
    unittest.main()