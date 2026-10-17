import unittest

import maya.standalone
import mref
from maya import cmds


class TestClusterHandle(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_cluster(self):
        transform = cmds.polyCube(name="cube", constructionHistory=False)[0]
        cluster, handle = cmds.cluster(transform)
        handle_shape = cmds.listRelatives(handle, shapes=True, fullPath=True)[0]
        return mref.get(cluster), mref.get(handle_shape), transform

    def test_binds_to_handle_shape(self):
        _, handle_shape, _ = self._make_cluster()
        self.assertIn("ClusterHandle", handle_shape.assigned_traits())
        self.assertIn("Shape", handle_shape.assigned_traits())

    def test_does_not_bind_to_cluster_deformer(self):
        cluster, _, _ = self._make_cluster()
        self.assertNotIn("ClusterHandle", cluster.assigned_traits())

    def test_deformer(self):
        cluster, handle_shape, _ = self._make_cluster()
        self.assertEqual(handle_shape.deformer(), cluster)

    def test_deformer_none_when_disconnected(self):
        handle_shape = mref.create("clusterHandle")
        self.assertIsNone(handle_shape.deformer())
        self.assertEqual(len(handle_shape.deformed_geometry()), 0)

    def test_deformed_geometry(self):
        _, handle_shape, transform = self._make_cluster()
        geometry = handle_shape.deformed_geometry()
        self.assertIsInstance(geometry, mref.ReferenceList)
        self.assertEqual(len(geometry), 1)
        self.assertEqual(geometry[0].transform().name(), transform)


if __name__ == "__main__":
    unittest.main()
