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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class RunExecutionBlock(aniseed.RigComponent):
    """
    This will instigate the run of a block during the execution of another
    block.
    """
    identifier = "Stack : Run Execution Block"

    def __init__(self, *args, **kwargs):
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
        if requirement_name == "Execution Block Label":
            return aniseed.widgets.ItemSelector(
                items=self.get_valid_execution_blocks(),
                default_item="",
            )

    def get_all_parent_labels(self):
        parents = []
        parent = self.parent

        while parent:
            parents.append(parent.label())
            parent = parent.parent

        return parents

    def get_valid_execution_blocks(self):

        execution_blocks = []
        parent_labels = self.get_all_parent_labels()

        for component in self.stack.components(of_type=ExecutionBlock.identifier):
            if component.label() not in parent_labels:
                execution_blocks.append(component.label())

        clean_list = sorted(list(set(execution_blocks)))
        clean_list.insert(0, "")
        return clean_list

    def is_valid(self):
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
        component_label = self.input("Execution Block Label").get()

        component = self.stack.get_component_by_label(
            label=component_label,
            of_type=ExecutionBlock.identifier,
        )

        if not component:
            return False

        # -- Propagate the nested build's success/failure up to the
        # -- outer build. Without this, a failed sub-build would be
        # -- silently masked as success at this layer.
        return self.stack.build(build_below=component)
