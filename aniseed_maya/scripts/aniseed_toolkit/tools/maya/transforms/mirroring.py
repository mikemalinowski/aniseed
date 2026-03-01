import aniseed_toolkit
import maya.cmds as mc


class GlobalMirrorTool(aniseed_toolkit.Tool):

    identifier = "Global Mirror"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(
        self,
        transforms: list[str] or str = None,
        across: str = "YZ",
        behaviour: bool = True,
        name_replacement: dict = None,
    ):
        """
        This function is taken from github with a minor modification. The
        author and credit goes to Andreas Ranman.

        Github Url:
            https://gist.github.com/rondreas/1c6d4e5fc6535649780d5b65fc5a9283

        Mirrors transform across hyperplane.

        Args:
            transforms: list of Transform or string.
            across: plane which to mirror across (XY, YX or XZ).
            behaviour: If true, it should mirror the rotational behaviour too
            name_replacement : a tuple of length two, where the first part should
                be replaced with the second part
        """
        return aniseed_toolkit.mirror.global_mirror(
            transforms=transforms or mc.ls(selection=True),
            across=across,
            behaviour=behaviour,
            name_replacement=name_replacement,
        )


class InvertTranslationTool(aniseed_toolkit.Tool):

    identifier = "Invert Translation"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(self, transforms: list[str] = None) -> None:
        """
        This will invert the translation channels of a node

        Args:
            transforms: List of transforms to invert the translation of

        Returns:
            None
        """
        return aniseed_toolkit.mirror.invert_translation(
            transforms=transforms or mc.ls(selection=True),
        )
