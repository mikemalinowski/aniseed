import unittest

import maya.standalone
import mref
from maya import cmds


class TestExpression(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

        self.box = cmds.createNode("transform", name="box")
        self.driver = cmds.createNode("transform", name="driver")

    def _make_expression(self, string="box.tx = driver.ty * 2;", **kwargs):
        return mref.get(cmds.expression(string=string, name="expr", **kwargs))

    @staticmethod
    def _plug_names(attributes):
        return sorted(attribute.pointer().name() for attribute in attributes)

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_expression(self):
        self.assertIn("Expression", self._make_expression().assigned_traits())

    def test_does_not_bind_to_unrelated_node(self):
        self.assertNotIn("Expression", mref.get(self.box).assigned_traits())

    # ------------------------------------------------------------------
    # expression string
    # ------------------------------------------------------------------

    def test_expression_string(self):
        expression = self._make_expression()
        self.assertEqual(
            expression.expression_string(),
            "box.translateX = driver.translateY * 2;",
        )

    def test_set_expression_string_rebuilds_connections(self):
        expression = self._make_expression()
        expression.set_expression_string("box.tz = driver.sx;")
        self.assertIn("box.translateZ", expression.expression_string())
        self.assertEqual(self._plug_names(expression.output_attributes()), ["box.translateZ"])
        self.assertEqual(self._plug_names(expression.input_attributes()), ["driver.scaleX"])

    # ------------------------------------------------------------------
    # bound object
    # ------------------------------------------------------------------

    def test_bound_object_none(self):
        self.assertIsNone(self._make_expression().bound_object())

    def test_bound_object(self):
        expression = self._make_expression("tx = 1;", object=self.box)
        self.assertEqual(expression.bound_object().name(), "box")

    def test_set_bound_object(self):
        expression = self._make_expression("float $a = 1;")
        expression.set_bound_object(mref.get(self.driver))
        self.assertEqual(expression.bound_object().name(), "driver")

    # ------------------------------------------------------------------
    # animated
    # ------------------------------------------------------------------

    def test_animated(self):
        expression = self._make_expression()
        self.assertTrue(expression.is_animated())
        expression.set_animated(False)
        self.assertFalse(expression.is_animated())
        self.assertEqual(cmds.getAttr(f"{expression.name()}.animated"), 0)
        expression.set_animated(True)
        self.assertTrue(expression.is_animated())

    # ------------------------------------------------------------------
    # inputs / outputs
    # ------------------------------------------------------------------

    def test_input_attributes(self):
        expression = self._make_expression("box.tx = driver.ty + driver.tz;")
        inputs = expression.input_attributes()
        self.assertIsInstance(inputs, mref.ReferenceList)
        self.assertEqual(self._plug_names(inputs), ["driver.translateY", "driver.translateZ"])

    def test_output_attributes(self):
        expression = self._make_expression("box.tx = 1; box.ty = 2;")
        outputs = expression.output_attributes()
        self.assertIsInstance(outputs, mref.ReferenceList)
        self.assertEqual(self._plug_names(outputs), ["box.translateX", "box.translateY"])

    def test_attributes_look_through_unit_conversion(self):
        # -- Rotations are angular, so Maya inserts unitConversion nodes
        expression = self._make_expression("box.rx = driver.ry;")
        self.assertEqual(self._plug_names(expression.input_attributes()), ["driver.rotateY"])
        self.assertEqual(self._plug_names(expression.output_attributes()), ["box.rotateX"])

    def test_time_only_expression_has_no_input_attributes(self):
        expression = self._make_expression("box.tx = time;")
        self.assertEqual(len(expression.input_attributes()), 0)


if __name__ == "__main__":
    unittest.main()
