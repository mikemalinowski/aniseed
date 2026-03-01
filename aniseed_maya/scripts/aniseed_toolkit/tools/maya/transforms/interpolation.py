import aniseed_toolkit


class InterpolateVector(aniseed_toolkit.Tool):

    identifier = "Interpolate Vectors"
    categories = [
        "Transforms",
    ]
    user_facing = False

    def run(
        self,
        vector_a: list[float],
        vector_b: list[float],
        factor: float,
    ):
        return aniseed_toolkit.transformation.interpolate_vector(
            vector_a, vector_b, factor
        )
