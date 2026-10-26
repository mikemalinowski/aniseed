import os
import shutil
import tempfile
import unittest

import maya.standalone
import mref
from maya import cmds


class TestFileTexture(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)
        self.directory = tempfile.mkdtemp(prefix="mref_file_texture_")

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _touch(self, name):
        path = os.path.join(self.directory, name).replace("\\", "/")
        with open(path, "w") as handle:
            handle.write("")
        return path

    def _make_texture(self):
        node = cmds.shadingNode("file", asTexture=True, name="tex")
        place = cmds.shadingNode("place2dTexture", asUtility=True, name="place")
        cmds.connectAttr(f"{place}.outUV", f"{node}.uvCoord")
        return mref.get(node)

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_file_node(self):
        self.assertIn("FileTexture", self._make_texture().assigned_traits())

    def test_does_not_bind_to_other_textures(self):
        checker = cmds.shadingNode("checker", asTexture=True)
        self.assertNotIn("FileTexture", mref.get(checker).assigned_traits())
        self.assertNotIn("FileTexture", mref.get("lambert1").assigned_traits())

    # ------------------------------------------------------------------
    # path / colour space
    # ------------------------------------------------------------------

    def test_file_path_round_trip(self):
        texture = self._make_texture()
        self.assertEqual(texture.file_path(), "")
        texture.set_file_path("C:/textures/wood.<UDIM>.png")
        self.assertEqual(texture.file_path(), "C:/textures/wood.<UDIM>.png")

    def test_colour_space_round_trip(self):
        texture = self._make_texture()
        texture.set_colour_space("Raw")
        self.assertEqual(texture.colour_space(), "Raw")
        # -- Changing the path must not let file rules override it
        texture.set_file_path(self._touch("albedo.png"))
        self.assertEqual(texture.colour_space(), "Raw")

    # ------------------------------------------------------------------
    # tiling
    # ------------------------------------------------------------------

    def test_tiling_mode_round_trip(self):
        texture = self._make_texture()
        self.assertEqual(texture.tiling_mode(), "off")
        self.assertFalse(texture.is_tiled())
        texture.set_tiling_mode("udim")
        self.assertEqual(texture.tiling_mode(), "udim")
        self.assertTrue(texture.is_tiled())

    def test_set_tiling_mode_rejects_unknown(self):
        with self.assertRaises(ValueError):
            self._make_texture().set_tiling_mode("bogus")

    # ------------------------------------------------------------------
    # resolution
    # ------------------------------------------------------------------

    def test_resolved_paths_empty(self):
        self.assertEqual(self._make_texture().resolved_paths(), [])
        self.assertFalse(self._make_texture().file_exists())

    def test_resolved_paths_plain_file(self):
        path = self._touch("albedo.png")
        texture = self._make_texture()
        texture.set_file_path(path)
        resolved = texture.resolved_paths()
        self.assertEqual(len(resolved), 1)
        self.assertEqual(os.path.normcase(resolved[0]), os.path.normcase(os.path.normpath(path).replace("\\", "/")))
        self.assertTrue(texture.file_exists())

    def test_resolved_paths_missing_file(self):
        texture = self._make_texture()
        texture.set_file_path(os.path.join(self.directory, "missing.png"))
        self.assertEqual(len(texture.resolved_paths()), 1)
        self.assertFalse(texture.file_exists())

    def test_resolved_paths_expands_environment_variables(self):
        path = self._touch("env.png")
        os.environ["MREF_TEST_TEXTURE_DIR"] = self.directory
        try:
            texture = self._make_texture()
            texture.set_file_path("$MREF_TEST_TEXTURE_DIR/env.png")
            self.assertTrue(texture.file_exists())
            self.assertTrue(texture.resolved_paths()[0].endswith("env.png"))
        finally:
            del os.environ["MREF_TEST_TEXTURE_DIR"]

    def test_resolved_paths_udim(self):
        for tile in ["1001", "1002", "1011"]:
            self._touch(f"wood.{tile}.png")
        self._touch("other.1001.png")

        texture = self._make_texture()
        texture.set_tiling_mode("udim")
        texture.set_file_path(f"{self.directory}/wood.<UDIM>.png")

        resolved = texture.resolved_paths()
        self.assertEqual(
            [os.path.basename(path) for path in resolved],
            ["wood.1001.png", "wood.1002.png", "wood.1011.png"],
        )
        self.assertTrue(texture.file_exists())

    def test_udim_file_exists_false_without_tiles(self):
        texture = self._make_texture()
        texture.set_tiling_mode("udim")
        texture.set_file_path(f"{self.directory}/none.<UDIM>.png")
        self.assertEqual(texture.resolved_paths(), [])
        self.assertFalse(texture.file_exists())

    # ------------------------------------------------------------------
    # place2dTexture
    # ------------------------------------------------------------------

    def test_place2d_texture(self):
        place = self._make_texture().place2d_texture()
        self.assertIsNotNone(place)
        self.assertEqual(place.name(), "place")

    def test_place2d_texture_none(self):
        node = cmds.createNode("file", name="bare")
        self.assertIsNone(mref.get(node).place2d_texture())


if __name__ == "__main__":
    unittest.main()
