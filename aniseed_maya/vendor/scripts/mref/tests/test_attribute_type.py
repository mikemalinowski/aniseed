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


if __name__ == "__main__":
    unittest.main()