import os
import json
import tempfile
import unittest
import xstack

COMPONENT_PATH = os.path.join(
    os.path.dirname(__file__),
)

class TestUnitStack(unittest.TestCase):
    counter = 0
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

        component_a.set_parent(
            parent=None,
            child_index=1
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

        component_a.set_parent(parent=component_b)

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

    def test_progression(self):
        self._reset_counter()

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        for i in range(1, 10):
            component = stack.add_component(
                label="",
                component_type="ComponentWithOption",
            )

        stack.build_progressed.connect(self._increment_counter)
        result = stack.build()

        self.assertEqual(
            self.counter,
            10,
        )

    def _reset_counter(self):
        counter = 0

    def _increment_counter(self, *args, **kwargs):
        self.counter += 1


# ------------------------------------------------------------------------------
class TestImportSubtree(unittest.TestCase):
    """
    Tests for Stack.import_subtree_under and Component.import_subtree —
    the save-subset-then-load-under-a-parent workflow.
    """

    def setUp(self):
        # -- A temp directory for any JSON files written by these tests.
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------

    def _make_stack(self):
        return xstack.Stack(component_paths=[COMPONENT_PATH])

    def _tmp_json(self, name="subtree.json"):
        return os.path.join(self.tmp_path, name)

    # --------------------------------------------------------------------------
    # Single-component export → import-under-parent
    # --------------------------------------------------------------------------

    def test_import_subtree_under_adds_loaded_component_as_child(self):
        # -- Set up source stack with one component to export
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        # -- Set up destination stack with a target parent
        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        # -- Import
        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        # -- Target should now have exactly one child with the source label
        self.assertEqual(len(target_parent.children), 1)
        self.assertEqual(target_parent.children[0].label(), "source_component")

    def test_import_subtree_regenerates_uuid(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )
        source_uuid = source_component.uuid()

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported = target_parent.children[0]
        self.assertNotEqual(
            imported.uuid(),
            source_uuid,
            "Imported component must get a fresh UUID, not the source's UUID.",
        )

    def test_import_subtree_preserves_option_values(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="ComponentWithOption",
        )
        source_component.option("test_option").set("custom_value")

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported = target_parent.children[0]
        self.assertEqual(
            imported.option("test_option").get(),
            "custom_value",
        )

    def test_import_subtree_preserves_input_values(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="ComponentWithExpectedRequirementSet",
        )
        source_component.input("expected_requirement").set(42)

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported = target_parent.children[0]
        self.assertEqual(
            imported.input("expected_requirement").get(),
            42,
        )

    def test_import_subtree_preserves_disabled_state(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )
        source_component.set_enabled(False)

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported = target_parent.children[0]
        self.assertFalse(imported.is_enabled())

    # --------------------------------------------------------------------------
    # Recursive subtree
    # --------------------------------------------------------------------------

    def test_import_subtree_preserves_child_hierarchy(self):
        # -- Build a 3-deep subtree on the source side
        source_stack = self._make_stack()
        root = source_stack.add_component(
            label="root",
            component_type="MinimalComponent",
        )
        child = source_stack.add_component(
            label="child",
            component_type="MinimalComponent",
            parent=root,
        )
        grandchild = source_stack.add_component(
            label="grandchild",
            component_type="MinimalComponent",
            parent=child,
        )

        filepath = self._tmp_json()
        root.save_settings(filepath)

        # -- Import into a fresh stack
        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported_root = target_parent.children[0]
        self.assertEqual(imported_root.label(), "root")
        self.assertEqual(len(imported_root.children), 1)

        imported_child = imported_root.children[0]
        self.assertEqual(imported_child.label(), "child")
        self.assertEqual(len(imported_child.children), 1)

        imported_grandchild = imported_child.children[0]
        self.assertEqual(imported_grandchild.label(), "grandchild")
        self.assertEqual(len(imported_grandchild.children), 0)

    def test_import_subtree_regenerates_uuids_through_full_depth(self):
        source_stack = self._make_stack()
        root = source_stack.add_component(
            label="root",
            component_type="MinimalComponent",
        )
        child = source_stack.add_component(
            label="child",
            component_type="MinimalComponent",
            parent=root,
        )

        source_uuids = {root.uuid(), child.uuid()}

        filepath = self._tmp_json()
        root.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )
        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported_uuids = {
            target_parent.children[0].uuid(),
            target_parent.children[0].children[0].uuid(),
        }

        self.assertEqual(
            len(source_uuids & imported_uuids),
            0,
            "No imported component should share a UUID with the source.",
        )

    # --------------------------------------------------------------------------
    # parent=None case
    # --------------------------------------------------------------------------

    def test_import_subtree_under_none_parent_adds_as_root_components(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        # -- Destination stack starts empty
        self.assertEqual(len(dest_stack.root_components), 0)

        dest_stack.import_subtree_under(parent=None, filepath=filepath)

        # -- The imported component should now be a root component
        self.assertEqual(len(dest_stack.root_components), 1)
        self.assertEqual(dest_stack.root_components[0].label(), "source_component")

    # --------------------------------------------------------------------------
    # Full-stack file shape (Stack.save output)
    # --------------------------------------------------------------------------

    def test_import_subtree_under_accepts_full_stack_file(self):
        # -- A stack-format file (with "tree" key) has multiple roots
        source_stack = self._make_stack()
        source_stack.add_component(label="root_a", component_type="MinimalComponent")
        source_stack.add_component(label="root_b", component_type="MinimalComponent")

        filepath = self._tmp_json()
        source_stack.save(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        # -- Both roots from the source file become children of the target
        child_labels = sorted(c.label() for c in target_parent.children)
        self.assertEqual(child_labels, ["root_a", "root_b"])

    # --------------------------------------------------------------------------
    # Error / edge cases
    # --------------------------------------------------------------------------

    def test_import_subtree_nonexistent_file_is_noop(self):
        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        # -- Should not raise; just no-op
        dest_stack.import_subtree_under(
            parent=target_parent,
            filepath=self._tmp_json("does_not_exist.json"),
        )

        self.assertEqual(len(target_parent.children), 0)

    def test_import_subtree_empty_filepath_is_noop(self):
        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath="")

        self.assertEqual(len(target_parent.children), 0)

    # --------------------------------------------------------------------------
    # Component.import_subtree (convenience wrapper)
    # --------------------------------------------------------------------------

    def test_component_import_subtree_adds_loaded_component_as_child(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        # -- Use the Component.import_subtree convenience wrapper
        target_parent.import_subtree(filepath)

        self.assertEqual(len(target_parent.children), 1)
        self.assertEqual(target_parent.children[0].label(), "source_component")

    # --------------------------------------------------------------------------
    # Round-trip
    # --------------------------------------------------------------------------

    def test_round_trip_preserves_options_inputs_and_hierarchy(self):
        source_stack = self._make_stack()
        root = source_stack.add_component(
            label="root",
            component_type="ComponentWithOption",
        )
        root.option("test_option").set("root_value")

        child = source_stack.add_component(
            label="child",
            component_type="ComponentWithOption",
            parent=root,
        )
        child.option("test_option").set("child_value")

        filepath = self._tmp_json()
        root.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )
        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported_root = target_parent.children[0]
        imported_child = imported_root.children[0]

        self.assertEqual(imported_root.option("test_option").get(), "root_value")
        self.assertEqual(imported_child.option("test_option").get(), "child_value")

    # --------------------------------------------------------------------------
    # Label collision warning
    # --------------------------------------------------------------------------

    def test_import_subtree_warns_on_label_collision(self):
        # -- Source component with a label
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="duplicate_label",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        # -- Destination already has a component with the same label
        dest_stack = self._make_stack()
        dest_stack.add_component(
            label="duplicate_label",
            component_type="MinimalComponent",
        )
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        # -- Capture stdout to verify a warning was printed.
        import io
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            dest_stack.import_subtree_under(
                parent=target_parent,
                filepath=filepath,
            )

        output = buffer.getvalue()
        self.assertIn("duplicate_label", output)
        self.assertIn("label collision", output.lower())

        # -- The import should still have happened despite the warning.
        self.assertEqual(len(target_parent.children), 1)

    # --------------------------------------------------------------------------
    # Subtree-load doesn't disturb existing components
    # --------------------------------------------------------------------------

    def test_import_subtree_does_not_modify_existing_components(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        existing_component = dest_stack.add_component(
            label="existing",
            component_type="MinimalComponent",
        )
        existing_uuid = existing_component.uuid()

        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        # -- existing_component should still be in the stack with the same UUID
        self.assertIn(existing_component, dest_stack.root_components)
        self.assertEqual(existing_component.uuid(), existing_uuid)


if __name__ == "__main__":
    unittest.main()