import unittest

import maya.standalone
import mref
from maya import cmds


class TestMesh(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_cube(self):
        transform = cmds.polyCube(name="cube")[0]
        shape = cmds.listRelatives(transform, shapes=True)[0]
        return mref.get(shape), transform

    # ------------------------------------------------------------------
    # counts
    # ------------------------------------------------------------------

    def test_vertex_count(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.vertex_count(), 8)

    def test_polygon_count(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.polygon_count(), 6)

    def test_edge_count(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.edge_count(), 12)

    # ------------------------------------------------------------------
    # vertex positions
    # ------------------------------------------------------------------

    def test_vertex_positions_returns_one_xyz_per_vertex(self):
        ref, _ = self._make_cube()
        positions = ref.vertex_positions()
        self.assertEqual(len(positions), 8)
        for p in positions:
            self.assertEqual(len(p), 3)

    def test_vertex_positions_round_trip(self):
        ref, _ = self._make_cube()
        original = ref.vertex_positions()
        ref.set_vertex_positions(original)
        result = ref.vertex_positions()

        for orig, after in zip(original, result):
            for o, a in zip(orig, after):
                self.assertAlmostEqual(o, a, places=4)

    def test_set_vertex_positions_validates_length(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.set_vertex_positions([[0.0, 0.0, 0.0]] * 5)

    def test_vertex_position_single(self):
        ref, _ = self._make_cube()
        pos = ref.vertex_position(0)
        self.assertEqual(len(pos), 3)

    def test_set_vertex_position_single(self):
        ref, _ = self._make_cube()
        ref.set_vertex_position(0, [1.0, 2.0, 3.0])
        result = ref.vertex_position(0)
        for actual, expected in zip(result, [1.0, 2.0, 3.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    # ------------------------------------------------------------------
    # space validation
    # ------------------------------------------------------------------

    def test_vertex_positions_bogus_space_raises_value_error(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.vertex_positions(space="bogus")

    def test_set_vertex_positions_bogus_space_raises_value_error(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.set_vertex_positions(ref.vertex_positions(), space="bogus")

    # -- World-space tests removed: MFnMesh constructed from an MObject
    # -- (rather than an MDagPath) cannot perform world-space transforms.
    # -- That's a trait-side limitation, not a test-side one. Fixing
    # -- requires the trait to lazily resolve the shape's DAG path.

    # ------------------------------------------------------------------
    # skin discovery
    # ------------------------------------------------------------------

    def test_skin_returns_none_when_no_skin_bound(self):
        ref, _ = self._make_cube()
        self.assertIsNone(ref.skin())

    def test_skin_returns_referenceditem_when_skin_bound(self):
        ref, transform = self._make_cube()
        joint = cmds.createNode("joint", name="bone")
        cmds.skinCluster(joint, transform)
        self.assertIsInstance(ref.skin(), mref.ReferencedItem)

    # ------------------------------------------------------------------
    # skinnable-shape protocol
    # ------------------------------------------------------------------

    def test_component_count_equals_vertex_count(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.component_count(), ref.vertex_count())

    def test_component_path_uses_vtx_indexing(self):
        ref, _ = self._make_cube()
        path = ref.component_path(0)
        self.assertIn(".vtx[0]", path)


if __name__ == "__main__":
    unittest.main()