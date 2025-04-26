import aniseed
import aniseed_toolkit
import maya.cmds as mc


class BasicTransform(aniseed_toolkit.Tool):

    identifier = "Create Basic Transform"
    classification = "Rigging"
    user_facing = False

    def run(
            self,
            classification: str,
            description: str,
            location: str,
            config: aniseed.RigConfiguration,
            parent=None,
            match_to=None,
    ) -> str:
        """
        This will create a basic transform node but will name it using the aniseed
        config, and optionally set the parenting and transforms.

        Args:
            classification: The classification part of the name to apply
            description: The description part of the name to apply
            location: The location part of the name to apply
            config: The aniseed configuration instance
            parent: Optionally provide a parent, and this node will be made
                a child of it on creation.
            match_to: Optionally provide a node to match transform to on creation

        Returns:
            The name of the created node
        """
        # -- Create our component org to keep everything together
        node = mc.rename(
            mc.createNode("transform"),
            config.generate_name(
                classification=classification,
                description=description,
                location=location,
            ),
        )

        if parent:
            mc.parent(
                node,
                parent,
            )

        if match_to:
            if isinstance(match_to, str):
                mc.xform(
                    node,
                    matrix=mc.xform(
                        match_to,
                        query=True,
                        matrix=True,
                        worldSpace=True,
                    ),
                    worldSpace=True,
                )

            elif isinstance(match_to, (list, tuple)):
                mc.xform(
                    node,
                    matrix=match_to,
                    worldSpace=True,
                )

        return node
