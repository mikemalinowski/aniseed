import unittest

import maya.standalone
import mref
from maya import cmds


class TestLight(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _arnold(self):
        try:
            cmds.loadPlugin("mtoa", quiet=True)
        except RuntimeError:
            self.skipTest("mtoa is not available")
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            self.skipTest("mtoa is not available")

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_native_lights(self):
        for node_type in ["ambientLight", "directionalLight", "pointLight", "spotLight", "areaLight", "volumeLight"]:
            light = mref.get(cmds.createNode(node_type))
            self.assertIn("Light", light.assigned_traits(), node_type)

    def test_does_not_bind_to_mesh_or_transform(self):
        cube = cmds.polyCube()[0]
        self.assertNotIn("Light", mref.get(cube).assigned_traits())
        shape = cmds.listRelatives(cube, shapes=True)[0]
        self.assertNotIn("Light", mref.get(shape).assigned_traits())
        self.assertNotIn("Light", mref.get("lambert1").assigned_traits())

    def test_binds_to_arnold_lights(self):
        self._arnold()
        for node_type in ["aiAreaLight", "aiSkyDomeLight"]:
            light = mref.get(cmds.createNode(node_type))
            self.assertIn("Light", light.assigned_traits(), node_type)

    def test_spot_light_binds_spot_trait(self):
        spot = mref.get(cmds.createNode("spotLight"))
        self.assertIn("SpotLight", spot.assigned_traits())
        point = mref.get(cmds.createNode("pointLight"))
        self.assertNotIn("SpotLight", point.assigned_traits())

    # ------------------------------------------------------------------
    # colour / intensity
    # ------------------------------------------------------------------

    def test_colour_round_trip(self):
        light = mref.get(cmds.createNode("pointLight"))
        light.set_colour([0.25, 0.5, 0.75])
        for actual, expected in zip(light.colour(), [0.25, 0.5, 0.75]):
            self.assertAlmostEqual(actual, expected)

    def test_intensity_round_trip(self):
        light = mref.get(cmds.createNode("directionalLight"))
        light.set_intensity(3.5)
        self.assertAlmostEqual(light.intensity(), 3.5)

    def test_arnold_colour_and_intensity(self):
        self._arnold()
        light = mref.get(cmds.createNode("aiAreaLight"))
        light.set_colour([1.0, 0.0, 0.0])
        light.set_intensity(4.0)
        self.assertAlmostEqual(light.colour()[0], 1.0)
        self.assertAlmostEqual(light.intensity(), 4.0)

    # ------------------------------------------------------------------
    # light_type
    # ------------------------------------------------------------------

    def test_light_type_native(self):
        expected = {
            "ambientLight": "ambient",
            "directionalLight": "directional",
            "pointLight": "point",
            "spotLight": "spot",
            "areaLight": "area",
            "volumeLight": "volume",
        }
        for node_type, label in expected.items():
            self.assertEqual(mref.get(cmds.createNode(node_type)).light_type(), label)

    def test_light_type_arnold(self):
        self._arnold()
        self.assertEqual(mref.get(cmds.createNode("aiAreaLight")).light_type(), "area")
        self.assertEqual(mref.get(cmds.createNode("aiSkyDomeLight")).light_type(), "skyDome")

    # ------------------------------------------------------------------
    # shadows
    # ------------------------------------------------------------------

    def test_casts_shadows_toggle(self):
        light = mref.get(cmds.createNode("spotLight"))
        # -- Maya 2026 defaults useRayTraceShadows to on
        light.set_casts_shadows(False)
        self.assertFalse(light.casts_shadows())
        light.set_casts_shadows(True)
        self.assertTrue(light.casts_shadows())
        light.set_casts_shadows(False)
        self.assertFalse(light.casts_shadows())

    def test_casts_shadows_sees_depth_map(self):
        light = mref.get(cmds.createNode("spotLight"))
        cmds.setAttr(f"{light.full_name()}.useRayTraceShadows", False)
        cmds.setAttr(f"{light.full_name()}.useDepthMapShadows", True)
        self.assertTrue(light.casts_shadows())
        light.set_casts_shadows(False)
        self.assertFalse(cmds.getAttr(f"{light.full_name()}.useDepthMapShadows"))

    def test_casts_shadows_arnold(self):
        self._arnold()
        light = mref.get(cmds.createNode("aiAreaLight"))
        light.set_casts_shadows(False)
        self.assertFalse(light.casts_shadows())
        light.set_casts_shadows(True)
        self.assertTrue(light.casts_shadows())

    # ------------------------------------------------------------------
    # light linking
    # ------------------------------------------------------------------

    def test_illuminated_objects_defaults_to_all(self):
        cube = cmds.polyCube(name="cube")[0]
        sphere = cmds.polySphere(name="sphere")[0]
        light = mref.get(cmds.pointLight())
        names = light.illuminated_objects().names()
        self.assertIn(cube, names)
        self.assertIn(sphere, names)
        self.assertIsInstance(light.illuminated_objects(), mref.ReferenceList)

    def test_illuminated_objects_excludes_sets(self):
        cmds.polyCube(name="cube")
        light = mref.get(cmds.pointLight())
        self.assertNotIn("initialShadingGroup", light.illuminated_objects().names())

    def test_unlink_and_link_objects(self):
        cube = cmds.polyCube(name="cube")[0]
        sphere = cmds.polySphere(name="sphere")[0]
        light = mref.get(cmds.pointLight())

        light.unlink_objects(mref.get(cube))
        names = light.illuminated_objects().names()
        self.assertNotIn(cube, names)
        self.assertIn(sphere, names)

        light.link_objects([cube])
        self.assertIn(cube, light.illuminated_objects().names())

    # ------------------------------------------------------------------
    # SpotLight
    # ------------------------------------------------------------------

    def test_cone_angle_round_trip(self):
        spot = mref.get(cmds.createNode("spotLight"))
        spot.set_cone_angle(60.0)
        self.assertAlmostEqual(spot.cone_angle(), 60.0)

    def test_penumbra_angle_round_trip(self):
        spot = mref.get(cmds.createNode("spotLight"))
        spot.set_penumbra_angle(5.0)
        self.assertAlmostEqual(spot.penumbra_angle(), 5.0)

    def test_dropoff_round_trip(self):
        spot = mref.get(cmds.createNode("spotLight"))
        spot.set_dropoff(2.0)
        self.assertAlmostEqual(spot.dropoff(), 2.0)

    def test_spot_light_keeps_light_methods(self):
        spot = mref.get(cmds.createNode("spotLight"))
        spot.set_intensity(2.0)
        self.assertAlmostEqual(spot.intensity(), 2.0)
        self.assertEqual(spot.light_type(), "spot")


if __name__ == "__main__":
    unittest.main()
