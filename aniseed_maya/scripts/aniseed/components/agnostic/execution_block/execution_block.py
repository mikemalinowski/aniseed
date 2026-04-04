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
        super(ExecutionBlock, self).__init__(*args, **kwargs)
        self.declare_option(
            name="Icon",
            value="",
        )

    def is_valid(self):
        return True

    def run(self):
        return True
