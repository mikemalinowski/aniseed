import unittest

import maya.standalone
import mref
from maya import cmds


class TestFollicle(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_plane(self):
        # -- 10x10 plane centred at the origin, lying on the XZ plane
        return cmds.polyPlane(width=10, height=10, sx=4, sy=4, name="plane")[0]

    def _make_follicle(self):
        shape = cmds.createNode("follicle", name="follicleShape")
        return mref.get(shape)

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_follicle(self):
        follicle = self._make_follicle()
        self.assertIn("Follicle", follicle.assigned_traits())
        self.assertIn("Shape", follicle.assigned_traits())

    def test_does_not_bind_to_unrelated_nodes(self):
        mesh = mref.get(cmds.listRelatives(self._make_plane(), shapes=True, fullPath=True)[0])
        self.assertNotIn("Follicle", mesh.assigned_traits())
        follicle_transform = self._make_follicle().parent()
        self.assertNotIn("Follicle", follicle_transform.assigned_traits())

    # ------------------------------------------------------------------
    # parameters
    # ------------------------------------------------------------------

    def test_parameter_u_round_trip(self):
        follicle = self._make_follicle()
        follicle.set_parameter_u(0.3)
        self.assertAlmostEqual(follicle.parameter_u(), 0.3, places=5)

    def test_parameter_v_round_trip(self):
        follicle = self._make_follicle()
        follicle.set_parameter_v(0.8)
        self.assertAlmostEqual(follicle.parameter_v(), 0.8, places=5)

    # ------------------------------------------------------------------
    # surface / attach_to / detach
    # ------------------------------------------------------------------

    def test_surface_none_when_unattached(self):
        self.assertIsNone(self._make_follicle().surface())

    def test_attach_to_mesh_via_transform(self):
        plane = self._make_plane()
        follicle = self._make_follicle()
        follicle.attach_to(plane, u=0.25, v=0.75)
        self.assertEqual(follicle.surface().name(), "planeShape")
        self.assertAlmostEqual(follicle.parameter_u(), 0.25, places=5)
        self.assertAlmostEqual(follicle.parameter_v(), 0.75, places=5)
        self.assertTrue(cmds.isConnected("planeShape.worldMatrix[0]", f"{follicle.full_name()}.inputWorldMatrix"))

    def test_attach_to_nurbs_surface(self):
        surface = cmds.nurbsPlane(name="nplane")[0]
        surface_shape = cmds.listRelatives(surface, shapes=True, fullPath=True)[0]
        follicle = self._make_follicle()
        follicle.attach_to(surface_shape, u=0.5, v=0.5)
        self.assertEqual(follicle.surface().full_name(), surface_shape)
        self.assertTrue(cmds.isConnected(f"{surface_shape}.local", f"{follicle.full_name()}.inputSurface"))

    def test_attach_to_rejects_non_surface(self):
        follicle = self._make_follicle()
        locator = cmds.spaceLocator()[0]
        with self.assertRaises(RuntimeError):
            follicle.attach_to(locator)

    def test_attach_to_drives_transform(self):
        follicle = self._make_follicle()
        follicle.attach_to(self._make_plane(), u=0.25, v=0.25)
        transform = follicle.parent().full_name()
        self.assertTrue(cmds.isConnected(f"{follicle.full_name()}.outTranslate", f"{transform}.translate"))
        self.assertTrue(cmds.isConnected(f"{follicle.full_name()}.outRotate", f"{transform}.rotate"))

    def test_attach_to_without_driving_transform(self):
        follicle = self._make_follicle()
        follicle.attach_to(self._make_plane(), drive_transform=False)
        transform = follicle.parent().full_name()
        self.assertFalse(cmds.listConnections(f"{transform}.translate", source=True, destination=False))

    def test_detach(self):
        follicle = self._make_follicle()
        follicle.attach_to(self._make_plane())
        follicle.detach()
        self.assertIsNone(follicle.surface())
        self.assertFalse(
            cmds.listConnections(f"{follicle.full_name()}.inputWorldMatrix", source=True, destination=False)
        )

    def test_drive_transform_is_idempotent(self):
        follicle = self._make_follicle()
        follicle.drive_transform()
        follicle.drive_transform()
        transform = follicle.parent().full_name()
        self.assertTrue(cmds.isConnected(f"{follicle.full_name()}.outTranslate", f"{transform}.translate"))

    # ------------------------------------------------------------------
    # evaluated outputs
    # ------------------------------------------------------------------

    def test_world_position(self):
        follicle = self._make_follicle()
        follicle.attach_to(self._make_plane(), u=0.25, v=0.75)
        x, y, z = follicle.world_position()
        self.assertAlmostEqual(x, -2.5, places=4)
        self.assertAlmostEqual(y, 0.0, places=4)
        self.assertAlmostEqual(z, -2.5, places=4)

    def test_world_position_follows_moved_surface(self):
        plane = self._make_plane()
        follicle = self._make_follicle()
        follicle.attach_to(plane, u=0.5, v=0.5)
        cmds.setAttr(f"{plane}.translateY", 4)
        self.assertAlmostEqual(follicle.world_position()[1], 4.0, places=4)

    def test_world_rotation(self):
        follicle = self._make_follicle()
        follicle.attach_to(self._make_plane(), u=0.5, v=0.5)
        rotation = follicle.world_rotation()
        self.assertEqual(len(rotation), 3)
        self.assertAlmostEqual(rotation[0], 90.0, places=3)

    def test_surface_normal(self):
        follicle = self._make_follicle()
        follicle.attach_to(self._make_plane(), u=0.5, v=0.5)
        x, y, z = follicle.surface_normal()
        self.assertAlmostEqual(abs(y), 1.0, places=4)

    def test_hair_system(self):
        follicle = self._make_follicle()
        self.assertIsNone(follicle.hair_system())
        hair = cmds.createNode("hairSystem", name="hairSystemShape")
        cmds.connectAttr(f"{follicle.full_name()}.outHair", f"{hair}.inputHair[0]")
        self.assertEqual(follicle.hair_system().name(), "hairSystemShape")


if __name__ == "__main__":
    unittest.main()
