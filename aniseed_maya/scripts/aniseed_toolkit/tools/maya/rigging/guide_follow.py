import aniseed_toolkit


class CreateAimHierarchy(aniseed_toolkit.Tool):
    identifier = "Create Aim Hierarchy"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, joints: list[str], constrain: bool = True) -> list[str]:
        return aniseed_toolkit.rigging.aim_hierarchy.create_aim_hierarchy(
            joints=joints,
            constrain=constrain,
        )
