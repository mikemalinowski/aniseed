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

    def _make_cubic(self):
        transform = cmds.curve(
            name="cubic1",
            point=[[0, 0, 0], [1, 1, 0], [2, -1, 0], [3, 1, 0], [4, 0, 0]],
            degree=3,
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

    # ------------------------------------------------------------------
    # binding / world space
    # ------------------------------------------------------------------

    def test_binds_to_curve(self):
        ref = self._make_curve()
        self.assertIn("NurbsCurve", ref.assigned_traits())

    def test_does_not_bind_to_unrelated_node(self):
        ref = mref.get(cmds.createNode("transform"))
        self.assertNotIn("NurbsCurve", ref.assigned_traits())

    def test_binds_to_empty_curve_node(self):
        ref = mref.get(cmds.createNode("nurbsCurve"))
        self.assertIsInstance(ref, mref.ReferencedItem)
        self.assertIn("NurbsCurve", ref.assigned_traits())

    def test_cv_position_world_space(self):
        ref = self._make_curve()
        cmds.setAttr("curve1.translateY", 10)
        self.assertAlmostEqual(ref.cv_position(1, space="world")[1], 10.0, places=4)
        self.assertAlmostEqual(ref.cv_position(1)[1], 0.0, places=4)

    def test_cv_positions_world_space(self):
        ref = self._make_curve()
        cmds.setAttr("curve1.translateZ", 4)
        for p in ref.cv_positions(space="world"):
            self.assertAlmostEqual(p[2], 4.0, places=4)

    def test_set_cv_position_world_space(self):
        ref = self._make_curve()
        cmds.setAttr("curve1.translateY", 10)
        ref.set_cv_position(0, [0.0, 10.0, 0.0], space="world")
        self.assertAlmostEqual(ref.cv_position(0)[1], 0.0, places=4)

    def test_set_cv_positions_world_space(self):
        ref = self._make_curve()
        cmds.setAttr("curve1.translateY", 10)
        ref.set_cv_positions(ref.cv_positions(space="world"), space="world")
        for p in ref.cv_positions():
            self.assertAlmostEqual(p[1], 0.0, places=4)

    def test_world_space_survives_reparent(self):
        ref = self._make_curve()
        parent = cmds.createNode("transform", name="offset")
        cmds.setAttr(f"{parent}.translateX", 7)
        cmds.parent("curve1", parent, relative=True)
        self.assertAlmostEqual(ref.cv_position(0, space="world")[0], 7.0, places=4)

    # ------------------------------------------------------------------
    # structure
    # ------------------------------------------------------------------

    def test_degree(self):
        self.assertEqual(self._make_curve().degree(), 1)
        self.assertEqual(self._make_cubic().degree(), 3)

    def test_form_open(self):
        self.assertEqual(self._make_curve().form(), "open")

    def test_form_periodic(self):
        transform = cmds.circle(constructionHistory=False)[0]
        ref = mref.get(cmds.listRelatives(transform, shapes=True)[0])
        self.assertEqual(ref.form(), "periodic")

    def test_knots(self):
        ref = self._make_curve()
        knots = ref.knots()
        self.assertEqual(len(knots), ref.knot_count())
        self.assertEqual(knots, sorted(knots))

    def test_parameter_range(self):
        ref = self._make_curve()
        self.assertEqual(ref.parameter_range(), (0.0, 3.0))

    def test_length(self):
        self.assertAlmostEqual(self._make_curve().length(), 3.0, places=4)

    # ------------------------------------------------------------------
    # parametric queries
    # ------------------------------------------------------------------

    def test_point_at_parameter(self):
        ref = self._make_curve()
        for actual, expected in zip(ref.point_at_parameter(1.5), [1.5, 0.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_point_at_parameter_world_space(self):
        ref = self._make_curve()
        cmds.setAttr("curve1.translateY", 10)
        self.assertAlmostEqual(ref.point_at_parameter(1.5, space="world")[1], 10.0, places=4)

    def test_tangent_at_parameter(self):
        ref = self._make_curve()
        for actual, expected in zip(ref.tangent_at_parameter(1.5), [1.0, 0.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_tangent_at_parameter_world_space(self):
        ref = self._make_curve()
        cmds.setAttr("curve1.rotateZ", 90)
        for actual, expected in zip(ref.tangent_at_parameter(1.5, space="world"), [0.0, 1.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_normal_at_parameter(self):
        transform = cmds.circle(normal=[0, 1, 0], constructionHistory=False)[0]
        ref = mref.get(cmds.listRelatives(transform, shapes=True)[0])
        parameter = sum(ref.parameter_range()) * 0.5
        normal = ref.normal_at_parameter(parameter)
        tangent = ref.tangent_at_parameter(parameter)
        self.assertAlmostEqual(sum(n * n for n in normal), 1.0, places=4)
        self.assertAlmostEqual(sum(n * t for n, t in zip(normal, tangent)), 0.0, places=4)

    def test_parameter_at_length(self):
        ref = self._make_curve()
        self.assertAlmostEqual(ref.parameter_at_length(1.5), 1.5, places=3)

    def test_parameter_at_length_clamps(self):
        ref = self._make_curve()
        self.assertAlmostEqual(ref.parameter_at_length(100.0), 3.0, places=3)

    def test_closest_point(self):
        ref = self._make_curve()
        point, parameter = ref.closest_point([2.0, 5.0, 0.0])
        for actual, expected in zip(point, [2.0, 0.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)
        self.assertAlmostEqual(parameter, 2.0, places=4)

    def test_closest_point_world_space(self):
        ref = self._make_curve()
        cmds.setAttr("curve1.translateY", 10)
        point, parameter = ref.closest_point([1.0, 20.0, 0.0], space="world")
        self.assertAlmostEqual(point[1], 10.0, places=4)
        self.assertAlmostEqual(parameter, 1.0, places=4)

    def test_parameter_at_point(self):
        ref = self._make_curve()
        self.assertAlmostEqual(ref.parameter_at_point([2.5, 1.0, 0.0]), 2.5, places=4)

    # ------------------------------------------------------------------
    # editing
    # ------------------------------------------------------------------

    def test_reverse(self):
        ref = self._make_curve()
        original = ref.cv_positions()
        ref.reverse()
        for expected, actual in zip(reversed(original), ref.cv_positions()):
            for e, a in zip(expected, actual):
                self.assertAlmostEqual(e, a, places=4)

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