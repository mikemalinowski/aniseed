import unittest

import maya.standalone
import mref
from maya import cmds


class TestNurbsSurface(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_surface(self):
        # -- A 2 x 3 span, degree 3 plane → 5 x 6 CVs, lying in the XZ
        # -- plane (axis = +Y), width 1, parameter range [0, 1] in U and V.
        transform = cmds.nurbsPlane(
            name="plane",
            patchesU=2,
            patchesV=3,
            degree=3,
            axis=(0, 1, 0),
            constructionHistory=False,
        )[0]
        shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        return mref.get(shape), transform

    def _assert_vectors_equal(self, a, b, places=4):
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, places=places)

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_nurbs_surface(self):
        ref, _ = self._make_surface()
        self.assertIn("NurbsSurface", ref.assigned_traits())
        self.assertIn("Shape", ref.assigned_traits())

    def test_does_not_bind_to_mesh(self):
        transform = cmds.polyCube()[0]
        shape = cmds.listRelatives(transform, shapes=True)[0]
        self.assertNotIn("NurbsSurface", mref.get(shape).assigned_traits())

    # ------------------------------------------------------------------
    # counts / degree / ranges
    # ------------------------------------------------------------------

    def test_cv_counts(self):
        ref, _ = self._make_surface()
        self.assertEqual(ref.cv_count_u(), 5)
        self.assertEqual(ref.cv_count_v(), 6)
        self.assertEqual(ref.cv_count(), 30)

    def test_span_counts(self):
        ref, _ = self._make_surface()
        self.assertEqual(ref.span_count_u(), 2)
        self.assertEqual(ref.span_count_v(), 3)

    def test_degrees(self):
        ref, _ = self._make_surface()
        self.assertEqual(ref.degree_u(), 3)
        self.assertEqual(ref.degree_v(), 3)

    def test_parameter_ranges(self):
        ref, _ = self._make_surface()
        self._assert_vectors_equal(ref.parameter_range_u(), (0.0, 1.0))
        self._assert_vectors_equal(ref.parameter_range_v(), (0.0, 1.0))

    # ------------------------------------------------------------------
    # cv positions
    # ------------------------------------------------------------------

    def test_cv_positions_ordering_is_u_outer_v_inner(self):
        ref, _ = self._make_surface()
        positions = ref.cv_positions()
        self.assertEqual(len(positions), 30)
        num_v = ref.cv_count_v()
        for u in range(ref.cv_count_u()):
            for v in range(num_v):
                self._assert_vectors_equal(positions[u * num_v + v], ref.cv_position(u, v))

    def test_cv_positions_round_trip(self):
        ref, _ = self._make_surface()
        original = ref.cv_positions()
        moved = [[x, y + 1.0, z] for x, y, z in original]
        ref.set_cv_positions(moved)
        for expected, actual in zip(moved, ref.cv_positions()):
            self._assert_vectors_equal(actual, expected)

    def test_set_cv_positions_validates_length(self):
        ref, _ = self._make_surface()
        with self.assertRaises(ValueError):
            ref.set_cv_positions([[0.0, 0.0, 0.0]] * 3)

    def test_set_cv_position_single(self):
        ref, _ = self._make_surface()
        ref.set_cv_position(1, 2, [5.0, 6.0, 7.0])
        self._assert_vectors_equal(ref.cv_position(1, 2), [5.0, 6.0, 7.0])
        # -- Value is visible to cmds too, at the same cv[u][v] address
        self._assert_vectors_equal(
            cmds.pointPosition(f"{ref.full_name()}.cv[1][2]", local=True),
            [5.0, 6.0, 7.0],
        )

    def test_world_space_cv_position(self):
        ref, transform = self._make_surface()
        cmds.setAttr(f"{transform}.translate", 0, 10, 0)
        local = ref.cv_position(0, 0)
        world = ref.cv_position(0, 0, space="world")
        self.assertAlmostEqual(world[1], local[1] + 10.0, places=4)

    def test_set_world_space_cv_positions(self):
        ref, transform = self._make_surface()
        cmds.setAttr(f"{transform}.translate", 0, 10, 0)
        world = ref.cv_positions(space="world")
        flattened = [[x, 10.0, z] for x, _, z in world]
        ref.set_cv_positions(flattened, space="world")
        for position in ref.cv_positions():
            self.assertAlmostEqual(position[1], 0.0, places=4)

    def test_bogus_space_raises_value_error(self):
        ref, _ = self._make_surface()
        with self.assertRaises(ValueError):
            ref.cv_positions(space="bogus")

    # ------------------------------------------------------------------
    # surface queries
    # ------------------------------------------------------------------

    def test_point_at_parameter(self):
        ref, _ = self._make_surface()
        self._assert_vectors_equal(ref.point_at_parameter(0.5, 0.5), [0.0, 0.0, 0.0])

    def test_point_at_parameter_world(self):
        ref, transform = self._make_surface()
        cmds.setAttr(f"{transform}.translate", 3, 0, 0)
        self._assert_vectors_equal(
            ref.point_at_parameter(0.5, 0.5, space="world"),
            [3.0, 0.0, 0.0],
        )

    def test_closest_point(self):
        ref, _ = self._make_surface()
        position, u, v = ref.closest_point([0.0, 5.0, 0.0])
        self._assert_vectors_equal(position, [0.0, 0.0, 0.0])
        self.assertAlmostEqual(u, 0.5, places=4)
        self.assertAlmostEqual(v, 0.5, places=4)

    def test_closest_point_world(self):
        ref, transform = self._make_surface()
        cmds.setAttr(f"{transform}.translate", 0, 10, 0)
        position, _, _ = ref.closest_point([0.0, 0.0, 0.0], space="world")
        self._assert_vectors_equal(position, [0.0, 10.0, 0.0])

    # ------------------------------------------------------------------
    # skin
    # ------------------------------------------------------------------

    def test_skin_returns_none_when_no_skin_bound(self):
        ref, _ = self._make_surface()
        self.assertIsNone(ref.skin())

    def test_skin_returns_skin_cluster(self):
        ref, transform = self._make_surface()
        cmds.select(clear=True)
        joint = cmds.joint()
        skin = cmds.skinCluster(joint, transform, toSelectedBones=True)[0]
        result = ref.skin()
        self.assertIsNotNone(result)
        self.assertEqual(result.name(), skin)

    # ------------------------------------------------------------------
    # skinnable-shape protocol
    # ------------------------------------------------------------------

    def test_component_count_equals_cv_count(self):
        ref, _ = self._make_surface()
        self.assertEqual(ref.component_count(), 30)

    def test_component_path_format(self):
        ref, _ = self._make_surface()
        self.assertEqual(ref.component_path(0), f"{ref.full_name()}.cv[0][0]")
        # -- 6 CVs in V, so index 7 is u=1, v=1 and index 11 is u=1, v=5
        self.assertEqual(ref.component_path(7), f"{ref.full_name()}.cv[1][1]")
        self.assertEqual(ref.component_path(11), f"{ref.full_name()}.cv[1][5]")

    def test_component_path_matches_cv_positions_order(self):
        ref, _ = self._make_surface()
        positions = ref.cv_positions()
        for index in (0, 5, 13, 29):
            self._assert_vectors_equal(
                cmds.pointPosition(ref.component_path(index), local=True),
                positions[index],
            )

    def test_skin_cluster_weights_round_trip(self):
        ref, transform = self._make_surface()
        cmds.select(clear=True)
        joint_a = cmds.joint(name="ja", position=(0, 0, -1))
        joint_b = cmds.joint(name="jb", position=(0, 0, 1))
        skin = mref.get(cmds.skinCluster(joint_a, joint_b, transform, toSelectedBones=True)[0])

        weights = skin.weights()
        self.assertEqual(len(weights["weights"][0]), ref.component_count())

        # -- Weight component 7 fully to ja and check via the component path
        index = 7
        weights["weights"][0][index] = 1.0
        weights["weights"][1][index] = 0.0
        skin.set_weights(weights)
        value = cmds.skinPercent(
            skin.name(),
            ref.component_path(index),
            transform=joint_a,
            query=True,
        )
        self.assertAlmostEqual(value, 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
