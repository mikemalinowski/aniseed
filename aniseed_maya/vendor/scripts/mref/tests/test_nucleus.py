import unittest

import maya.standalone
import mref
from maya import cmds
from maya import mel


class TestNucleus(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_scene(self):
        """
        Builds an nCloth plane and an nRigid sphere sharing one solver
        """
        plane = cmds.polyPlane(sx=4, sy=4, name="clothPlane")[0]
        sphere = cmds.polySphere(name="collider")[0]
        try:
            cmds.select(plane)
            cloth = mel.eval("createNCloth 0")
            cmds.select(sphere)
            rigid = mel.eval("makeCollideNCloth")
        except RuntimeError as exc:
            self.skipTest(f"nCloth creation failed in standalone: {exc}")
        if not cloth or not rigid:
            self.skipTest("nCloth creation returned nothing")
        return mref.get(cmds.ls(type="nucleus")[0]), cloth[0], rigid[0]

    def _make_nucleus(self):
        return mref.get(cmds.createNode("nucleus", name="solver"))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_nucleus(self):
        nucleus = self._make_nucleus()
        self.assertIn("Nucleus", nucleus.assigned_traits())
        self.assertIn("Transform", nucleus.assigned_traits())

    def test_does_not_bind_to_unrelated_nodes(self):
        for node_type in ("transform", "nCloth", "hairSystem"):
            node = mref.get(cmds.createNode(node_type))
            self.assertNotIn("Nucleus", node.assigned_traits(), node_type)

    # ------------------------------------------------------------------
    # objects
    # ------------------------------------------------------------------

    def test_active_objects(self):
        nucleus, cloth, _ = self._make_scene()
        self.assertEqual(nucleus.active_objects().names(), [cloth])

    def test_passive_objects(self):
        nucleus, _, rigid = self._make_scene()
        self.assertEqual(nucleus.passive_objects().names(), [rigid])

    def test_objects(self):
        nucleus, cloth, rigid = self._make_scene()
        objects = nucleus.objects()
        self.assertIsInstance(objects, mref.ReferenceList)
        self.assertEqual(objects.names(), [cloth, rigid])

    def test_objects_empty(self):
        self.assertEqual(len(self._make_nucleus().objects()), 0)

    def test_add_object(self):
        nucleus = self._make_nucleus()
        hair = cmds.createNode("hairSystem", name="hairShape")
        nucleus.add_object(hair)
        self.assertEqual(nucleus.active_objects().names(), ["hairShape"])

    def test_add_object_moves_between_solvers(self):
        old_nucleus, cloth, _ = self._make_scene()
        new_nucleus = self._make_nucleus()
        new_nucleus.add_object(cloth)
        self.assertEqual(new_nucleus.active_objects().names(), [cloth])
        self.assertEqual(len(old_nucleus.active_objects()), 0)

    # ------------------------------------------------------------------
    # gravity
    # ------------------------------------------------------------------

    def test_gravity_round_trip(self):
        nucleus = self._make_nucleus()
        self.assertAlmostEqual(nucleus.gravity(), 9.8, places=4)
        nucleus.set_gravity(3.5)
        self.assertAlmostEqual(nucleus.gravity(), 3.5, places=4)

    def test_gravity_direction_round_trip(self):
        nucleus = self._make_nucleus()
        self.assertEqual(nucleus.gravity_direction(), [0.0, -1.0, 0.0])
        nucleus.set_gravity_direction([1, 0, 0])
        self.assertEqual(nucleus.gravity_direction(), [1.0, 0.0, 0.0])

    # ------------------------------------------------------------------
    # start frame
    # ------------------------------------------------------------------

    def test_start_frame_round_trip(self):
        nucleus = self._make_nucleus()
        nucleus.set_start_frame(25)
        self.assertEqual(nucleus.start_frame(), 25)

    # ------------------------------------------------------------------
    # enable / disable
    # ------------------------------------------------------------------

    def test_enable_disable(self):
        nucleus = self._make_nucleus()
        self.assertTrue(nucleus.is_enabled())
        nucleus.disable()
        self.assertFalse(nucleus.is_enabled())
        nucleus.enable()
        self.assertTrue(nucleus.is_enabled())


if __name__ == "__main__":
    unittest.main()
