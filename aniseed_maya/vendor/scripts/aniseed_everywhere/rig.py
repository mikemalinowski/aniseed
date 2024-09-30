import os
import json
import typing
import xstack
import traceback

from crosswalk import app

from . import config
from . import component
from . import constants


# --------------------------------------------------------------------------------------
class Rig(xstack.Stack):
    """
    This class is what represents a rig. It is built upon xstack, and therefore is an
    execution stack. You may add components to the rig and ultimately execute the build
    of that rig.

    Args:
        label: You only need to provide this if you are asking for a new rig to be
            built. This will be the name of the rig

        host: This should be the object that represents the rig. This class will
            auto-populate based on the data stored on that object.

        component_paths: An optional list of paths that should be added to the
            component library
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, label="", host=None, component_paths: typing.List or None = None):
        super(Rig, self).__init__(
            label=label,
            component_paths=component_paths,
            component_base_class=component.RigComponent,
        )

        # -- If we're not given a host, then we need to add one
        if not host:
            host = self._create_host(label)
            is_new_rig = True

        else:
            is_new_rig = False


        # -- Store our host
        self._host = host

        # -- Add our rig configuration class to the component library. We do this because
        # -- we always need one rig configuration class to be present
        self.component_library.register_item(
            config.RigConfiguration,
        )

        # -- Ensure we add any paths set by the environment
        paths = os.environ.get(constants.RIG_COMPONENTS_PATHS_ENVVAR, "").split(",")

        for path in paths:
            if path:
                self.component_library.register_path(path)

        x = app.attributes.get_attribute(
            self.host(),
            "recipe",
        )

        self.deserialize(
            json.loads(
                app.attributes.get_attribute(
                    self.host(),
                    "recipe",
                ),
            )
        )

        # -- As we have now populated the class, emit the fact that the class has
        # -- changed
        self.changed.connect(
            self.serialise,
        )

    # ----------------------------------------------------------------------------------
    def host(self):
        return self._host

    # ----------------------------------------------------------------------------------
    @property
    def label(self):
        """
        We always want to return the name of the host when getting the label
        """
        return app.objects.get_name(self.host())

    # ----------------------------------------------------------------------------------
    @label.setter
    def label(self, v):
        """
        Our label is always defined by the name of the host
        """
        pass

    # ----------------------------------------------------------------------------------
    def config(self):
        """
        This will return the rig configuration class for the rig
        """
        for component_instance in self.components():
            if component_instance.identifier.startswith("Rig Configuration :"):
                return component_instance

        print("could not locate configuration component")
        return None

    # ----------------------------------------------------------------------------------
    def serialise(self) -> typing.Dict:
        """
        We subclass the serialise function so that we can take the serialised
        data and store it within the host object
        """
        data = super(Rig, self).serialise()

        app.attributes.set_attribute(
            object_=self.host(),
            attribute_name="recipe",
            value=json.dumps(data),
        )

        return data

    # ----------------------------------------------------------------------------------
    @classmethod
    def _create_host(cls, name: str):
        """
        This will create the host object within the applications scene. It ensures the host
        has the right attributes to be able to store its serialised
        """
        host = app.objects.create(
            name=name,
        )

        app.attributes.add_float_attribute(
            object_=host,
            attribute_name="aniseed_rig",
            value=1,
        )

        app.attributes.add_string_attribute(
            object_=host,
            attribute_name="recipe",
            value="{}"
        )

        return host

    # ----------------------------------------------------------------------------------
    # noinspection PyBroadException
    def build(
        self,
        build_up_to: str = None,
        build_only: str = None,
        build_below: str = None,
        validate_only: bool = False
    ) -> bool:
        """
        We re-implement the build to allow us to check whether we have a rig configuration
        component in a stack. If we do not, or if it is not valid then we do not allow
        the build to continue
        """

        if not self.config():
            print("No configuration component found. You must have one in order to build")
            return False

        # -- We also need to check that it is valid. But not, its posisble this could be
        # -- third party code, so we wrap it in a broad exception
        try:
            if not self.config().is_valid():
                print("Failed to validate the rig configuration. Stopping build.")
                return False

        except:
            print(f"Failed to run validation for {self.config()}")
            print(traceback.print_exc())
            return False

        return super(Rig, self).build(
            build_up_to,
            build_only,
            build_below,
            validate_only,
        )