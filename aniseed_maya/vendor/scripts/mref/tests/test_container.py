import unittest

import maya.standalone
import mref
from maya import cmds


class TestContainer(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_container(self, name="asset", nodes=None, container_type="container"):
        kwargs = dict(name=name, type=container_type)
        if nodes:
            kwargs["addNode"] = nodes
        return mref.get(cmds.container(**kwargs))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_container(self):
        container = self._make_container()
        self.assertIn("Container", container.assigned_traits())

    def test_binds_to_dag_container(self):
        container = self._make_container(container_type="dagContainer")
        self.assertIn("Container", container.assigned_traits())
        self.assertIn("Transform", container.assigned_traits())

    def test_does_not_bind_to_unrelated_nodes(self):
        self.assertNotIn("Container", mref.get(cmds.createNode("transform")).assigned_traits())
        self.assertNotIn("Container", mref.get(cmds.animLayer("layer")).assigned_traits())

    # ------------------------------------------------------------------
    # membership
    # ------------------------------------------------------------------

    def test_member_nodes(self):
        a = cmds.createNode("multiplyDivide", name="a")
        b = cmds.createNode("plusMinusAverage", name="b")
        container = self._make_container(nodes=[a, b])
        members = container.member_nodes()
        self.assertIsInstance(members, mref.ReferenceList)
        self.assertEqual(sorted(members.names()), ["a", "b"])

    def test_add_member_nodes(self):
        container = self._make_container()
        a = mref.get(cmds.createNode("multiplyDivide", name="a"))
        b = cmds.createNode("plusMinusAverage", name="b")

        container.add_member_nodes(a)
        container.add_member_nodes([b])
        self.assertEqual(sorted(container.member_nodes().names()), ["a", "b"])

    def test_add_member_nodes_include_network(self):
        container = self._make_container()
        a = cmds.createNode("multiplyDivide", name="a")
        b = cmds.createNode("plusMinusAverage", name="b")
        cmds.connectAttr(f"{a}.outputX", f"{b}.input1D[0]")

        container.add_member_nodes(a, include_network=True)
        self.assertIn("b", container.member_nodes().names())

    def test_remove_member_nodes(self):
        a = cmds.createNode("multiplyDivide", name="a")
        b = cmds.createNode("plusMinusAverage", name="b")
        container = self._make_container(nodes=[a, b])

        container.remove_member_nodes(mref.get(a))
        self.assertEqual(container.member_nodes().names(), ["b"])
        self.assertTrue(cmds.objExists(a))

    def test_is_member_node(self):
        a = cmds.createNode("multiplyDivide", name="a")
        b = cmds.createNode("plusMinusAverage", name="b")
        container = self._make_container(nodes=[a])
        self.assertTrue(container.is_member_node(a))
        self.assertTrue(container.is_member_node(mref.get(a)))
        self.assertFalse(container.is_member_node(b))

    # ------------------------------------------------------------------
    # publishing
    # ------------------------------------------------------------------

    def test_publish_attribute_and_published_attributes(self):
        a = cmds.createNode("multiplyDivide", name="a")
        container = self._make_container(nodes=[a])

        container.publish_attribute(f"{a}.input1X", "gain")
        container.publish_attribute(mref.get(f"{a}.input2Y"))

        published = container.published_attributes()
        self.assertEqual(sorted(published.keys()), ["gain", "input2Y"])
        self.assertEqual(published["gain"].name(include_node=True), "a.input1X")

    def test_unpublish_attribute(self):
        a = cmds.createNode("multiplyDivide", name="a")
        container = self._make_container(nodes=[a])
        container.publish_attribute(f"{a}.input1X", "gain")
        container.publish_attribute(f"{a}.input1Y", "bias")

        container.unpublish_attribute("gain")
        self.assertEqual(list(container.published_attributes().keys()), ["bias"])

    def test_published_attributes_empty(self):
        self.assertEqual(self._make_container().published_attributes(), {})

    # ------------------------------------------------------------------
    # hierarchy
    # ------------------------------------------------------------------

    def test_parent_and_child_containers(self):
        child = self._make_container("child")
        parent = self._make_container("parent")
        parent.add_member_nodes(child)

        self.assertIsNone(parent.parent_container())
        self.assertEqual(child.parent_container(), parent)

        children = parent.child_containers()
        self.assertIsInstance(children, mref.ReferenceList)
        self.assertEqual(children.names(), ["child"])
        self.assertEqual(len(child.child_containers()), 0)


if __name__ == "__main__":
    unittest.main()
