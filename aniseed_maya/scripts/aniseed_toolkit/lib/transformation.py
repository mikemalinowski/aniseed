import mref
import aniseed
import functools
import aniseed_toolkit
from maya import cmds
from maya.api import OpenMaya as om

from . import shapes


def timed_function_call(func):
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print("{} took {} seconds".format(func.__name__, end_time - start_time))
        return result
    return wrapper


def distance_between(
    node_a: str = "",
    node_b: str = "",
    print_result: bool = False,
) -> float:
    """
    Returns the distance between two objects

    Args:
        node_a: The object to measure from
        node_b: The object to measure to
        print_result: If true, the result will be printed

    Returns:
        The distance between two objects
    """

    if not node_a:
        node_a = cmds.ls(sl=True)[0]

    if not node_b:
        node_b = cmds.ls(sl=True)[1]

    point_a = cmds.xform(
        node_a,
        query=True,
        translation=True,
        worldSpace=True,
    )

    point_b = cmds.xform(
        node_b,
        query=True,
        translation=True,
        worldSpace=True,
    )

    point_a = om.MVector(*point_a)
    point_b = om.MVector(*point_b)

    delta = point_b - point_a

    # if print_result:
    #     print(f"Distance between {node_a} and {node_b} is {delta}")
    return delta.length()


def factor_between(node: str = "", from_this: str = "", to_this: str = "", print_result: bool = False) -> float:
    """
    This will return a factor (between zero and one) for how close the given
    node is between the from_this and to_this nodes.

    Args:
        node: The node to monitor
        from_this: The first node to compare to
        to_this: The second node to compare to

    Returns:
        The factor for how close the given node is between the from_this and to_this
    """
    total_distance = aniseed_toolkit.run(
        "Distance Between",
        from_this,
        to_this,
    )

    delta = aniseed_toolkit.run(
        "Distance Between",
        node,
        to_this,
    )

    distance_factor = max(
        0.0,
        min(
            1.0,
            delta / total_distance,
        ),
    )

    if print_result:
        print(f"Factor of {node} between {from_this} and {to_this} is {distance_factor}")

    return distance_factor


def direction_between(
    node_a: str = "",
    node_b: str = "",
    print_result: bool = True,
) -> list[float]:
    """
    This will return a direction vector (normalised vector) between the
    two nodes

    Args:
        node_a: The object to measure from
        node_b: The object to measure to
        print_result: If true, the result will be printed

    Returns:
        The direction vector between the two nodes
    """
    a = cmds.rename(cmds.createNode("transform"), "Xfoo1")
    b = cmds.rename(cmds.createNode("transform"), "Xfoo2")

    cmds.parent(
        b,
        a,
    )

    cmds.xform(
        a,
        matrix=cmds.xform(
            node_a,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    cmds.xform(
        b,
        matrix=cmds.xform(
            node_b,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    tx = cmds.xform(
        b,
        query=True,
        translation=True,
    )

    n = om.MVector(*tx).normal()

    cmds.delete(a)

    if print_result:
        print(f"Direction between {node_a} and {node_b} is {n}")

    return n


def calculate_upvector_position(
    point_a: str = "",
    point_b: str = "",
    point_c: str = "",
    length: float = 0.5,
    create: bool = False,
):
    """
    Based on three points, this will calculate the position for an
    up-vector for the plane.

    Args:
        point_a: Start point (which can be a float list or a node name)
        point_b: End point (which can be a float list or a node name)
        point_c: Start point (which can be a float list or a node name)
        length: By default the vector will be multipled by the chain length
            but you can use this value to multiply that to make it further or
            shorter
        create: If true, a transform node will be created at the specified location

    Returns:
        MVector of the position in worldspace
    """

    if not point_a:
        point_a = cmds.ls(selection=True)[0]

    if not point_b:
        point_b = cmds.ls(selection=True)[1]

    if not point_c:
        point_c = cmds.ls(selection=True)[2]

    # -- If we're given transforms we need to convert them to
    # -- vectors
    if isinstance(point_a, str):
        point_a = cmds.xform(
            point_a,
            query=True,
            translation=True,
            worldSpace=True,
        )

    if isinstance(point_b, str):
        point_b = cmds.xform(
            point_b,
            query=True,
            translation=True,
            worldSpace=True,
        )

    if isinstance(point_c, str):
        point_c = cmds.xform(
            point_c,
            query=True,
            translation=True,
            worldSpace=True,
        )

    point_a = om.MVector(*point_a)
    point_b = om.MVector(*point_b)
    point_c = om.MVector(*point_c)

    # -- Create the vectors between the points
    ab = point_b - point_a
    ac = point_c - point_a
    cb = point_c - point_b

    # -- Get the center point between the end points
    center = point_a + (((ab * ac) / (ac * ac))) * ac

    # -- Create a normal vector pointing at the mid point
    normal = (point_b - center).normal()

    # -- Define the length for the upvector
    vector_length = (ab.length() + cb.length()) * length

    # -- Calculate the final vector position
    result = point_b + (vector_length * normal)

    if create:
        node = cmds.createNode('transform')
        cmds.xform(
            node,
            translation=(
                result.x,
                result.y,
                result.z,
            ),
            worldSpace=True,
        )
        cmds.select(node)

    return result


def calculate_four_point_spline_positions(
    nodes: [str],
):
    """
    This will determine the positions for a bezier spline in order
    to keep the joints transforms.

    Args:
        nodes: List of nodes
    """
    positions = list()
    degree = 1

    points = [
        cmds.xform(
            node,
            query=True,
            translation=True,
            worldSpace=True,
        )
        for node in nodes
    ]

    knots = [
        i
        for i in range(len(points) + degree - 1)
    ]

    cmds.curve(
        point=points,
        degree=degree,
        knot=knots
    )

    quad_curve = cmds.rebuildCurve(
        replaceOriginal=True,
        rebuildType=0,  # Uniform
        endKnots=1,
        keepRange=False,
        keepEndPoints=True,
        keepTangents=False,
        spans=1,
        degree=3,
        tolerance=0.01,
    )[0]

    cv_count = cmds.getAttr(f"{quad_curve}.spans") + cmds.getAttr(f"{quad_curve}.degree")

    for cv_index in range(cv_count):
        position = cmds.xform(
            f"{quad_curve}.cv[{cv_index}]",
            query=True,
            translation=True,
            worldSpace=True,
        )
        positions.append(position)

    cmds.delete(quad_curve)
    return positions

def interpolate_vector(
    vector_a: list[float],
    vector_b: list[float],
    factor: float,
):
    vector_length = len(vector_a)

    resolved_vector = []

    for component_index in range(vector_length):

        a = vector_a[component_index]
        b = vector_b[component_index]
        interpolated_result = a + (b - a) * factor
        resolved_vector.append(interpolated_result)

    return resolved_vector



def position_between(
    node: str = "",
    from_this: str = "",
    to_this: str = "",
    factor = 0.5,
):
    """
    This will set the translation of the given node to be at a position
    between from_this and to_this based on the factor value. A factor
    of zero will mean a position on top of from_this, whilst a factor
    of 1 will mean a position on bottom of to_this.

    Args:
        node: The node to adjust the position for
        from_this: The first node to consider
        to_this: The second node to consider
        factor: The factor value to use

    Returns:
        None
    """
    cns = cmds.pointConstraint(
        to_this,
        node,
        maintainOffset=False,
    )[0]

    cmds.pointConstraint(
        from_this,
        node,
        maintainOffset=False,
    )

    cmds.setAttr(
        cns + "." + cmds.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[0],
        1 - factor
    )

    cmds.setAttr(
        cns + "." + cmds.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[-1],
        factor,
    )

    xform = cmds.xform(
        node,
        query=True,
        matrix=True,
    )

    cmds.delete(cns)

    cmds.xform(
        node,
        matrix=xform,
    )


def get_relative_matrix(node: str = "", relative_to: str = "") -> list[float]:
    """
    This will get a matrix which is the relative matrix between the relative_to
    and the node item

    Args:
        node: The node to consider as the child
        relative_to: The node to consider as the parent

    Returns:
        relative matrix as a list (maya.cmds)
    """
    parent_buffer = cmds.createNode("transform")
    child_buffer = cmds.createNode("transform")

    cmds.parent(
        child_buffer,
        parent_buffer,
    )

    cmds.xform(
        parent_buffer,
        matrix=cmds.xform(
            relative_to,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
    )

    cmds.xform(
        child_buffer,
        matrix=cmds.xform(
            node,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    relative_matrix = cmds.xform(
        child_buffer,
        query=True,
        matrix=True,
    )

    cmds.delete(parent_buffer)

    return relative_matrix


def apply_relative_matrix(node: str, matrix: list[float], relative_to: str = ""):
    """
    This will apply the matrix to the node as if the node were a child
    of the relative_to node

    Args:
        node: The node to adjust
        matrix: The matrix to apply (maya.cmds)
        relative_to: The node to use as a parent for spatial transforms

    Returns:
        None
    """
    parent_buffer = cmds.createNode("transform")
    child_buffer = cmds.createNode("transform")

    cmds.parent(
        child_buffer,
        parent_buffer,
    )

    cmds.xform(
        parent_buffer,
        matrix=cmds.xform(
            relative_to,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
    )

    cmds.xform(
        child_buffer,
        matrix=matrix,
    )

    cmds.xform(
        node,
        matrix=cmds.xform(
            child_buffer,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    cmds.delete(parent_buffer)


def snap_position(snap_this, to_this=None):
    translation = [0, 0, 0]

    if to_this:
        translation = cmds.xform(
            to_this,
            query=True,
            translation=True,
            worldSpace=True,
        )

    cmds.xform(
        snap_this,
        translation=translation,
        worldSpace=True,
    )


class TransformMixer:
    """
    Allows for transforms to be interacted with in the same way that blendshapes
    can be interacted with.

    Must be able to add a deformer. When adding a deformer it will generate a target
    for each pose.

    Must be able to add a pose. When adding a pose it must generate a target representing
    this pose for each deformer.
    """

    def __init__(self, node=None, parent=None):

        if not node:
            node = self.create_node(parent=parent)
        self.node = mref.get(node)

        self.target_lookup = dict()

    # @timed_function_call
    def add_deformer(self, name):
        """
        This should create a transform for the deformer
        """
        deformer_parent = mref.create("transform", name=f"deformerspace_{name}", parent=self.deformer_root())
        # shapes.load_shape(deformer_parent.name(), "core_lollipop")

        new_deformer = mref.create("transform", name=f"deformer_{name}", parent=deformer_parent)
        new_deformer.add_attribute(
            "deformer_name",
            attribute_type="string",
            value=name,
        )

        new_deformer.message.connect_next(self.node.deformers)

        for pose in self.poses():
            print("[in add deformer] creating target for pose : %s" % pose)
            self.create_target(new_deformer, pose)

        return new_deformer

    # @timed_function_call
    def add_pose(self, name):

        self.node.add_attribute(
            name,
            attribute_type="float",
            keyable=True,
            value=0,
        )

        visibility_label = f"show_{name}_targets"
        if not self.node.has_attribute(visibility_label):
            self.node.add_attribute(
                f"show_{name}_targets",
                attribute_type="bool",
                keyable=True,
                value=False,
            )
        new_pose = mref.create("transform", name=f"pose_{name}", parent=self.pose_root())
        new_pose.add_attribute(
            "pose_name",
            attribute_type="string",
            value=name,
        )

        new_pose.add_attribute(
            "targets",
            attribute_type="message",
            value=None,
            multi=True,
        )



        new_pose.message.connect_next(self.node.attr("poses"))

        for deformer in self.deformers():
            target = self.create_target(deformer, new_pose)
            self.node.attr(visibility_label).connect(target.visibility)

        return new_pose

    # @timed_function_call
    def create_target(self, deformer, pose):
        label = f"{deformer.name()}__{pose.name()}"

        target = mref.create("transform", name=f"target__{label}", parent=deformer.parent())
        target.set_matrix(deformer.get_matrix(space="world"), space="world")
        shapes.load_shape(target.name(), "core_cube")

        target.add_attribute(
            "deformer_name",
            attribute_type="string",
            value=deformer.attr("deformer_name").get()
        )

        target.add_attribute(
            "pose_name",
            attribute_type="string",
            value=pose.pose_name.get(),
        )
        target.message.connect_next(pose.attr("targets"))
        blend_translation = mref.create("multiplyDivide", name=f"blendtrans__{label}")
        blend_rotation = mref.create("multiplyDivide", name=f"blendtrot__{label}")

        try:
            translation_combiner = deformer.attr("translate").inputs()[0].node()
        except IndexError:
            translation_combiner = mref.create("plusMinusAverage", name=f"addtranslation_{label}")
            translation_combiner.attr("output3D").connect(deformer.attr("translate"))

        try:
            rotation_combiner = deformer.attr("rotate").inputs()[0].node()
        except IndexError:
            rotation_combiner = mref.create("plusMinusAverage", name=f"addrotate_{label}")
            rotation_combiner.attr("output3D").connect(deformer.attr("rotate"))

        target.attr("translate").connect(blend_translation.attr("input1"))
        target.attr("rotate").connect(blend_rotation.attr("input1"))

        for axis in ["X", "Y", "Z"]:
            driving_attribute = self.node.attr(pose.attr("pose_name").get())
            driving_attribute.connect(blend_translation.attr(f"input2{axis}"))
            driving_attribute.connect(blend_rotation.attr(f"input2{axis}"))

        blend_translation.attr("output").connect_next(translation_combiner.attr("input3D"))
        blend_rotation.attr("output").connect_next(rotation_combiner.attr("input3D"))

        return target

    def create_node(self, parent=None):
        node = mref.create("transform", name="transformMixer", parent=parent)
        node.add_attribute(
            "deformers",
            attribute_type="message",
            value=None,
            multi=True,
        )
        node.add_attribute(
            "poses",
            attribute_type="message",
            value=None,
            multi=True,
        )
        mref.create("transform", name="deformerRoot", parent=node)
        mref.create("transform", name="poseRoot", parent=node)

        return node

    def remove_deformer(self, deformer_name):
        self.get_deformer(deformer_name).delete()

        for pose in self.poses():
            target = self.get_target(pose_name=pose.attr("pose_name").get(), deformer_name=deformer_name)
            if target:
                target.delete()

    def remove_pose(self, pose_name):
        self.get_target(pose_name=pose_name).delete()

    def deformer_root(self):
        return self.node.children(node_type="transform", name_match="deformerRoot")[0]

    def pose_root(self):
        return self.node.children(node_type="transform", name_match="poseRoot")[0]

    def poses(self):
        return [n.node() for n in self.node.poses.inputs()]

    def deformers(self):
        print("NODE: %s" % self.node)
        print(self.node.deformers)
        print(self.node.deformers.inputs())
        return [n.node() for n in self.node.deformers.inputs()]

    @functools.lru_cache(maxsize=None)
    def get_pose(self, pose_name):
        for pose_node in self.poses():
            if pose_node.attr("pose_name").get() == pose_name:
                return pose_node
        return None

    @functools.lru_cache(maxsize=None)
    def get_deformer(self, deformer_name):
        for deformer_node in self.deformers():
            if deformer_node.attr("deformer_name").get() == deformer_name:
                return deformer_node
        return None

    # def get_target(self, pose_name, deformer_name):
    #     for node in self.get_pose(pose_name).children(recursive=True):
    #         if cmds.objExists(f"{node.name()}.deformer_name"):
    #             if node.attr("deformer_name").get() == deformer_name:
    #                 return node
    #     return None

    @functools.lru_cache(maxsize=None)
    def get_target(self, pose_name, deformer_name):
        pose_node = self.get_pose(pose_name)

        targets = [
            target.node()
            for target in pose_node.targets.inputs()
        ]

        for target in targets:
            if cmds.getAttr(target.name() + ".deformer_name") == deformer_name:
                return target

        return None

    def get_target_mapping(self):
        results = dict()
        for pose in self.poses():
            pose_name = pose.attr("pose_name").get()
            targets = [n.node() for n in pose.targets.inputs()]

            for target in targets:
                results[f"{pose_name}--{target.attr('deformer_name').get()}"] = target
        return results

    @timed_function_call
    def serialise(self):
        """
        {
        "deformers": [
            {"name":"", "transform": []},
            {"name":"", "transform": []},
            {"name":"", "transform": []}
        ]
        "poses": [
            {
                "name":"",
                "targets": [
                    {"name":"", "transform": []},
                    {"name":"", "transform": []},
                ]
            }
        ]

        }
        """
        data = {
            "deformers": [],
            "poses": []
        }

        deformers = self.deformers()
        deformer_names = [
            deformer.attr("deformer_name").get()
            for deformer in deformers
        ]
        poses = self.poses()
        pose_names = [
            pose.attr("pose_name").get()
            for pose in poses
        ]
        target_data = self.get_target_mapping()

        for idx, deformer in enumerate(deformers):
            data["deformers"].append(
                {
                    "name": deformer_names[idx],
                    "transform": deformer.parent().get_matrix(),
                    "rotation_order": deformer.attr("rotateOrder").get(),
                }
            )

        for pose_idx, pose in enumerate(poses):
            pose_name = pose_names[pose_idx]
            pose_data = {
                "name": pose_name,
                "targets": [],
            }

            for deformer_idx, deformer in enumerate(deformers):
                deformer_name = deformer_names[deformer_idx]
                lookup_label = f"{pose_name}--{deformer_name}"
                target = target_data[lookup_label]
                # target = self.get_target(pose_names[pose_idx], deformer_name=deformer_names[deformer_idx])
                pose_data["targets"].append(
                    {
                        "name": deformer_name,
                        "transform": target.get_matrix(),
                    }
                )
            data["poses"].append(pose_data)
        return data

    @classmethod
    def deserialise(cls, data, parent=None):

        mixer = cls(parent=parent)

        for deformer_data in data.get("deformers", list()):
            deformer = mixer.add_deformer(deformer_data["name"])
            deformer.parent().set_matrix(deformer_data["transform"])
            deformer.rotateOrder.set(deformer_data["rotation_order"])

        for pose_data in data.get("poses", list()):
            pose = mixer.add_pose(pose_data["name"])

            for target_data in pose_data["targets"]:
                target = mixer.get_target(pose_data["name"], target_data["name"])
                target.set_matrix(target_data["transform"])

        return mixer

