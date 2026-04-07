import mref
import collections


class TransformMixer:
    target_tag = "xformtarget"
    deformer_tag = "xformdeformer"

    def __init__(self, attribute_host):
        self.attribute_host = mref.get(attribute_host)

        self.deformer_parent = self.attribute_host.children(name_match="deformers")[0]
        self.targets_parent = self.attribute_host.children(name_match="targets")[0]

        # -- These are the the transforms that will get driven around
        self.deformers = self.deformer_parent.children()

        # -- These are the attributes which drive the constraints
        self.attributes = self.attribute_host.attributes(userDefined=True)

        # -- For each attribute for each deformer we have a target
        self.targets = collections.defaultdict(mref.ReferenceList)

        for deformer in self.deformers:
            self.targets[deformer] = mref.ReferenceList(
                [
                    n.node()
                    for n in deformer.attr("message").outputs()
                    if self.target_tag in n.node().name()
                ],
            )

        if not self.attribute_host.has_attribute("zero"):
            self.add_attribute("zero")

    @classmethod
    def create(cls, name):
        node = mref.create("transform", name=name)
        deformers_org = mref.create("transform", name="deformers", parent=node)
        targets_org = mref.create("transform", name="targets", parent=node)

        return TransformMixer(node)

    def add_attribute(self, attribute_name):
        """
        Adds an attribute to the attribute tracker, and creates an attribute
        target for each deformer.
        """
        if not self.attribute_host.has_attribute(attribute_name):
            attribute = self.attribute_host.add_attribute(
                name=attribute_name,
                attribute_type="float",
                value=0,
                minValue=0,
                maxValue=1,
                keyable=True,
            )
        else:
            attribute = self.attribute_host.attr(attribute_name)

        self.attributes.append(attribute)

        for deformer in self.deformers:
            self._add_target(deformer, attribute_name)

    def add_deformer(self, name):
        """
        adds a deformer to the list and ensures that it has a target for each
        attribute that already exists.
        """
        deformer = mref.create(
            "transform",
            name=f"{self.deformer_tag}_{name}",
            parent=self.deformer_parent.full_name(),
        )
        deformer.match_to(self.attribute_host)
        self.deformers.append(deformer)

        for attribute in self.attributes:
            self._add_target(deformer, attribute.name())

        return deformer

    def _add_target(self, deformer, attribute_name):

        new_target_parent = mref.create(
            "transform",
            name=f"{self.target_tag}_{attribute_name}_{deformer.name()}_parent",
            parent=self.targets_parent.full_name(),
        )
        new_target = mref.create(
            "transform",
            name=f"{self.target_tag}_{attribute_name}_{deformer.name()}",
            parent=new_target_parent,
        )
        new_target.match_to(deformer)

        # -- Add a link to the deformer
        new_target.add_attribute(
            "deformer",
            attribute_type="message",
            value=None,
        )
        new_target.add_attribute(
            "attribute_name",
            attribute_type="string",
            value=attribute_name,
        )
        deformer.attr("message").connect(new_target.attr("deformer"))

        if deformer.attr("offsetParentMatrix").inputs():
            multiply_matrix = deformer.attr("offsetParentMatrix").inputs()[0].node()
        else:
            multiply_matrix = mref.create("multMatrix")
            multiply_matrix.attr("matrixSum").connect(deformer.attr("offsetParentMatrix"))

        next_matrix_index = len(multiply_matrix.attr("matrixIn").inputs())
        blend_matrix = mref.create("blendMatrix")
        new_target.attr("matrix").connect(blend_matrix.attr("target[1].targetMatrix"))
        self.attribute_host.attr(attribute_name).connect(blend_matrix.attr("target[1].weight"))
        blend_matrix.attr("outputMatrix").connect(multiply_matrix.attr(f"matrixIn[{next_matrix_index}]"))

        # -- Add the taret to the list of targets for this
        # -- deformer
        self.targets[deformer].append(new_target)

    def serialise(self):
        data = dict(
            attributes=self.attributes.names(),
            deformers=dict()
        )

        for deformer in self.deformers:
            deformer_name = deformer.name()[len(self.deformer_tag) + 1:]
            data["deformers"][deformer_name] = dict()
            for target in self.targets[deformer]:
                tag = target.name().split(self.deformer_tag)[0].split(self.target_tag)[-1].replace("_", "")
                # tag = target.attr("attribute_name").get()
                data["deformers"][deformer_name][tag] = target.get_matrix()

        return data

    def deserialise(self, data):

        if not data:
            return

        # -- Delete any current items
        for deformer in self.deformers:
            for target in self.targets[deformer]:
                target.delete()
            deformer.delete()

        # -- Reset our variables
        self.deformers = mref.ReferenceList()
        self.targets = collections.defaultdict(mref.ReferenceList)
        self.attributes = mref.ReferenceList()

        for attribute in data["attributes"]:
            self.add_attribute(attribute)

        for deformer_tag in data["deformers"]:
            deformer = self.add_deformer(deformer_tag)

            for attribute_name in data["deformers"][deformer_tag]:
                target = self.get_target(deformer, attribute_name)
                target.set_matrix(data["deformers"][deformer_tag][attribute_name])

    def get_target(self, deformer, attribute_name):
        for target in self.targets[deformer]:
            if target.attr("attribute_name").get() == attribute_name:
                return target
        return None
