"""
Provides the "Utility : Wildcard Renamer" component, which finds every node
matching a wildcard search string (optionally only those under a given
node) and replaces a substring in their names.
"""
import aniseed
import mref


class WildCardRenamer(aniseed.RigComponent):
    """
    Finds every node matching the wildcard search string (optionally only
    those under a given node) and replaces part of their names.
    """

    identifier = "Utility : Wildcard Renamer"

    def __init__(self, *args, **kwargs):
        """
        Declares the Search Under, Search String, Replace This and With This
        inputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Search Under",
            value="",
        )

        self.declare_input(
            name="Search String",
            value="",
        )

        self.declare_input(
            name="Replace This",
            value="",
        )

        self.declare_input(
            name="With This",
            value="",
        )

    def input_widget(self, requirement_name: str) -> "PySide6.QWidget":
        """
        Returns an object selector for the Search Under input.
        """
        if requirement_name == "Search Under":
            return aniseed.widgets.ObjectSelector()

    def run(self) -> bool:
        """
        Renames every node matching the Search String (and whose full name
        contains Search Under, if given) by replacing Replace This with With
        This in its name.
        """
        search_string = self.input("Search String").get()
        replace_this = self.input("Replace This").get()
        with_this = self.input("With This").get()
        search_under = self.input("Search Under").get()

        for node in mref.ls(search_string):

            if search_under and search_under not in node.full_name():
                continue

            if replace_this in node.name():
                node.rename(node.name().replace(replace_this, with_this))

        return True
