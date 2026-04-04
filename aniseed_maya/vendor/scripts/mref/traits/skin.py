import mref
from maya import cmds
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as oma


class SkinCluster(mref.Trait):

    def __init__(self, *args, **kwargs):
        super(SkinCluster, self).__init__(*args, **kwargs)

        self._dependency_node = om.MFnDependencyNode(self._pointer)
        self._skin_cluster = oma.MFnSkinCluster(self._pointer)

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        if isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kSkinClusterFilter):
            return True
        return False

    def influences(self) -> list[mref.ReferencedItem]:
        """
        Returns a list of influences on the skin cluster
        """
        results = []

        for m_influence in self._skin_cluster.influenceObjects():
            results.append(mref.get(m_influence.node()))
        return results

    def weights(self) -> dict:
        """
        Returns a dictionary of skin weights in the following format:

        {
            influence (mref.ReferenceItem): list of floats where each value is the weight for the vertex id
        }
        """
        shape = self.shape()

        if not shape:
            return dict()

        # Get vertex count
        component_count = shape.component_count()

        # Initialize dictionary
        weights_dict = {inf: [0.0] * component_count for inf in self.influences()}

        # Loop over vertices
        for component_id in range(component_count):

            # Query weights for all influences on this vertex
            weights = cmds.skinPercent(self.item.full_name(), shape.component_path(component_id), query=True, value=True)

            for inf_index, inf in enumerate(self.influences()):
                weights_dict[inf][component_id] = weights[inf_index]

        return weights_dict

    def set_weights(self, weights: dict, normalize: bool = True) -> None:
        """
        Sets the skin weights. The weight data is expected to be in the following
        format:

        {
            influence (mref.ReferenceItem): list of floats where each value is the weight for the vertex id
        }
        """

        shape = self.shape()
        if not shape:
            return

        component_count = shape.component_count()

        for component_id in range(component_count):

            transform_value = []
            for influence in self.influences():
                w = weights.get(influence, [0.0] * component_count)[component_id]
                transform_value.append((influence.full_name(), w))

            cmds.skinPercent(
                self.item.full_name(),
                shape.component_path(component_id),
                transformValue=transform_value,
                normalize=normalize
            )

    def add_influence(self, influence: mref.ReferencedItem|str, **kwargs) -> None:
        """
        This will add the given influence to the skin cluster
        """
        influence = mref.get(influence)
        cmds.skinCluster(self.item.full_name(), edit=True, addInfluence=influence.full_name(), **kwargs)

    def shape(self) -> mref.ReferencedItem:
        """
        Returns the first shape being driven by this skin cluster
        """
        return mref.get(cmds.skinCluster(self.item.full_name(), query=True, geometry=True)[0])

    def shapes(self) -> list[mref.ReferencedItem]:
        """
        Returns a list of shapes being driven by this skin cluster
        """
        return [mref.get(n) for n in cmds.skinCluster(self.item.full_name(), query=True, geometry=True)]
