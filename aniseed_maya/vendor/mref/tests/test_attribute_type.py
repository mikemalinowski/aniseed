import unittest

import maya.standalone
import mref
from maya import cmds


class TestAttribute(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_attr(self, attribute_type="float", attr_name="myAttr", node_name="my_node"):
        node = mref.create("transform", name=node_name)
        node.add_attribute(name=attr_name, value=None, attribute_type=attribute_type)
        return node, node.attr(attr_name)

    # ------------------------------------------------------------------
    # name / full_name / path
    # ------------------------------------------------------------------

    def test_name_returns_partial_attribute_name(self):
        _, attr = self._make_attr()
        self.assertEqual(attr.name(), "myAttr")

    def test_name_with_node_returns_short_form(self):
        _, attr = self._make_attr()
        self.assertEqual(attr.name(include_node=True), "my_node.myAttr")

    def test_full_name_returns_dag_path(self):
        _, attr = self._make_attr()
        # Transform at scene root → |my_node.myAttr
        self.assertEqual(attr.full_name(), "|my_node.myAttr")

    def test_path_aliases_full_name(self):
        _, attr = self._make_attr()
        self.assertEqual(attr.path(), attr.full_name())

    # ------------------------------------------------------------------
    # get / set
    # ------------------------------------------------------------------

    def test_set_and_get_float(self):
        _, attr = self._make_attr(attribute_type="float")
        attr.set(5.5)
        self.assertAlmostEqual(attr.get(), 5.5, places=4)

    def test_set_and_get_string(self):
        _, attr = self._make_attr(attribute_type="string")
        attr.set("hello")
        self.assertEqual(attr.get(), "hello")

    # ------------------------------------------------------------------
    # get_type
    # ------------------------------------------------------------------

    def test_get_type_returns_attribute_type(self):
        _, attr = self._make_attr(attribute_type="float")
        self.assertEqual(attr.get_type(), "float")

    def test_get_type_is_cached(self):
        _, attr = self._make_attr(attribute_type="float")
        t1 = attr.get_type()
        t2 = attr.get_type()
        self.assertEqual(t1, t2)

    # ------------------------------------------------------------------
    # python_type
    # ------------------------------------------------------------------

    def test_python_type_float(self):
        _, attr = self._make_attr(attribute_type="float")
        self.assertEqual(attr.python_type(), float)

    def test_python_type_long_returns_int(self):
        # -- Regression guard: `long` was previously missing from the
        # -- python_type mapping and returned None.
        _, attr = self._make_attr(attribute_type="long")
        self.assertEqual(attr.python_type(), int)

    def test_python_type_bool(self):
        _, attr = self._make_attr(attribute_type="bool")
        self.assertEqual(attr.python_type(), bool)

    def test_python_type_string(self):
        _, attr = self._make_attr(attribute_type="string")
        self.assertEqual(attr.python_type(), str)

    def test_python_type_message_returns_none(self):
        _, attr = self._make_attr(attribute_type="message")
        self.assertIsNone(attr.python_type())

    # ------------------------------------------------------------------
    # connect / disconnect / connect_next
    # ------------------------------------------------------------------

    def test_connect_creates_input(self):
        node_a = mref.create("transform", name="src_node")
        node_a.add_attribute(name="src", value=None, attribute_type="float")
        node_b = mref.create("transform", name="dst_node")
        node_b.add_attribute(name="dst", value=None, attribute_type="float")

        node_a.attr("src").connect(node_b.attr("dst"))
        self.assertEqual(len(node_b.attr("dst").inputs()), 1)

    def test_disconnect_with_single_referenceditem_does_not_raise(self):
        # -- Regression guard for the TypeError-on-single-arg bug.
        node_a = mref.create("transform", name="src_node")
        node_a.add_attribute(name="src", value=None, attribute_type="float")
        node_b = mref.create("transform", name="dst_node")
        node_b.add_attribute(name="dst", value=None, attribute_type="float")

        attr_a = node_a.attr("src")
        attr_b = node_b.attr("dst")
        attr_a.connect(attr_b)

        attr_a.disconnect(attr_b)
        self.assertEqual(len(attr_b.inputs()), 0)

    def test_disconnect_all_drops_every_connection(self):
        node_a = mref.create("transform", name="src_node")
        node_a.add_attribute(name="src", value=None, attribute_type="float")
        node_b = mref.create("transform", name="dst_node")
        node_b.add_attribute(name="dst", value=None, attribute_type="float")

        attr_a = node_a.attr("src")
        attr_b = node_b.attr("dst")
        attr_a.connect(attr_b)
        attr_a.disconnect()

        self.assertEqual(len(attr_b.inputs()), 0)

    # ------------------------------------------------------------------
    # inputs / outputs with node_type filter
    # ------------------------------------------------------------------

    def test_inputs_node_type_filter_matches(self):
        # -- Regression guard: node_type was previously a no-op param.
        md = mref.create("multiplyDivide", name="md_node")
        target = mref.create("transform", name="target_node")
        md.outputX.connect(target.translateX)

        # Matching type returns the input
        inputs = target.translateX.inputs(node_type="multiplyDivide")
        self.assertEqual(len(inputs), 1)

    def test_inputs_node_type_filter_excludes(self):
        md = mref.create("multiplyDivide", name="md_node")
        target = mref.create("transform", name="target_node")
        md.outputX.connect(target.translateX)

        # Non-matching type returns nothing
        inputs = target.translateX.inputs(node_type="locator")
        self.assertEqual(len(inputs), 0)

    # ------------------------------------------------------------------
    # Binding
    # ------------------------------------------------------------------

    def test_binds_to_plug_only(self):
        node, attr = self._make_attr()
        self.assertIn("Attribute", attr.assigned_traits())
        self.assertNotIn("Attribute", node.assigned_traits())

    # ------------------------------------------------------------------
    # Definition queries
    # ------------------------------------------------------------------

    def test_is_dynamic(self):
        node, attr = self._make_attr()
        self.assertTrue(attr.is_dynamic())
        self.assertFalse(node.attr("translateX").is_dynamic())

    def test_default_value(self):
        node = mref.create("transform", name="n")
        self.assertEqual(node.attr("translateX").default_value(), 0.0)
        self.assertEqual(node.attr("scale").default_value(), [1.0, 1.0, 1.0])
        cmds.addAttr(node.full_name(), longName="myDefault", attributeType="float", defaultValue=2.5)
        self.assertAlmostEqual(node.attr("myDefault").default_value(), 2.5, places=4)

    def test_default_value_none_for_string(self):
        _, attr = self._make_attr(attribute_type="string")
        self.assertIsNone(attr.default_value())

    def test_min_max(self):
        _, attr = self._make_attr()
        self.assertIsNone(attr.minimum())
        self.assertIsNone(attr.maximum())

        attr.set_minimum(-1)
        attr.set_maximum(4)
        self.assertEqual(attr.minimum(), -1.0)
        self.assertEqual(attr.maximum(), 4.0)

        attr.set_minimum(None)
        attr.set_maximum(None)
        self.assertIsNone(attr.minimum())
        self.assertIsNone(attr.maximum())

    def test_min_on_static_attribute(self):
        node = mref.create("transform", name="n")
        self.assertIsNone(node.attr("translateX").minimum())
        with self.assertRaises(RuntimeError):
            node.attr("translateX").set_minimum(0)

    def test_enum_names(self):
        node = mref.create("transform", name="n")
        node.add_attribute(name="mode", value=None, attribute_type="enum", enumName="off:on:auto")
        attr = node.attr("mode")
        self.assertEqual(attr.enum_names(), ["off", "on", "auto"])

        attr.set_enum_names(["a", "b"])
        self.assertEqual(attr.enum_names(), ["a", "b"])

    def test_enum_names_sparse(self):
        node = mref.create("transform", name="n")
        node.add_attribute(name="mode", value=None, attribute_type="enum", enumName="a=0:b=5")
        self.assertEqual(node.attr("mode").enum_names(), ["a", "b"])

    def test_enum_names_none_for_non_enum(self):
        _, attr = self._make_attr()
        self.assertIsNone(attr.enum_names())

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def test_keyable(self):
        _, attr = self._make_attr()
        self.assertFalse(attr.is_keyable())
        attr.set_keyable(True)
        self.assertTrue(attr.is_keyable())
        self.assertTrue(attr.is_in_channel_box())

    def test_channel_box(self):
        _, attr = self._make_attr()
        self.assertFalse(attr.is_in_channel_box())
        attr.set_in_channel_box(True)
        self.assertTrue(attr.is_in_channel_box())
        self.assertFalse(attr.is_keyable())

    def test_lock_unlock(self):
        _, attr = self._make_attr()
        self.assertFalse(attr.is_locked())
        attr.lock()
        self.assertTrue(attr.is_locked())
        attr.unlock()
        self.assertFalse(attr.is_locked())

    def test_is_locked_matches_set_lock(self):
        _, attr = self._make_attr()
        attr.set(lock=True)
        self.assertTrue(attr.is_locked())

    def test_hidden(self):
        _, attr = self._make_attr()
        self.assertFalse(attr.is_hidden())
        attr.set_hidden(True)
        self.assertTrue(attr.is_hidden())

    def test_set_hidden_static_raises(self):
        node = mref.create("transform", name="n")
        with self.assertRaises(RuntimeError):
            node.attr("translateX").set_hidden(True)

    # ------------------------------------------------------------------
    # Naming
    # ------------------------------------------------------------------

    def test_nice_name(self):
        node, attr = self._make_attr()
        self.assertEqual(node.attr("translateX").nice_name(), "Translate X")
        attr.set_nice_name("Fancy")
        self.assertEqual(attr.nice_name(), "Fancy")

    def test_alias(self):
        _, attr = self._make_attr()
        self.assertIsNone(attr.alias())
        attr.set_alias("nickname")
        self.assertEqual(attr.alias(), "nickname")
        attr.set_alias(None)
        self.assertIsNone(attr.alias())

    def test_alias_on_array_element(self):
        node = mref.create("transform", name="n")
        cmds.addAttr(node.full_name(), longName="arr", attributeType="float", multi=True)
        element = node.attr("arr").element(2)
        element.set_alias("second")
        self.assertEqual(element.alias(), "second")
        self.assertEqual(node.attr("second").index(), 2)

    # ------------------------------------------------------------------
    # Structure
    # ------------------------------------------------------------------

    def test_compound_children_and_parent(self):
        node = mref.create("transform", name="n")
        translate = node.attr("translate")
        self.assertTrue(translate.is_compound())
        self.assertEqual(
            [child.name() for child in translate.children()],
            ["translateX", "translateY", "translateZ"],
        )
        self.assertEqual(node.attr("translateX").parent().name(), "translate")
        self.assertIsNone(translate.parent())
        self.assertEqual(len(node.attr("translateX").children()), 0)

    def test_array_elements(self):
        node = mref.create("transform", name="n")
        cmds.addAttr(node.full_name(), longName="arr", attributeType="float", multi=True)
        cmds.setAttr(f"{node.full_name()}.arr[0]", 1)
        cmds.setAttr(f"{node.full_name()}.arr[3]", 2)

        array = node.attr("arr")
        self.assertTrue(array.is_array())
        self.assertFalse(array.is_element())
        self.assertIsNone(array.index())
        self.assertEqual([e.index() for e in array.elements()], [0, 3])

        element = array.element(3)
        self.assertTrue(element.is_element())
        self.assertFalse(element.is_array())
        self.assertEqual(element.get(), 2.0)
        self.assertEqual(element.parent().name(), "arr")
        self.assertEqual(element.full_name(), "|n.arr[3]")

    def test_element_on_non_array_raises(self):
        _, attr = self._make_attr()
        self.assertEqual(len(attr.elements()), 0)
        with self.assertRaises(TypeError):
            attr.element(0)

    def test_nested_compound_array_child(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        constraint = mref.get(cmds.parentConstraint(driver, target)[0])
        targets = constraint.attr("target")
        self.assertEqual(len(targets.children()), 0)

        element = targets.element(0)
        weight = [c for c in element.children() if c.name().endswith("targetWeight")][0]
        self.assertEqual(weight.name(), "target[0].targetWeight")
        self.assertEqual(weight.parent().name(), "target[0]")
        self.assertAlmostEqual(weight.get(), 1.0, places=4)

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    def test_is_connected_and_source(self):
        md = mref.create("multiplyDivide", name="md_node")
        target = mref.create("transform", name="target_node")
        self.assertFalse(target.translateX.is_connected())
        self.assertIsNone(target.translateX.source())

        md.outputX.connect(target.translateX)
        self.assertTrue(target.translateX.is_connected())
        self.assertTrue(md.outputX.is_connected())
        self.assertEqual(target.translateX.source().name(include_node=True), "md_node.outputX")

    def test_source_skips_unit_conversion(self):
        a = mref.create("transform", name="a")
        b = mref.create("transform", name="b")
        a.translateX.connect(b.rotateX)
        self.assertEqual(b.rotateX.source().name(include_node=True), "a.translateX")
        self.assertEqual(
            b.rotateX.source(skip_converters=False).node().node_type(),
            "unitConversion",
        )

    # ------------------------------------------------------------------
    # delete
    # ------------------------------------------------------------------

    def test_delete_dynamic(self):
        node, attr = self._make_attr()
        attr.delete()
        self.assertFalse(node.has_attribute("myAttr"))

    def test_delete_static_raises(self):
        node = mref.create("transform", name="n")
        with self.assertRaises(RuntimeError):
            node.attr("translateX").delete()

    def test_delete_array_element(self):
        node = mref.create("transform", name="n")
        cmds.addAttr(node.full_name(), longName="arr", attributeType="float", multi=True)
        cmds.setAttr(f"{node.full_name()}.arr[0]", 1)
        cmds.setAttr(f"{node.full_name()}.arr[1]", 2)
        node.attr("arr").element(0).delete()
        self.assertEqual([e.index() for e in node.attr("arr").elements()], [1])


if __name__ == "__main__":
    unittest.main()