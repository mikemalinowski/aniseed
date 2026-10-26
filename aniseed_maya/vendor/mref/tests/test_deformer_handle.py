import unittest

import maya.standalone
import mref
from maya import cmds


DEFORMER_TYPES = ["bend", "twist", "flare", "sine", "squash", "wave"]


class TestDeformerHandle(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_handle_shape(self, deformer_type="bend"):
        sphere = cmds.polySphere(name="sphere")[0]
        deformer, handle = cmds.nonLinear(sphere, type=deformer_type)
        handle_shape = cmds.listRelatives(handle, shapes=True)[0]
        return mref.get(handle_shape), deformer, handle

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_every_handle_type(self):
        for deformer_type in DEFORMER_TYPES:
            shape_ref, _, _ = self._make_handle_shape(deformer_type)
            traits = shape_ref.assigned_traits()
            self.assertIn("DeformerHandle", traits, deformer_type)
            self.assertIn("Shape", traits, deformer_type)

    def test_does_not_bind_to_other_nodes(self):
        _, deformer, handle = self._make_handle_shape()
        cluster, cluster_handle = cmds.cluster("sphere")
        cluster_shape = cmds.listRelatives(cluster_handle, shapes=True)[0]
        for node in (deformer, handle, "sphereShape", cluster, cluster_shape):
            self.assertNotIn("DeformerHandle", mref.get(node).assigned_traits())

    # ------------------------------------------------------------------
    # deformer / deformer_type
    # ------------------------------------------------------------------

    def test_deformer(self):
        shape_ref, deformer, _ = self._make_handle_shape()
        self.assertEqual(shape_ref.deformer().name(), deformer)
        self.assertIn("NonLinear", shape_ref.deformer().assigned_traits())

    def test_deformer_none_when_disconnected(self):
        shape_ref, deformer, _ = self._make_handle_shape()
        cmds.disconnectAttr(f"{shape_ref.full_name()}.deformerData", f"{deformer}.deformerData")
        self.assertIsNone(shape_ref.deformer())
        self.assertEqual(shape_ref.deformed_geometry(), [])

    def test_deformer_type(self):
        for deformer_type in DEFORMER_TYPES:
            shape_ref, _, _ = self._make_handle_shape(deformer_type)
            self.assertEqual(shape_ref.deformer_type(), deformer_type)

    def test_transform_is_handle(self):
        shape_ref, _, handle = self._make_handle_shape()
        self.assertEqual(shape_ref.transform().name(), handle)

    # ------------------------------------------------------------------
    # deformed_geometry
    # ------------------------------------------------------------------

    def test_deformed_geometry(self):
        shape_ref, _, _ = self._make_handle_shape("wave")
        result = shape_ref.deformed_geometry()
        self.assertIsInstance(result, mref.ReferenceList)
        self.assertEqual(result.names(), ["sphereShape"])


if __name__ == "__main__":
    unittest.main()
