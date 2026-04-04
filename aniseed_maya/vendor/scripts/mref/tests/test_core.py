import mref
import unittest
import maya.standalone
from maya import cmds


class TestCore(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            # Already initialized (or running inside Maya)
            pass
        cmds.file(newFile=True, force=True)

    def test_can_create_node(self):
        node = mref.create("transform")

        self.assertIsInstance(
            node,
            mref.ReferencedItem,
        )

    def test_can_create_with_parenting(self):
        node_a = mref.create("transform")
        node_b = mref.create("transform", parent=node_a.name())

        self.assertIn(
            node_a.name(),
            node_b.full_name()
        )

    def test_can_create_with_name(self):
        node = mref.create("transform", name="foobar")
        self.assertEqual(
            node.name(),
            "foobar",
        )

    def test_can_get(self):
        node_name = cmds.createNode("transform", name="foobar")
        node = mref.get(node_name)

        self.assertIsNotNone(node)
        self.assertEqual(node.name() ,"foobar")

    def test_can_find(self):
        node_name = cmds.createNode("transform", name="foobar")
        nodes = mref.find("foo*")

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name(), "foobar")

    def test_can_interact_with_selection(self):
        node = mref.create("transform")
        mref.select(node)
        selection = mref.selected()

        self.assertEqual(len(selection), 1)
        self.assertEqual(selection[0], node)

    def test_item_equality(self):
        created_node = mref.create("transform", name="foobar")
        found_node = mref.get("foobar")

        self.assertEqual(created_node, found_node)