import aniseed_toolkit

# -- The builder lives in the rigging layer. The name is kept here so that
# -- anything which referenced it from this module still finds it.
Ribbon = aniseed_toolkit.rigging.ribbon.Ribbon


class RibbonTool(aniseed_toolkit.Tool):

    identifier = "Create Ribbon Setup2"
    classification = "Rigging"
    categories = [
        "Rigging",
    ]

    def run(
        self,
        start_joint,
        end_joint,
        transform_matrices,
        parent=None,
        ribbon=None,
        skin_data=None,
    ):
        return aniseed_toolkit.rigging.ribbon.create_ribbon(
            start_joint=start_joint,
            end_joint=end_joint,
            transform_matrices=transform_matrices,
            parent=parent,
            ribbon=ribbon,
            skin_data=skin_data,
        )
