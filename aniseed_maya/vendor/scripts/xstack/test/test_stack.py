import os
import unittest
import xstack

COMPONENT_PATH = os.path.join(
    os.path.dirname(__file__),
)

class TestUnitStack(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_can_instance_stack(self):

        stack = xstack.Stack()

        self.assertIsNotNone(stack)

    def test_can_find_components(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        self.assertGreater(
            len(stack.component_library.plugins()),
            0,
        )

    def test_can_add_component(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="test",
            component_type="MinimalComponent",
        )

        self.assertIsNotNone(component)

        self.assertIn(
            component,
            stack.components(),
        )

    def test_can_remove_component(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="test",
            component_type="MinimalComponent",
        )

        stack.remove_component(component)

        self.assertNotIn(
            component,
            stack.components(),
        )

    def test_can_build_stack(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        test_component = stack.component_library.request("RunTestComponent")
        test_component.RUN_ORDER = []

        component = stack.add_component(
            label="test",
            component_type="RunTestComponent",
        )

        stack.build()

        self.assertGreater(
            len(test_component.RUN_ORDER),
            0,
        )

    def test_basic_build_order_stack(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        test_component = stack.component_library.request("RunTestComponent")
        test_component.RUN_ORDER = []

        component_a = stack.add_component(
            label="test",
            component_type="RunTestComponent",
        )

        component_b = stack.add_component(
            label="test",
            component_type="RunTestComponent",
        )

        stack.build()

        self.assertEqual(
            component_a,
            test_component.RUN_ORDER[0],
        )

        self.assertEqual(
            component_b,
            test_component.RUN_ORDER[1],
        )

    def test_adjust_build_order_stack(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        test_component = stack.component_library.request("RunTestComponent")
        test_component.RUN_ORDER = []

        component_a = stack.add_component(
            label="test a",
            component_type="RunTestComponent",
        )

        component_b = stack.add_component(
            label="test b",
            component_type="RunTestComponent",
        )

        stack.set_build_position(
            component_a,
            parent=None,
            index=1
        )

        stack.build()

        self.assertEqual(
            component_b,
            test_component.RUN_ORDER[0],
        )

        self.assertEqual(
            component_a,
            test_component.RUN_ORDER[1],
        )

    def test_adjust_build_parent_stack(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        test_component = stack.component_library.request("RunTestComponent")
        test_component.RUN_ORDER = []

        component_a = stack.add_component(
            label="test a",
            component_type="RunTestComponent",
        )

        component_b = stack.add_component(
            label="test b",
            component_type="RunTestComponent",
        )

        stack.set_build_position(
            component_a,
            parent=component_b,
        )

        stack.build()

        self.assertEqual(
            component_b,
            test_component.RUN_ORDER[0],
        )

        self.assertEqual(
            component_a,
            test_component.RUN_ORDER[1],
        )

    def test_invalid_component(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        stack.add_component(label="", component_type="InvalidComponent")

        result = stack.build()

        self.assertFalse(result)

    def test_invalid_requirement(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        stack.add_component(label="", component_type="ComponentWithExpectedRequirementNotSet")

        result = stack.build()

        self.assertFalse(result)

    def test_valid_input(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(label="", component_type="ComponentWithExpectedRequirementNotSet")

        component.input("expected_requirement").set(True)

        result = stack.build()

        self.assertTrue(result)

    def test_not_executed_status(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="MinimalComponent",
        )

        self.assertEqual(
            component.status(),
            xstack.constants.Status.NotExecuted,
        )

    def test_executed_successfully_status(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="MinimalComponent",
        )
        stack.build()

        self.assertEqual(
            component.status(),
            xstack.constants.Status.Success,
        )

    def test_execution_failed_status(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="FailingComponent",
        )
        stack.build()

        self.assertEqual(
            component.status(),
            xstack.constants.Status.Failed,
        )

    def test_invalid_status(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="ComponentWithExpectedRequirementNotSet",
        )
        stack.build()

        self.assertEqual(
            component.status(),
            xstack.constants.Status.Invalid,
        )

    def test_option_setting(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="ComponentWithOption",
        )

        component.option("test_option").set("bar")

        result = stack.build()

        self.assertTrue(
            result
        )