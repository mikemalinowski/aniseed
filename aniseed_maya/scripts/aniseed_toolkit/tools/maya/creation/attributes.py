import aniseed_toolkit
import maya.cmds as mc


class AddSeparator(aniseed_toolkit.Tool):

    identifier = 'Add Separator Attribute'
    classification = "Rigging"
    user_facing = False

    def run(self, node: str = "") -> None:
        """
        Adds an underscored attribute as an attribute separator

        Args:
            node: Node to add the separator to

        Return:
            None
        """
        if not node:
            node = mc.ls(sl=True)[0]

        character = "_"
        name_to_use = character * 8

        while mc.objExists(f"{node}.{name_to_use}"):
            name_to_use += character

        mc.addAttr(
            node,
            shortName=name_to_use,
            k=True,
        )
        mc.setAttr(f"{node}.{name_to_use}", lock=True)
