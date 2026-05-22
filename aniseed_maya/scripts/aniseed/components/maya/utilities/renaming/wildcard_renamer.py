import aniseed
import mref


class WildCardRenamer(aniseed.RigComponent):

    identifier = "Utility : Wildcard Renamer"

    def __init__(self, *args, **kwargs):
        aniseed.RigComponent.__init__(self, *args, **kwargs)

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
        if requirement_name == "Search Under":
            return aniseed.widgets.ObjectSelector()

    def run(self) -> bool:
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
