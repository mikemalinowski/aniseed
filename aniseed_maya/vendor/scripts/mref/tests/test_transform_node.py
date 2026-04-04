import mref
import unittest
import maya.standalone
from maya import cmds


class TestTransformNode(unittest.TestCase):

    five_up_matrix = [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 5, 0, 1]
    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            # Already initialized (or running inside Maya)
            pass
        cmds.file(newFile=True, force=True)

    def test_can_get_matrix(self):

        node = mref.create("transform")
        matrix = node.get_matrix()

        self.assertTrue(len(matrix), 15)

    def test_can_set_matrix(self):

        node = mref.create("transform")
        node.set_matrix(self.five_up_matrix)

        y = cmds.getAttr(f"{node.name()}.translateY")

        self.assertEqual(y, self.five_up_matrix[-3])