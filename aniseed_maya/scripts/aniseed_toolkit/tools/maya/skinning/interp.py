import aniseed_toolkit
from maya import cmds


class SkinInterpSetTargetAWeights(aniseed_toolkit.Tool):
    identifier = 'Interp : Set Target A Weights'
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self):
        aniseed_toolkit.skin.SkinLerper.set_target_a_weights(cmds.ls(selection=True)[0])


class SkinInterpSetTargetBWeights(aniseed_toolkit.Tool):
    identifier = 'Interp : Set Target B Weights'
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self):
        aniseed_toolkit.skin.SkinLerper.set_target_b_weights(cmds.ls(selection=True)[0])


class SkinInterpApply(aniseed_toolkit.Tool):
    identifier = 'Interp : Apply Interpolation'
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, interpolation_factor=0.5):
        aniseed_toolkit.skin.SkinLerper.set_destination_vertices(
            [
                n
                for n in cmds.ls(sl=True, flatten=True)
            ]
        )
        aniseed_toolkit.skin.SkinLerper.set_by_interpolation_factor(interpolation_factor)
