"""
Provides the "Stack : Execution Block" component, which defines a block of
components the Aniseed App exposes as a build button, and the
"Stack : Run Execution Block" component, which builds another execution block
from within the current build. Blocks that are ancestors of the runner are
excluded from selection to avoid the most obvious recursion case.
"""
import os
import aniseed


class ExecutionBlock(aniseed.RigComponent):
    """
    The execution block does nothing other than define a block which is usually
    executed. The Aniseed App looks for components of this type and will expose
    the component as a button - making it easier for a user to trigger the building
    of blocks without having to hard code specific concepts into the tool.
    """

    identifier = "Stack : Execution Block"
    icon = os.path.join(
        os.path.dirname(__file__),
        "execution_block.png",
    )


class RunExecutionBlock(aniseed.RigComponent):
    """
    This will instigate the run of a block during the execution of another
    block.
    """
    identifier = "Stack : Run Execution Block"

    def __init__(self, *args, **kwargs):
        """
        Declares the "Execution Block Label" input, which names the Execution
        Block whose components should be built when this component runs.
        """
        super().__init__(*args, **kwargs)
        self.declare_input(
            name="Execution Block Label",
            description=(
                "The label of the Execution Block to run. Only blocks "
                "that are not ancestors of this component are listed, "
                "to avoid the most obvious recursion case."
            ),
            value="",
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an item selector for the "Execution Block Label" input, listing
        the execution blocks that are valid to run from this component.

        Args:
            requirement_name: The name of the input to return a widget for.

        Returns:
            The widget for the input, or None if the input has no custom widget.
        """
        if requirement_name == "Execution Block Label":
            return aniseed.widgets.ItemSelector(
                items=self.get_valid_execution_blocks(),
                default_item="",
            )

    def get_all_parent_labels(self):
        """
        Walks up the component hierarchy and collects the label of every
        ancestor of this component.

        Returns:
            List of ancestor labels, starting with the immediate parent.
        """
        parents = []
        parent = self.parent

        while parent:
            parents.append(parent.label())
            parent = parent.parent

        return parents

    def get_valid_execution_blocks(self):
        """
        Gathers the labels of all Execution Block components in the stack,
        excluding any that are ancestors of this component to avoid the most
        obvious recursion case.

        Returns:
            Sorted, de-duplicated list of labels with an empty string inserted at
            the front so that no block is selected by default.
        """

        execution_blocks = []
        parent_labels = self.get_all_parent_labels()

        for component in self.stack.components(of_type=ExecutionBlock.identifier):
            if component.label() not in parent_labels:
                execution_blocks.append(component.label())

        clean_list = sorted(set(execution_blocks))
        clean_list.insert(0, "")
        return clean_list

    def is_valid(self):
        """
        Checks that an execution block label has been chosen and that an
        Execution Block with that label exists in the stack. The reason for
        failure is printed.
        """
        component_label = self.input("Execution Block Label").get()

        if not component_label:
            print("No Component Label Selected")
            return False

        component = self.stack.get_component_by_label(
            label=component_label,
            of_type=ExecutionBlock.identifier,
        )

        if not component:
            print(f"{component_label} could not be found.")
            return False

        return True

    def run(self):
        """
        Builds the stack below the chosen Execution Block. The result of that
        nested build is returned, but the stack ignores the return value of run,
        so a failed nested build does not fail the outer build.
        """
        component_label = self.input("Execution Block Label").get()

        component = self.stack.get_component_by_label(
            label=component_label,
            of_type=ExecutionBlock.identifier,
        )

        if not component:
            return False

        # -- Note that the stack ignores the value returned from run, so a
        # -- failed nested build does not fail the outer build
        return self.stack.build(build_below=component)
