import aniseed_toolkit
import maya.cmds as mc


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

        for node in mc.ls(sl=True):
            aniseed_toolkit.run(
                "Apply Shape Color",
                node=node,
                r=user_provided_color[0],
                g=user_provided_color[1],
                b=user_provided_color[2],
            )

    @classmethod
    def ask_for_color(cls):
        mc.colorEditor()
        if mc.colorEditor(query=True, result=True):
            return mc.colorEditor(query=True, rgb=True)
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
        This will apply the given rgb values to the shapes of the selected nodes
        and ensure that their colour overrides are set.

        Args:
            node: The node to apply the colour to
            r: The red channel value (between zero and one)
            g: The green channel value (between zero and one)
            b: The blue channel value (between zero and one)

        Returns:
            None
        """
        rgb = [r, g, b]
        all_shapes = list()

        if mc.nodeType(node) == "transform" or mc.nodeType(node) == "joint":
            all_shapes.extend(
                mc.listRelatives(
                    node,
                    shapes=True,
                )
            )

        elif mc.nodeType(node) == "nurbsCurve":
            all_shapes.append(node)

        for shape in all_shapes:

            mc.setAttr(f"{shape}.overrideEnabled", True)
            mc.setAttr(f"{shape}.overrideRGBColors", True)
            mc.setAttr(f"{shape}.useOutlinerColor", True)

            for idx, channel in enumerate(["R", "G", "B"]):
                mc.setAttr(f"{shape}.overrideColor{channel}", rgb[idx])# / 255.0)
                mc.setAttr(f"{shape}.outlinerColor{channel}", rgb[idx])# / 255.0)
