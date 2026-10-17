import unittest

import maya.standalone
import mref
from maya import cmds


class TestCluster(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_cluster(self):
        cube = cmds.polyCube(name="cube")[0]
        # -- Note: cmds.cluster's name flag returns names which do not
        # -- match the created nodes, so default names are used
        cluster, handle = cmds.cluster(cube)
        return mref.get(cluster), cube, handle

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_cluster(self):
        cluster_ref, _, _ = self._make_cluster()
        traits = cluster_ref.assigned_traits()
        self.assertIn("Cluster", traits)
        self.assertIn("GeometryFilter", traits)

    def test_does_not_bind_to_other_nodes(self):
        _, cube, handle = self._make_cluster()
        handle_shape = cmds.listRelatives(handle, shapes=True)[0]
        for node in (cube, handle, handle_shape):
            self.assertNotIn("Cluster", mref.get(node).assigned_traits())

    def test_does_not_bind_to_other_deformers(self):
        cube = cmds.polyCube()[0]
        bend = cmds.nonLinear(cube, type="bend")[0]
        self.assertNotIn("Cluster", mref.get(bend).assigned_traits())

    # ------------------------------------------------------------------
    # handle / handle_shape
    # ------------------------------------------------------------------

    def test_handle(self):
        cluster_ref, _, handle = self._make_cluster()
        self.assertEqual(cluster_ref.handle().name(), handle)

    def test_handle_shape(self):
        cluster_ref, _, handle = self._make_cluster()
        handle_shape = cmds.listRelatives(handle, shapes=True)[0]
        self.assertEqual(cluster_ref.handle_shape().name(), handle_shape)

    # ------------------------------------------------------------------
    # relative
    # ------------------------------------------------------------------

    def test_relative(self):
        cluster_ref, _, _ = self._make_cluster()
        self.assertFalse(cluster_ref.is_relative())
        cluster_ref.set_relative(True)
        self.assertTrue(cluster_ref.is_relative())
        self.assertTrue(cmds.getAttr(f"{cluster_ref.full_name()}.relative"))

    # ------------------------------------------------------------------
    # weighted node
    # ------------------------------------------------------------------

    def test_weighted_node(self):
        cluster_ref, _, handle = self._make_cluster()
        self.assertEqual(cluster_ref.weighted_node().name(), handle)

    def test_set_weighted_node(self):
        cluster_ref, _, _ = self._make_cluster()
        locator = cmds.spaceLocator(name="loc")[0]
        cluster_ref.set_weighted_node(locator)
        self.assertEqual(cluster_ref.weighted_node().name(), "loc")
        self.assertEqual(cluster_ref.handle().name(), "loc")

    # ------------------------------------------------------------------
    # bind_pre_matrix / rebind
    # ------------------------------------------------------------------

    def test_bind_pre_matrix_default_identity(self):
        cluster_ref, _, _ = self._make_cluster()
        matrix = cluster_ref.bind_pre_matrix()
        self.assertEqual(len(matrix), 16)
        self.assertEqual(matrix, [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                                  0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0])

    def test_rebind(self):
        cluster_ref, cube, handle = self._make_cluster()
        rest = cmds.pointPosition(f"{cube}.vtx[0]", world=True)

        cmds.setAttr(f"{handle}.translateX", 2)
        moved = cmds.pointPosition(f"{cube}.vtx[0]", world=True)
        self.assertAlmostEqual(moved[0], rest[0] + 2)

        cluster_ref.rebind()
        rebound = cmds.pointPosition(f"{cube}.vtx[0]", world=True)
        self.assertAlmostEqual(rebound[0], rest[0])
        self.assertAlmostEqual(cluster_ref.bind_pre_matrix()[12], -2.0)

    # ------------------------------------------------------------------
    # GeometryFilter is also bound
    # ------------------------------------------------------------------

    def test_geometry_filter_envelope(self):
        cluster_ref, _, _ = self._make_cluster()
        self.assertAlmostEqual(cluster_ref.envelope(), 1.0)
        cluster_ref.set_envelope(0.25)
        self.assertAlmostEqual(cluster_ref.envelope(), 0.25)

    def test_geometry_filter_output_geometry(self):
        cluster_ref, _, _ = self._make_cluster()
        self.assertEqual(cluster_ref.output_geometry().names(), ["cubeShape"])

    def test_geometry_filter_deformer_weights(self):
        cluster_ref, _, _ = self._make_cluster()
        self.assertEqual(cluster_ref.deformer_weights(), [1.0] * 8)

        weights = [0.0, 0.5, 1.0, 0.5, 0.0, 0.5, 1.0, 0.5]
        cluster_ref.set_deformer_weights(weights)
        self.assertEqual(cluster_ref.deformer_weights(), weights)


if __name__ == "__main__":
    unittest.main()
