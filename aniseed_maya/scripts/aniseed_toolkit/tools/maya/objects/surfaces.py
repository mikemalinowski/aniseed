import aniseed_toolkit


class SerialiseNurbsSurface(aniseed_toolkit.Tool):

    identifier = "Serialise Nurbs Surface"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, surface, relative_to=None):
        return aniseed_toolkit.surfaces.serialise(surface, relative_to)


class ConstructNurbsSurface(aniseed_toolkit.Tool):

    identifier = "Construct Nurbs Surface"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, data, name="reconstructedSurface", parent_transform=None):
        return aniseed_toolkit.surfaces.construct(data, name, parent_transform)
