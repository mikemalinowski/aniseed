"""
Provides the "Custom : Import Rig Part" component, intended to import a hand
made rig part from a Maya file into an optional namespace. The import itself
is not implemented yet, so the component currently only validates that the
file exists.
"""
import os
import aniseed


class ComponentImporter(aniseed.RigComponent):
    """
    This allows you to specify a custom (hand made) rig part as a .ma file and
    import that.

    When importing, it will parent any root nodes under the given parent. Optionally
    you can specify a namespace which this will placed within. If you do not specify
    a namespace, then no namespace will be created.
    """

    identifier = "Custom : Import Rig Part"

    def __init__(self, *args, **kwargs):
        """
        Declares the "Filepath" input and the "Namespace" and "Reference"
        import options.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
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

    def input_widget(self, requirement_name: str):
        """
        Returns a file path selector for the "Filepath" input, seeded with its
        current value.

        Args:
            requirement_name: The name of the input to return a widget for.
        """
        if requirement_name == "Filepath":
            return aniseed.widgets.FilepathSelector(
                default_value=self.input("Filepath").get(),
            )

    def is_valid(self):
        """
        Checks that the given file path exists.
        """

        filepath = self.input("Filepath").get()

        if not os.path.exists(filepath):
            print(f"{filepath} does not exist")
            return False

        return True

    def run(self):
        """
        Does nothing yet, as the import itself has not been implemented.
        """
        # -- The import itself has not been implemented yet
        pass
