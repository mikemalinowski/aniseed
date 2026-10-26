import unittest

import maya.standalone
import mref
from maya import cmds


class TestAnnotation(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_annotation(self):
        locator = cmds.spaceLocator(name="pointAt")[0]
        cmds.setAttr(f"{locator}.translate", 1, 2, 3)
        annotation = cmds.annotate(locator, text="hello", point=(5, 5, 5))
        return mref.get(annotation), locator

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_annotation(self):
        annotation, _ = self._make_annotation()
        self.assertIn("Annotation", annotation.assigned_traits())
        self.assertIn("Shape", annotation.assigned_traits())

    def test_does_not_bind_to_unrelated_nodes(self):
        _, locator = self._make_annotation()
        self.assertNotIn("Annotation", mref.get(locator).assigned_traits())
        shape = cmds.listRelatives(locator, shapes=True, fullPath=True)[0]
        self.assertNotIn("Annotation", mref.get(shape).assigned_traits())

    # ------------------------------------------------------------------
    # text
    # ------------------------------------------------------------------

    def test_text(self):
        annotation, _ = self._make_annotation()
        self.assertEqual(annotation.text(), "hello")

    def test_set_text(self):
        annotation, _ = self._make_annotation()
        annotation.set_text("world")
        self.assertEqual(annotation.text(), "world")

    def test_text_empty_on_new_node(self):
        annotation = mref.get(cmds.createNode("annotationShape"))
        self.assertEqual(annotation.text(), "")

    # ------------------------------------------------------------------
    # target
    # ------------------------------------------------------------------

    def test_target(self):
        annotation, locator = self._make_annotation()
        target = annotation.target()
        self.assertIsNotNone(target)
        self.assertEqual(target.parent().name(), locator)

    def test_target_none(self):
        annotation = mref.get(cmds.createNode("annotationShape"))
        self.assertIsNone(annotation.target())
        self.assertIsNone(annotation.target_position())

    def test_set_target(self):
        annotation, _ = self._make_annotation()
        other = cmds.createNode("transform", name="other")
        annotation.set_target(other)
        self.assertEqual(annotation.target().name(), "other")

    def test_set_target_none_disconnects(self):
        annotation, _ = self._make_annotation()
        annotation.set_target(None)
        self.assertIsNone(annotation.target())

    def test_target_position(self):
        annotation, _ = self._make_annotation()
        for actual, expected in zip(annotation.target_position(), (1, 2, 3)):
            self.assertAlmostEqual(actual, expected, places=4)

    # ------------------------------------------------------------------
    # display_arrow
    # ------------------------------------------------------------------

    def test_display_arrow_round_trip(self):
        annotation, _ = self._make_annotation()
        self.assertTrue(annotation.display_arrow())
        annotation.set_display_arrow(False)
        self.assertFalse(annotation.display_arrow())
        annotation.set_display_arrow(True)
        self.assertTrue(annotation.display_arrow())


if __name__ == "__main__":
    unittest.main()
