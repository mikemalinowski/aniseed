import unittest

import maya.standalone
import mref
from maya import cmds


class TestShader(unittest.TestCase):

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

    def _make_shader(self, node_type="lambert", name="myShader"):
        return mref.get(cmds.shadingNode(node_type, asShader=True, name=name))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_surface_shaders(self):
        for node_type in ["lambert", "blinn", "phong", "standardSurface", "surfaceShader"]:
            shader = self._make_shader(node_type, name=f"{node_type}_test")
            self.assertIn("Shader", shader.assigned_traits(), node_type)

    def test_binds_to_arnold_shader(self):
        self._arnold()
        shader = self._make_shader("aiStandardSurface", name="aiShader")
        self.assertIn("Shader", shader.assigned_traits())

    def test_does_not_bind_to_non_shaders(self):
        file_node = cmds.shadingNode("file", asTexture=True)
        self.assertNotIn("Shader", mref.get(file_node).assigned_traits())
        self.assertNotIn("Shader", mref.get("initialShadingGroup").assigned_traits())
        displacement = cmds.shadingNode("displacementShader", asShader=True)
        self.assertNotIn("Shader", mref.get(displacement).assigned_traits())
        self.assertNotIn("Shader", mref.get(cmds.polyCube()[0]).assigned_traits())

    # ------------------------------------------------------------------
    # shading groups
    # ------------------------------------------------------------------

    def test_shading_groups_of_default_shader(self):
        # -- lambert1 before Maya 2026, openPBR_shader1 from 2026 on
        default = cmds.listConnections("initialShadingGroup.surfaceShader", source=True, destination=False)[0]
        groups = mref.get(default).shading_groups()
        self.assertIsInstance(groups, mref.ReferenceList)
        self.assertIn("initialShadingGroup", groups.names())

    def test_shading_groups_lists_each_group(self):
        shader = self._make_shader()
        for name in ["sgA", "sgB"]:
            shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name)
            cmds.connectAttr(f"{shader.full_name()}.outColor", f"{shading_group}.surfaceShader")
        self.assertEqual(sorted(shader.shading_groups().names()), ["sgA", "sgB"])

    def test_shading_groups_empty_for_new_shader(self):
        self.assertEqual(self._make_shader().shading_groups(), [])

    def test_create_shading_group_creates_once(self):
        shader = self._make_shader()
        shading_group = shader.create_shading_group()
        self.assertEqual(shading_group.name(), "myShaderSG")
        self.assertIn("ShadingEngine", shading_group.assigned_traits())
        self.assertEqual(shading_group.surface_shader().name(), "myShader")

        again = shader.create_shading_group()
        self.assertEqual(again, shading_group)
        self.assertEqual(len(shader.shading_groups()), 1)

    # ------------------------------------------------------------------
    # assignment
    # ------------------------------------------------------------------

    def test_assign_to_object(self):
        cube = cmds.polyCube(name="cube")[0]
        shader = self._make_shader()
        shader.assign_to(mref.get(cube))
        self.assertEqual(shader.assigned_geometry().names(), ["cubeShape"])
        self.assertNotIn(
            "cubeShape",
            mref.get("initialShadingGroup").assigned_geometry().names(),
        )

    def test_assign_to_faces(self):
        cube = cmds.polyCube(name="cube")[0]
        sphere = cmds.polySphere(name="sphere")[0]
        shader = self._make_shader()
        shader.assign_to([f"{cube}.f[0:1]", sphere])
        self.assertEqual(
            sorted(shader.assigned_geometry().names()),
            ["cubeShape", "sphereShape"],
        )

    def test_assigned_geometry_empty(self):
        self.assertEqual(self._make_shader().assigned_geometry(), [])

    # ------------------------------------------------------------------
    # colour
    # ------------------------------------------------------------------

    def test_colour_attribute_by_type(self):
        expected = {
            "lambert": "color",
            "blinn": "color",
            "standardSurface": "baseColor",
            "openPBRSurface": "baseColor",
            "surfaceShader": "outColor",
        }
        available = set(cmds.allNodeTypes())
        for node_type, attribute_name in expected.items():
            # -- openPBRSurface only exists from Maya 2026; creating an
            # -- unregistered type silently makes an "unknown" node instead
            if node_type not in available:
                continue
            shader = self._make_shader(node_type, name=f"{node_type}_test")
            attribute = shader.colour_attribute()
            self.assertIsNotNone(attribute, node_type)
            self.assertEqual(attribute.name(), attribute_name, node_type)

    def test_colour_round_trip(self):
        for node_type in ["lambert", "standardSurface", "surfaceShader"]:
            shader = self._make_shader(node_type, name=f"{node_type}_test")
            shader.set_colour([0.1, 0.2, 0.3])
            for actual, expected in zip(shader.colour(), [0.1, 0.2, 0.3]):
                self.assertAlmostEqual(actual, expected, places=5, msg=node_type)

    def test_colour_arnold(self):
        self._arnold()
        shader = self._make_shader("aiStandardSurface", name="aiShader")
        self.assertEqual(shader.colour_attribute().name(), "baseColor")
        shader.set_colour([1.0, 0.5, 0.0])
        self.assertAlmostEqual(shader.colour()[1], 0.5)

    def test_colour_none_when_unsupported(self):
        # -- A layered shader classifies as a surface shader but has no
        # -- single colour attribute.
        shader = self._make_shader("layeredShader", name="layered")
        if "Shader" not in shader.assigned_traits():
            self.skipTest("layeredShader not classified as a surface shader")
        self.assertIsNone(shader.colour_attribute())
        self.assertIsNone(shader.colour())
        with self.assertRaises(RuntimeError):
            shader.set_colour([1, 0, 0])


if __name__ == "__main__":
    unittest.main()
