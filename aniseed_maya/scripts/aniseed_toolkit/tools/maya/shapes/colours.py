import aniseed_toolkit
from maya import cmds


class ApplyShapeColorPrompt(aniseed_toolkit.Tool):

    identifier = 'Apply Shape Color Prompt'
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(self) -> None:
        """
        This will prompt the user with a colour dialog and apply the given
        colour to the shapes of the selected nodes.
        """
        user_provided_color = self.ask_for_color()

        if not user_provided_color:
            return

        for node in cmds.ls(sl=True):
            aniseed_toolkit.scene.shapes.apply_color(
                node=node,
                r=user_provided_color[0],
                g=user_provided_color[1],
                b=user_provided_color[2],
            )

    @classmethod
    def ask_for_color(cls):
        cmds.colorEditor()
        if cmds.colorEditor(query=True, result=True):
            # -- The colour editor gives values between 0 and 1, while
            # -- apply_color takes them between 0 and 255
            return [
                channel * 255.0
                for channel in cmds.colorEditor(query=True, rgb=True)
            ]
        return None


class ApplyShapeColor(aniseed_toolkit.Tool):

    identifier = 'Apply Shape Color'
    classification = "Rigging"
    user_facing = False
    categories = [
        "Shapes",
    ]

    # --------------------------------------------------------------------------------------
    def run(self, node: str = "", r: float = 0, g: float = 0, b: float = 0) -> None:
        """
        This will apply the given rgb values to the shapes of the given node
        (or the selected nodes if none is given) and ensure that their colour
        overrides are set.

        Args:
            node: The node to apply the colour to
            r: The red channel value (between 0 and 255)
            g: The green channel value (between 0 and 255)
            b: The blue channel value (between 0 and 255)

        Returns:
            None
        """
        for node in [node] if node else cmds.ls(selection=True):
            aniseed_toolkit.scene.shapes.apply_color(
                node=node,
                r=r,
                g=g,
                b=b,
            )