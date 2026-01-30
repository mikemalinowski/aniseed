import maya
import aniseed_toolkit
from maya import cmds


class SkinLerper:

    target_a_weights = []
    target_b_weights = []
    destination_vertices = []
    destination_mesh = None

    @classmethod
    def get_interpolated_value(cls, interp, a, b):
        return a + ((b - a) * interp)

    @classmethod
    def set_by_interpolation_factor(cls, interpolation_factor):
        skin = maya.mel.eval(f'findRelatedSkinCluster "{cls.destination_mesh}";')
        influences = cmds.skinCluster(skin, query=True, influence=True)
        interpolated_values = []

        for idx in range(len(SkinLerper.target_a_weights)):
            interpolated_values.append(
                cls.get_interpolated_value(
                    interp=interpolation_factor,
                    a=SkinLerper.target_a_weights[idx],
                    b=SkinLerper.target_b_weights[idx]
                ),
            )

        paired_data = []
        for idx in range(len(interpolated_values)):
            paired_data.append((influences[idx], interpolated_values[idx]))

        for vertex in cls.destination_vertices:
            cmds.skinPercent(
                skin,
                vertex,
                transformValue=paired_data,
            )

    @classmethod
    def set_target_a_weights(cls, vertex):
        mesh = vertex.split(".")[0]
        skin = maya.mel.eval(f'findRelatedSkinCluster "{mesh}";')
        SkinLerper.target_a_weights = cmds.skinPercent(skin, vertex, query=True, value=True)

    @classmethod
    def set_target_b_weights(cls, vertex):
        mesh = vertex.split(".")[0]
        skin = maya.mel.eval(f'findRelatedSkinCluster "{mesh}";')
        SkinLerper.target_b_weights = cmds.skinPercent(skin, vertex, query=True, value=True)

    @classmethod
    def set_destination_vertices(cls, vertices):
        SkinLerper.destination_mesh = vertices[0].split(".")[0]
        SkinLerper.destination_vertices = [n for n in vertices]


class SkinInterpSetTargetAWeights(aniseed_toolkit.Tool):
    identifier = 'Interp : Set Target A Weights'
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self):
        SkinLerper.set_target_a_weights(cmds.ls(sl=True)[0])


class SkinInterpSetTargetBWeights(aniseed_toolkit.Tool):
    identifier = 'Interp : Set Target B Weights'
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self):
        SkinLerper.set_target_b_weights(cmds.ls(sl=True)[0])


class SkinInterpApply(aniseed_toolkit.Tool):
    identifier = 'Interp : Apply Interpolation'
    classification = "Rigging"
    categories = [
        "Skinning",
    ]

    def run(self, interpolation_factor=0.5):
        SkinLerper.set_destination_vertices(
            [
                n
                for n in cmds.ls(sl=True, flatten=True)
            ]
        )
        SkinLerper.set_by_interpolation_factor(interpolation_factor)
