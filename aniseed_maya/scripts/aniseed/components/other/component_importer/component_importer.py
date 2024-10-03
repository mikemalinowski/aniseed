import os
import aniseed


# --------------------------------------------------------------------------------------
class ComponentImporter(aniseed.RigComponent):
    """
    This allows you to specify a custom (hand made) rig part as a .ma file and
    import that.

    When importing, it will parent any root nodes under the given parent. Optionally
    you can specify a namespace which this will placed within. If you do not specify
    a namespace, then no namespace will be created.
    """

    identifier = "Custom : Import Rig Part"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(ComponentImporter, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Filepath",
            validate=True,
            value="",
        )

        self.declare_option(
            name="Namespace",
            value="",
            group="Import Settings",
        )

        self.declare_option(
            name="Reference",
            value=False,
            group="Import Settings",
        )

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name: str):
        if requirement_name == "Filepath":
            return aniseed.widgets.everywhere.FilepathSelector(
                default_value=self.option("Filepath").get(),
            )

    # ----------------------------------------------------------------------------------
    def is_valid(self):

        filepath = self.requirement("Filepath").get()

        if not os.path.exists(filepath):
            print(f"{filepath} does not exist")
            return False

        return True

    # ----------------------------------------------------------------------------------
    def run(self):
        pass
