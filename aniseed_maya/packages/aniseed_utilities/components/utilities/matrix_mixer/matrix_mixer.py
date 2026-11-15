"""
Provides the "Utility : Matrix Mixer" component, which builds an
aniseed_utilities MatrixMixer (see au.rig.matrix_mixer) from stored data,
driving its Driven Objects through their offsetParentMatrix. Poses and
driven objects are edited in the Matrix Mixer Pose Editor, which the Open
Pose Editor option opens and which stores every change back into the
component.

Other components can attach a mixer beneath themselves with add_to, listing
their own outputs (addresses) as the driven objects, as those nodes only
exist once they have built.
"""
import os
import logging

import mref
import aniseed
import qtility
import aniseed_utilities as au
from aniseed import toolkits

log = logging.getLogger(__name__)


class MatrixMixer(aniseed.RigComponent):
    """
    Builds a matrix mixer (see au.rig.matrix_mixer.MatrixMixer) from the
    stored data, driving each of the Driven Objects through its
    offsetParentMatrix. Poses are blended onto the driven objects much like
    a blendshape blends vertices, and each pose weight is a keyable
    attribute on the mixer node (optionally proxied onto other nodes).

    All editing (poses, driven objects, saving and loading json) is done in
    the Matrix Mixer Pose Editor tool, opened from the Open Pose Editor
    option, which stores the result back into the component.
    """

    identifier = "Utility : Matrix Mixer"
    icon = os.path.join(os.path.dirname(__file__), "matrix_mixer.png")

    # -- The options naming the mixer node and holding its data, which the
    # -- Matrix Mixer Pose Editor tool stores edited poses into
    mixer_options = ("Node", "Data")

    # -- The option listing the driven objects, which the editor adds to
    mixer_driven_option = "Driven Objects"

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent input, the Driven Objects, Proxy Hosts and naming
        options, the hidden mixer Data and Node storage and the editing
        button options.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the mixer node is parented under",
        )

        self.declare_option(
            name="Driven Objects",
            value=[],
            description=(
                "The nodes (or addresses) the mixer drives, through their offsetParentMatrix. Their poses are "
                "stored under these names, so renaming one here disconnects it from its stored poses."
            ),
        )

        self.declare_option(
            name="Proxy Hosts",
            value=[],
            description="Nodes (or addresses) which are given a proxy of every pose weight when the mixer builds",
        )

        self.declare_option(
            name="Descriptive Prefix",
            description=(
                "If given, every node of the mixer is named with the rig configuration, with this in front "
                "of its description. If not, the nodes keep the mixer's own names (matrixMixer etc)."
            ),
            value="",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            description="Location token (e.g. md/lf/rt) applied to the node names, when a Descriptive Prefix is given",
            value=self.config.middle,
            group="Naming",
        )

        self.declare_option(
            name="Data",
            value={},
            hidden=True,
            description="The serialised mixer: its poses and their matrices, keyed by the Driven Objects entries",
        )

        self.declare_option(
            name="Node",
            value="",
            hidden=True,
            description="The name of the mixer node made by the last build",
        )

        self.declare_option(
            name="Open Pose Editor",
            value=None,
            description=(
                "Opens the Matrix Mixer Pose Editor on the built mixer, to edit its poses and driven objects "
                "and save or load them as json"
            ),
        )

        self.declare_output(
            name="Mixer",
            description="The mixer node, whose pose attributes drive the poses",
            is_default=True,
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the Parent input.
        """
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector()

    def option_widget(self, requirement_name: str):
        """
        Returns object lists for the Driven Objects and Proxy Hosts, a
        location selector, and the Open Pose Editor button.
        """
        if requirement_name in ("Driven Objects", "Proxy Hosts"):
            return aniseed.widgets.ObjectList()

        if requirement_name == "Location":
            return aniseed.widgets.LocationSelector(self.config, self.option(requirement_name).get())

        if requirement_name == "Open Pose Editor":
            return aniseed.widgets.ButtonWidget(button_name="Open Pose Editor", func=self.open_pose_editor)

    def is_valid(self) -> bool:
        """
        Checks that every Driven Object entry names something. Entries are
        resolved at build time, as addresses only exist once the components
        before this one have built.
        """
        for entry in self.option("Driven Objects").get() or list():
            if not entry:
                log.warning(f"{self.label()} : The Driven Objects list has an empty entry")
                return False

        return True

    def run(self) -> bool:
        """
        Builds the mixer under the Parent input, drives every Driven Object
        which exists (warning about any which do not, whose stored poses are
        kept), applies the stored poses, proxies every pose weight onto the
        Proxy Hosts and records the mixer node's name.
        """
        mixer = au.rig.matrix_mixer.MatrixMixer(
            parent=self.input("Parent").get() or None,
            namer=self._namer(),
        )
        self.option("Node").set(mixer.node.name())
        self.output("Mixer").set(mixer.node.name())

        with mixer:
            for key in self.option("Driven Objects").get() or list():
                node_name = self._resolve(key)

                if not node_name or not mref.objExists(node_name):
                    log.warning(f"{self.label()} : {key!r} resolves to {node_name!r}, which does not exist")
                    continue

                try:
                    mixer.add_driven(node_name, key=key)

                except ValueError as error:
                    log.warning(f"{self.label()} : {error}")

            missing = mixer.apply_data(self.option("Data").get() or dict())

        for key in missing:
            log.warning(f"{self.label()} : Poses are stored for {key!r}, which is not driven. They are kept.")

        for host in self.option("Proxy Hosts").get() or list():
            host_name = self._resolve(host)

            if not host_name or not mref.objExists(host_name):
                log.warning(f"{self.label()} : The proxy host {host_name!r} does not exist")
                continue

            m_host = mref.get(host_name)
            for pose_name in mixer.pose_names():
                if m_host.has_attribute(pose_name):
                    log.warning(f"{self.label()} : {host_name} already has a {pose_name!r} attribute, so it is not proxied")
                    continue

                m_host.add_proxy(pose_name, mixer.weight_attribute(pose_name))

        return True

    def _namer(self):
        """
        Returns the callable which names the mixer's nodes with the rig
        configuration (mechanical, the Descriptive Prefix and Location), or
        None if there is no Descriptive Prefix.
        """
        prefix = self.option("Descriptive Prefix").get()
        if not prefix:
            return None

        location = self.option("Location").get()
        return lambda label: self.config.generate_name(
            classification=self.config.mechanical,
            description=f"{prefix}{label}",
            location=location,
        )

    def _resolve(self, value):
        """
        Returns the value of the attribute the given value addresses, or the
        value itself if it is not an address.
        """
        if not value:
            return value

        attribute = self.rig.resolve_attribute(value)
        return attribute.get() if attribute else value

    @classmethod
    def add_to(
            cls,
            component,
            label: str,
            parent: str,
            driven: list,
            proxy_hosts: list = None,
            prefix: str = "",
            location: str = None,
    ):
        """
        Adds a Matrix Mixer component to the stack as a child of the given
        component, with no poses.

        Other components can reach this without importing this module, via
        ``self.rig.component_library.request("Utility : Matrix Mixer").add_to(...)``.

        Args:
            component: The component to add the mixer beneath
            label: The label for the mixer component
            parent: The node (or address) to parent the mixer under
            driven: The nodes (or addresses) the mixer drives
            proxy_hosts: Optional nodes (or addresses) to proxy every pose
                weight onto
            prefix: Sets the Descriptive Prefix option, which names the
                mixer's nodes with the rig configuration
            location: Sets the Location option. If not given, the given
                component's Location is used (if it has one).

        Returns:
            The matrix mixer component
        """
        options = {
            "Driven Objects": list(driven),
            "Proxy Hosts": list(proxy_hosts or []),
            "Descriptive Prefix": prefix,
        }

        if location is None and component.option("Location") is not None:
            location = component.option("Location").get()
        if location is not None:
            options["Location"] = location

        return component.stack.add_component(
            component_type=cls.identifier,
            label=label,
            parent=component,
            inputs={
                "Parent": parent,
            },
            options=options,
        )

    def mixer(self, silent: bool = False) -> au.rig.matrix_mixer.MatrixMixer | None:
        """
        Returns the mixer built by the last build, or None if it does not
        exist (after showing an error message, unless silent).
        """
        mixer_node = self.option("Node").get()

        if not au.rig.matrix_mixer.MatrixMixer.is_mixer(mixer_node):
            if not silent:
                qtility.request.message(
                    title="Error",
                    message="You must build the rig before interacting with the mixer",
                    parent=None,
                )
            return None

        return au.rig.matrix_mixer.MatrixMixer(mixer_node, namer=self._namer())

    def snapshot(self, mixer=None, previous: dict = None) -> None:
        """
        Serialises the built mixer into the Data option so it rebuilds the
        same way next time. Poses of driven objects which are not built (for
        instance because they were missing) are kept from the previous data.

        Args:
            mixer: The built mixer. If not given it is found from the Node
                option.
            previous: The data to keep unbuilt objects' poses from. If not
                given, the currently stored data is used.
        """
        mixer = mixer or self.mixer()

        if not mixer:
            return

        if previous is None:
            previous = self.option("Data").get() or dict()

        self.option("Data").set(au.rig.matrix_mixer.merge_unbound(mixer.serialise(), previous))

    def open_pose_editor(self) -> None:
        """
        Opens the Matrix Mixer Pose Editor on this component's mixer.
        """
        mixer = self.mixer()

        if not mixer:
            return

        toolkits.run("Matrix Mixer Pose Editor", options={"Mixer Node": mixer.node.name()})

    def driven_list(self, mixer) -> list:
        """
        Returns the Driven Objects option updated to match the mixer: entries
        the mixer drives keep their place (as do entries which did not build,
        so nothing is lost), and newly driven objects are added at the end.
        """
        driven_keys = mixer.driven_keys()
        current = list(self.option("Driven Objects").get() or list())

        missing = [
            entry
            for entry in current
            if entry not in driven_keys and not self._resolves(entry)
        ]

        return [
            entry
            for entry in current
            if entry in driven_keys or entry in missing
        ] + [
            key
            for key in driven_keys
            if key not in current
        ]

    def _resolves(self, entry) -> bool:
        """
        Returns True if the Driven Objects entry resolves to an existing node.
        """
        node_name = self._resolve(entry)
        return bool(node_name) and mref.objExists(node_name)
