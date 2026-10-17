import unittest

import maya.standalone
import mref
from maya import cmds


class TestMatrixNode(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _translated(self, name, position):
        node = cmds.createNode("transform", name=name)
        cmds.setAttr(f"{node}.translate", *position)
        return node

    def _assertMatrixTranslation(self, matrix, expected):
        self.assertEqual(len(matrix), 16)
        for actual, value in zip(matrix[12:15], expected):
            self.assertAlmostEqual(actual, value, places=4)

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_builtin_matrix_nodes(self):
        for node_type in (
            "multMatrix", "addMatrix", "wtAddMatrix", "decomposeMatrix",
            "composeMatrix", "pickMatrix", "blendMatrix", "aimMatrix",
            "parentMatrix", "holdMatrix", "passMatrix", "fourByFourMatrix",
            "uvPin", "proximityPin",
        ):
            node = mref.get(cmds.createNode(node_type))
            self.assertIn("MatrixNode", node.assigned_traits(), node_type)

    def test_binds_to_plugin_matrix_nodes(self):
        try:
            cmds.loadPlugin("matrixNodes", quiet=True)
        except RuntimeError:
            self.skipTest("matrixNodes plugin unavailable")
        for node_type in ("inverseMatrix", "transposeMatrix"):
            node = mref.get(cmds.createNode(node_type))
            self.assertIn("MatrixNode", node.assigned_traits(), node_type)

    def test_does_not_bind_to_unrelated_nodes(self):
        for node_type in ("transform", "multiplyDivide", "plusMinusAverage"):
            node = mref.get(cmds.createNode(node_type))
            self.assertNotIn("MatrixNode", node.assigned_traits(), node_type)

    # ------------------------------------------------------------------
    # output_matrix / output_matrix_attribute
    # ------------------------------------------------------------------

    def test_output_matrix_of_mult_matrix(self):
        a = self._translated("a", (1, 2, 3))
        b = self._translated("b", (10, 0, 0))
        mult = mref.get(cmds.createNode("multMatrix"))
        mult.add_matrix_input(f"{a}.matrix")
        mult.add_matrix_input(f"{b}.matrix")
        self._assertMatrixTranslation(mult.output_matrix(), (11, 2, 3))

    def test_output_matrix_attribute_names(self):
        mult = mref.get(cmds.createNode("multMatrix"))
        self.assertEqual(mult.output_matrix_attribute().name(), "matrixSum")
        hold = mref.get(cmds.createNode("holdMatrix"))
        self.assertEqual(hold.output_matrix_attribute().name(), "outMatrix")
        four = mref.get(cmds.createNode("fourByFourMatrix"))
        self.assertEqual(four.output_matrix_attribute().name(), "output")

    def test_output_matrix_array_output(self):
        pin = mref.get(cmds.createNode("uvPin"))
        attribute = pin.output_matrix_attribute(2)
        self.assertTrue(attribute.full_name().endswith("outputMatrix[2]"))

    def test_decompose_has_no_output_matrix(self):
        decompose = mref.get(cmds.createNode("decomposeMatrix"))
        self.assertIsNone(decompose.output_matrix_attribute())
        self.assertIsNone(decompose.output_matrix())

    def test_compose_output_matrix(self):
        compose = cmds.createNode("composeMatrix")
        cmds.setAttr(f"{compose}.inputTranslate", 4, 5, 6)
        self._assertMatrixTranslation(mref.get(compose).output_matrix(), (4, 5, 6))

    # ------------------------------------------------------------------
    # input_matrix_attributes / matrix_sources / add_matrix_input
    # ------------------------------------------------------------------

    def test_input_matrix_attributes_order_blend(self):
        blend = mref.get(cmds.createNode("blendMatrix"))
        cmds.setAttr(f"{blend.full_name()}.target[0].weight", 1.0)
        cmds.setAttr(f"{blend.full_name()}.target[3].weight", 1.0)
        names = [attr.full_name().split(".", 1)[1] for attr in blend.input_matrix_attributes()]
        self.assertEqual(
            names,
            ["inputMatrix", "target[0].targetMatrix", "target[3].targetMatrix"],
        )

    def test_input_matrix_attributes_aim(self):
        aim = mref.get(cmds.createNode("aimMatrix"))
        names = [attr.name() for attr in aim.input_matrix_attributes()]
        self.assertEqual(
            names,
            ["inputMatrix", "primaryTargetMatrix", "secondaryTargetMatrix"],
        )

    def test_input_matrix_attributes_reference_list(self):
        mult = mref.get(cmds.createNode("multMatrix"))
        self.assertIsInstance(mult.input_matrix_attributes(), mref.ReferenceList)
        self.assertEqual(len(mult.input_matrix_attributes()), 0)

    def test_add_matrix_input_appends_to_array(self):
        a = cmds.createNode("transform", name="a")
        b = cmds.createNode("transform", name="b")
        mult = mref.get(cmds.createNode("multMatrix"))
        first = mult.add_matrix_input(a)
        second = mult.add_matrix_input(b)
        self.assertTrue(first.full_name().endswith("matrixIn[0]"))
        self.assertTrue(second.full_name().endswith("matrixIn[1]"))
        self.assertEqual(
            cmds.listConnections(second.full_name(), plugs=True)[0],
            "b.worldMatrix",
        )

    def test_add_matrix_input_fills_fixed_slot_first(self):
        a = cmds.createNode("transform", name="a")
        b = cmds.createNode("transform", name="b")
        blend = mref.get(cmds.createNode("blendMatrix"))
        self.assertEqual(blend.add_matrix_input(a).name(), "inputMatrix")
        self.assertTrue(
            blend.add_matrix_input(b).full_name().endswith("target[0].targetMatrix")
        )

    def test_add_matrix_input_static_value(self):
        mult = mref.get(cmds.createNode("multMatrix"))
        value = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 7, 8, 9, 1]
        attribute = mult.add_matrix_input(value)
        self._assertMatrixTranslation(cmds.getAttr(attribute.full_name()), (7, 8, 9))
        self._assertMatrixTranslation(mult.output_matrix(), (7, 8, 9))

    def test_add_matrix_input_wt_add_sets_weight(self):
        wt = mref.get(cmds.createNode("wtAddMatrix"))
        attribute = wt.add_matrix_input(self._translated("a", (2, 0, 0)))
        self.assertTrue(attribute.full_name().endswith("wtMatrix[0].matrixIn"))
        self.assertEqual(cmds.getAttr(f"{wt.full_name()}.wtMatrix[0].weightIn"), 1.0)
        self._assertMatrixTranslation(wt.output_matrix(), (2, 0, 0))

    def test_add_matrix_input_raises_when_full(self):
        hold = mref.get(cmds.createNode("holdMatrix"))
        hold.add_matrix_input(cmds.createNode("transform"))
        with self.assertRaises(RuntimeError):
            hold.add_matrix_input(cmds.createNode("transform"))

    def test_matrix_sources(self):
        a = cmds.createNode("transform", name="a")
        b = cmds.createNode("transform", name="b")
        mult = mref.get(cmds.createNode("multMatrix"))
        mult.add_matrix_input(f"{a}.matrix")
        mult.add_matrix_input([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        mult.add_matrix_input(b)
        sources = mult.matrix_sources()
        self.assertIsInstance(sources, mref.ReferenceList)
        self.assertEqual([s.node().name() for s in sources], ["a", "b"])

    # ------------------------------------------------------------------
    # output_translation / output_rotation / output_scale
    # ------------------------------------------------------------------

    def test_decompose_outputs(self):
        node = cmds.createNode("transform")
        cmds.setAttr(f"{node}.translate", 1, 2, 3)
        cmds.setAttr(f"{node}.rotate", 0, 45, 0)
        cmds.setAttr(f"{node}.scale", 2, 2, 2)
        decompose = mref.get(cmds.createNode("decomposeMatrix"))
        decompose.add_matrix_input(f"{node}.matrix")
        for actual, expected in zip(decompose.output_translation(), (1, 2, 3)):
            self.assertAlmostEqual(actual, expected, places=4)
        self.assertAlmostEqual(decompose.output_rotation()[1], 45.0, places=4)
        for actual in decompose.output_scale():
            self.assertAlmostEqual(actual, 2.0, places=4)

    def test_generic_outputs_decompose_matrix(self):
        compose = cmds.createNode("composeMatrix")
        cmds.setAttr(f"{compose}.inputTranslate", 5, 0, 0)
        cmds.setAttr(f"{compose}.inputRotate", 30, 0, 0)
        cmds.setAttr(f"{compose}.inputScale", 1, 3, 1)
        compose = mref.get(compose)
        self.assertAlmostEqual(compose.output_translation()[0], 5.0, places=4)
        self.assertAlmostEqual(compose.output_rotation()[0], 30.0, places=4)
        self.assertAlmostEqual(compose.output_scale()[1], 3.0, places=4)

    # ------------------------------------------------------------------
    # connect_output_to
    # ------------------------------------------------------------------

    def test_connect_output_to_offset_parent_matrix(self):
        driver = self._translated("driver", (3, 4, 5))
        target = cmds.createNode("transform", name="target")
        mult = mref.get(cmds.createNode("multMatrix"))
        mult.add_matrix_input(driver)
        result = mult.connect_output_to(target)
        self.assertEqual(result, mult)
        self.assertEqual(
            cmds.listConnections(f"{target}.offsetParentMatrix", plugs=True)[0],
            f"{mult.name()}.matrixSum",
        )
        for actual, expected in zip(cmds.xform(target, q=True, ws=True, t=True), (3, 4, 5)):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_connect_output_to_via_decompose(self):
        driver = self._translated("driver", (3, 4, 5))
        target = cmds.createNode("transform", name="target")
        mult = mref.get(cmds.createNode("multMatrix"))
        mult.add_matrix_input(driver)
        result = mult.connect_output_to(target, offset_parent_matrix=False)
        self.assertEqual(result.node_type(), "decomposeMatrix")
        self.assertIn("MatrixNode", result.assigned_traits())
        for actual, expected in zip(cmds.getAttr(f"{target}.translate")[0], (3, 4, 5)):
            self.assertAlmostEqual(actual, expected, places=4)
        self.assertTrue(cmds.isConnected(f"{target}.rotateOrder", f"{result.name()}.inputRotateOrder"))

    def test_connect_output_to_from_decompose(self):
        driver = self._translated("driver", (1, 1, 1))
        target = cmds.createNode("transform", name="target")
        decompose = mref.get(cmds.createNode("decomposeMatrix"))
        decompose.add_matrix_input(f"{driver}.matrix")
        result = decompose.connect_output_to(target)
        self.assertEqual(result, decompose)
        self.assertTrue(cmds.isConnected(f"{decompose.name()}.outputTranslate", f"{target}.translate"))
        self.assertTrue(cmds.isConnected(f"{decompose.name()}.outputScale", f"{target}.scale"))


if __name__ == "__main__":
    unittest.main()
