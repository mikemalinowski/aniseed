import unittest

import maya.standalone
import mref
from maya import cmds


class TestGeometryFilter(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_cluster(self):
        transform = cmds.polyCube(name="cube", constructionHistory=False)[0]
        shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        cluster = cmds.cluster(transform)[0]
        return mref.get(cluster), mref.get(shape)

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_deformers(self):
        cluster, _ = self._make_cluster()
        self.assertIn("GeometryFilter", cluster.assigned_traits())

    def test_binds_to_skin_cluster(self):
        transform = cmds.polyCube(constructionHistory=False)[0]
        skin = mref.get(cmds.skinCluster(cmds.createNode("joint"), transform)[0])
        self.assertIn("GeometryFilter", skin.assigned_traits())
        self.assertIn("SkinCluster", skin.assigned_traits())

        # -- SkinCluster's own methods must still resolve
        self.assertEqual(len(skin.influences()), 1)

    def test_does_not_bind_to_transforms(self):
        node = mref.create("transform")
        self.assertNotIn("GeometryFilter", node.assigned_traits())

    # ------------------------------------------------------------------
    # geometry
    # ------------------------------------------------------------------

    def test_output_geometry(self):
        cluster, shape = self._make_cluster()
        outputs = cluster.output_geometry()
        self.assertIsInstance(outputs, mref.ReferenceList)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0], shape)

    def test_input_geometry(self):
        cluster, shape = self._make_cluster()
        inputs = cluster.input_geometry()
        self.assertEqual(len(inputs), 1)
        # -- The input is the intermediate orig shape, not the deformed one
        self.assertNotEqual(inputs[0], shape)
        self.assertTrue(inputs[0].is_intermediate())

    def test_geometry_index(self):
        cluster, shape = self._make_cluster()
        self.assertEqual(cluster.geometry_index(shape), 0)
        self.assertEqual(cluster.geometry_index(shape.full_name()), 0)

    # ------------------------------------------------------------------
    # envelope
    # ------------------------------------------------------------------

    def test_envelope_round_trip(self):
        cluster, _ = self._make_cluster()
        self.assertAlmostEqual(cluster.envelope(), 1.0)
        cluster.set_envelope(0.25)
        self.assertAlmostEqual(cluster.envelope(), 0.25)

    # ------------------------------------------------------------------
    # deformer weights
    # ------------------------------------------------------------------

    def test_deformer_weights_default(self):
        cluster, _ = self._make_cluster()
        weights = cluster.deformer_weights()
        self.assertEqual(len(weights), 8)
        for weight in weights:
            self.assertAlmostEqual(weight, 1.0)

    def test_set_deformer_weights(self):
        cluster, shape = self._make_cluster()
        values = [i / 10.0 for i in range(8)]
        cluster.set_deformer_weights(values, shape)

        for read, expected in zip(cluster.deformer_weights(shape), values):
            self.assertAlmostEqual(read, expected, places=5)

    def test_set_deformer_weights_affects_deformation(self):
        cluster, shape = self._make_cluster()
        cluster.set_deformer_weights([0.0] * 7 + [1.0])

        handle = cmds.listConnections(f"{cluster.full_name()}.matrix")[0]
        cmds.setAttr(f"{handle}.translateY", 1.0)

        # -- polyCube vertices 0 and 7 both start at y=-0.5; only the
        # -- fully weighted vertex 7 should follow the handle
        positions = shape.vertex_positions()
        self.assertAlmostEqual(positions[0][1], -0.5)
        self.assertAlmostEqual(positions[7][1], 0.5)

    def test_set_deformer_weights_wrong_length(self):
        cluster, _ = self._make_cluster()
        with self.assertRaises(ValueError):
            cluster.set_deformer_weights([1.0, 1.0])


if __name__ == "__main__":
    unittest.main()
