"""
This creates a generalised Spline Setup
"""
import aniseed_toolkit

# -- The builder lives in the rigging layer. The name is kept here so that
# -- anything which referenced it from this module still finds it.
SimpleSplineSetup = aniseed_toolkit.rigging.spline.SimpleSplineSetup


class SplineSetup(aniseed_toolkit.Tool):

    identifier = "Create Spline Setup"
    classification = "Rigging"
    categories = [
        "Rigging",
    ]

    def run(
        self,
        parent,
        joints,
        org_transform,
        control_transforms,
        constrain=True,
        lock_end_orientations=True,
    ):
        return aniseed_toolkit.rigging.spline.create_spline_setup(
            parent,
            joints,
            org_transform,
            control_transforms,
            constrain=constrain,
            lock_end_orientations=lock_end_orientations,
        )
