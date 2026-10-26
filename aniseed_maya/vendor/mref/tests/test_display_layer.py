import unittest

import maya.standalone
import mref
from maya import cmds


class TestDisplayLayer(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_layer(self, name="layerA"):
        return mref.get(cmds.createDisplayLayer(empty=True, name=name))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_display_layer(self):
        layer = self._make_layer()
        self.assertIn("DisplayLayer", layer.assigned_traits())
        self.assertNotIn("ObjectSet", layer.assigned_traits())

    def test_does_not_bind_to_set(self):
        object_set = cmds.sets(empty=True, name="plainSet")
        self.assertNotIn("DisplayLayer", mref.get(object_set).assigned_traits())

    # ------------------------------------------------------------------
    # membership
    # ------------------------------------------------------------------

    def test_members_empty(self):
        members = self._make_layer().members()
        self.assertIsInstance(members, mref.ReferenceList)
        self.assertEqual(members, [])

    def test_add_members(self):
        cube = cmds.polyCube(name="cube")[0]
        sphere = cmds.polySphere(name="sphere")[0]
        layer = self._make_layer()
        layer.add_members(mref.get(cube))
        layer.add_members([sphere])
        self.assertEqual(sorted(layer.members().names()), ["cube", "sphere"])

    def test_add_members_moves_between_layers(self):
        cube = cmds.polyCube(name="cube")[0]
        layer_a = self._make_layer("layerA")
        layer_b = self._make_layer("layerB")
        layer_a.add_members(cube)
        layer_b.add_members(cube)
        self.assertEqual(layer_a.members(), [])
        self.assertEqual(layer_b.members().names(), ["cube"])

    def test_remove_members(self):
        cube = cmds.polyCube(name="cube")[0]
        sphere = cmds.polySphere(name="sphere")[0]
        layer = self._make_layer()
        layer.add_members([cube, sphere])
        layer.remove_members(mref.get(cube))
        self.assertEqual(layer.members().names(), ["sphere"])

    def test_remove_members_ignores_other_layers(self):
        cube = cmds.polyCube(name="cube")[0]
        layer_a = self._make_layer("layerA")
        layer_b = self._make_layer("layerB")
        layer_b.add_members(cube)
        layer_a.remove_members(cube)
        self.assertEqual(layer_b.members().names(), ["cube"])

    # ------------------------------------------------------------------
    # display state
    # ------------------------------------------------------------------

    def test_visibility_round_trip(self):
        layer = self._make_layer()
        self.assertTrue(layer.is_visible())
        layer.set_visible(False)
        self.assertFalse(layer.is_visible())

    def test_display_type_round_trip(self):
        layer = self._make_layer()
        self.assertEqual(layer.display_type(), "normal")
        layer.set_display_type("template")
        self.assertEqual(layer.display_type(), "template")
        layer.set_display_type("reference")
        self.assertEqual(layer.display_type(), "reference")

    def test_set_display_type_rejects_unknown(self):
        with self.assertRaises(ValueError):
            self._make_layer().set_display_type("bogus")

    def test_hide_on_playback_round_trip(self):
        layer = self._make_layer()
        self.assertFalse(layer.hide_on_playback())
        layer.set_hide_on_playback(True)
        self.assertTrue(layer.hide_on_playback())

    def test_colour_index_round_trip(self):
        layer = self._make_layer()
        self.assertEqual(layer.colour_index(), 0)
        layer.set_colour_index(13)
        self.assertEqual(layer.colour_index(), 13)


if __name__ == "__main__":
    unittest.main()
