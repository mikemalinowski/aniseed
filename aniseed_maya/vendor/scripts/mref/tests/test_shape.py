import unittest

import maya.standalone
import mref
from maya import cmds


class TestShape(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_cube(self):
        transform = cmds.polyCube(name="cube", constructionHistory=False)[0]
        shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        return mref.get(shape), transform

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_shapes(self):
        shape, _ = self._make_cube()
        self.assertIn("Shape", shape.assigned_traits())

    def test_does_not_bind_to_transforms(self):
        _, transform = self._make_cube()
        self.assertNotIn("Shape", mref.get(transform).assigned_traits())

    def test_mesh_trait_still_wins(self):
        # -- Mesh has a higher priority, so its methods must still resolve
        shape, _ = self._make_cube()
        self.assertEqual(shape.vertex_count(), 8)

    # ------------------------------------------------------------------
    # transform / intermediate
    # ------------------------------------------------------------------

    def test_transform_returns_owner(self):
        shape, _ = self._make_cube()
        self.assertEqual(shape.transform().name(), "cube")

    def test_intermediate_round_trip(self):
        shape, _ = self._make_cube()
        self.assertFalse(shape.is_intermediate())
        shape.set_intermediate(True)
        self.assertTrue(shape.is_intermediate())
        shape.set_intermediate(False)
        self.assertFalse(shape.is_intermediate())

    # ------------------------------------------------------------------
    # bounding_box
    # ------------------------------------------------------------------

    def test_bounding_box_object_space(self):
        shape, _ = self._make_cube()
        minimum, maximum = shape.bounding_box()
        for value in minimum:
            self.assertAlmostEqual(value, -0.5)
        for value in maximum:
            self.assertAlmostEqual(value, 0.5)

    def test_bounding_box_world_space(self):
        shape, transform = self._make_cube()
        cmds.setAttr(f"{transform}.translateX", 10)

        minimum, maximum = shape.bounding_box(space="world")
        self.assertAlmostEqual(minimum[0], 9.5)
        self.assertAlmostEqual(maximum[0], 10.5)

        # -- Object space is unaffected by the transform
        minimum, _ = shape.bounding_box(space="object")
        self.assertAlmostEqual(minimum[0], -0.5)

    def test_bounding_box_invalid_space(self):
        shape, _ = self._make_cube()
        with self.assertRaises(ValueError):
            shape.bounding_box(space="local")

    # ------------------------------------------------------------------
    # deformers
    # ------------------------------------------------------------------

    def test_deformers_empty(self):
        shape, _ = self._make_cube()
        self.assertEqual(len(shape.deformers()), 0)

    def test_deformers_lists_stack(self):
        shape, transform = self._make_cube()
        joint = cmds.createNode("joint")
        cmds.skinCluster(joint, transform)
        cmds.cluster(transform)

        deformers = shape.deformers()
        self.assertEqual(len(deformers), 2)
        self.assertIsInstance(deformers, mref.ReferenceList)

        skins = shape.deformers(node_type="skinCluster")
        self.assertEqual(len(skins), 1)
        self.assertEqual(skins[0].node_type(), "skinCluster")


if __name__ == "__main__":
    unittest.main()
