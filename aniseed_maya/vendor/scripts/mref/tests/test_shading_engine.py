import unittest

import maya.standalone
import mref
from maya import cmds


class TestShadingEngine(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_shading_group(self, name="testSG"):
        return mref.get(cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_shading_engine(self):
        shading_group = self._make_shading_group()
        self.assertIn("ShadingEngine", shading_group.assigned_traits())
        self.assertIn("ObjectSet", shading_group.assigned_traits())

    def test_does_not_bind_to_plain_set(self):
        object_set = mref.get(cmds.sets(empty=True, name="plainSet"))
        self.assertNotIn("ShadingEngine", object_set.assigned_traits())
        self.assertNotIn("ShadingEngine", mref.get("lambert1").assigned_traits())

    # ------------------------------------------------------------------
    # shader slots
    # ------------------------------------------------------------------

    def test_initial_shading_group_surface_shader(self):
        # -- lambert1 before Maya 2026, openPBR_shader1 from 2026 on
        shader = mref.get("initialShadingGroup").surface_shader()
        self.assertIsNotNone(shader)
        expected = cmds.listConnections("initialShadingGroup.surfaceShader", source=True, destination=False)[0]
        self.assertEqual(shader.name(), expected)

    def test_surface_shader_none_when_empty(self):
        self.assertIsNone(self._make_shading_group().surface_shader())

    def test_set_surface_shader(self):
        shading_group = self._make_shading_group()
        shader = cmds.shadingNode("blinn", asShader=True, name="myBlinn")
        shading_group.set_surface_shader(mref.get(shader))
        self.assertEqual(shading_group.surface_shader().name(), "myBlinn")

    def test_set_surface_shader_replaces_and_clears(self):
        shading_group = self._make_shading_group()
        shading_group.set_surface_shader(cmds.shadingNode("blinn", asShader=True, name="a"))
        shading_group.set_surface_shader(cmds.shadingNode("lambert", asShader=True, name="b"))
        self.assertEqual(shading_group.surface_shader().name(), "b")
        shading_group.set_surface_shader(None)
        self.assertIsNone(shading_group.surface_shader())

    def test_displacement_shader_round_trip(self):
        shading_group = self._make_shading_group()
        self.assertIsNone(shading_group.displacement_shader())
        displacement = cmds.shadingNode("displacementShader", asShader=True, name="disp")
        shading_group.set_displacement_shader(displacement)
        self.assertEqual(shading_group.displacement_shader().name(), "disp")
        shading_group.set_displacement_shader(None)
        self.assertIsNone(shading_group.displacement_shader())

    def test_volume_shader_round_trip(self):
        shading_group = self._make_shading_group()
        self.assertIsNone(shading_group.volume_shader())
        fog = cmds.shadingNode("volumeFog", asShader=True, name="fog")
        shading_group.set_volume_shader(mref.get(fog))
        self.assertEqual(shading_group.volume_shader().name(), "fog")
        shading_group.set_volume_shader(None)
        self.assertIsNone(shading_group.volume_shader())

    # ------------------------------------------------------------------
    # assignment
    # ------------------------------------------------------------------

    def test_assigned_geometry_whole_object(self):
        cube = cmds.polyCube(name="cube")[0]
        shading_group = self._make_shading_group()
        shading_group.add_members(cube)
        geometry = shading_group.assigned_geometry()
        self.assertIsInstance(geometry, mref.ReferenceList)
        self.assertEqual(geometry.names(), ["cubeShape"])

    def test_assigned_geometry_from_faces(self):
        cube = cmds.polyCube(name="cube")[0]
        sphere = cmds.polySphere(name="sphere")[0]
        shading_group = self._make_shading_group()
        shading_group.add_members([f"{cube}.f[0:2]", f"{cube}.f[4]", sphere])
        self.assertEqual(
            sorted(shading_group.assigned_geometry().names()),
            ["cubeShape", "sphereShape"],
        )

    def test_assigned_geometry_empty(self):
        self.assertEqual(self._make_shading_group().assigned_geometry(), [])

    def test_assigned_components(self):
        cube = cmds.polyCube(name="cube")[0]
        sphere = cmds.polySphere(name="sphere")[0]
        shading_group = self._make_shading_group()
        shading_group.add_members([f"{cube}.f[0:2]", sphere])
        components = shading_group.assigned_components()
        self.assertEqual(len(components), 1)
        self.assertTrue(components[0].endswith(".f[0:2]"))
        self.assertIn("cube", components[0])

    def test_assigned_components_empty_for_whole_object(self):
        cube = cmds.polyCube(name="cube")[0]
        shading_group = self._make_shading_group()
        shading_group.add_members(cube)
        self.assertEqual(shading_group.assigned_components(), [])


if __name__ == "__main__":
    unittest.main()
