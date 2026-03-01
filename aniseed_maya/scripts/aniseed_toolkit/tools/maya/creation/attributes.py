import aniseed_toolkit


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
        aniseed_toolkit.attributes.add_separator(node)
