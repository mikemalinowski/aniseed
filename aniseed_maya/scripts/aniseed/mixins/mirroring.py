"""
MirrorMixin adds a "Mirror" action to a RigComponent via xstack's
``mixin_functions`` extension point.

The component is expected to declare a "Location" option whose value is
compared against ``self.config.left`` and ``self.config.right``. Only those
two values are mirrorable; any other value (middle, front, back) makes the
component non-mirrorable and hides the menu action.

Compose alongside RigComponent, mixin first:

    from aniseed.mixins.mirroring import MirrorMixin

    class Arm(MirrorMixin, RigComponent):

        identifier = "Limb : Arm"

        def mirror_mixin_items_to_mirror(self):
            return self.input("Bones").get()
"""
import mref
import qtility
import scribble
import aniseed_toolkit


class MirrorMixin:

    # -- Mirror plane for left<->right swaps. Class-level so a subclass can
    # -- override it if a rig ever needs a different reflection.
    MIRROR_PLANE = "YZ"

    # -- Scribble key used to remember the last-used search:replace expression
    _SCRIBBLE_KEY = "aniseed_mirror_expression"

    # ----------------------------------------------------------------------------------
    # xstack framework integration -- do not override in components.
    # ----------------------------------------------------------------------------------
    def mixin_functions(self):
        print("in mixing functions for ")
        if self.can_mirror():
            print("yes")
            return {"Mirror": self._invoke_mirror_from_ui}
        print("no")
        return {}

    # ----------------------------------------------------------------------------------
    # Public API. Override can_mirror to gate the menu dynamically; override
    # mirror only if the standard four-step flow needs replacing wholesale.
    # ----------------------------------------------------------------------------------
    def can_mirror(self) -> bool:
        """
        True when the component's Location option is set to the rig config's
        left or right value. Override to add further preconditions (e.g. a
        required input must be populated).
        """
        location_option = self.option("Location")
        if location_option is None:
            print("no location option")
            return False
        result = location_option.get() in (self.config.left, self.config.right)
        if not result:
            print("not left or right")
            return result

        print("yes can mirror")
        return result

    def mirror(self, search_for: str = None, replace_with: str = None):
        """
        Duplicate this component, swap its Location option to the opposite
        side, apply a regex search-and-replace to the twin's data, and
        mirror the transforms of the declared bones across the YZ plane.

        If ``search_for`` / ``replace_with`` are not provided, the location
        prefix swap is used as the default (e.g. ``"l_"`` -> ``"r_"``).

        :param search_for: Regex pattern to search for in the twin's inputs
            and options. Defaults to the source location prefix + ``"_"``.
        :param replace_with: Replacement string. Defaults to the target
            location prefix + ``"_"``.

        :return: The twin component, or None if this component is not on a
            mirrorable side.
        """
        mref.select(self.mirror_mixin_parent_item())

        source_location = self.option("Location").get()

        if source_location == self.config.left:
            target_location = self.config.right
        elif source_location == self.config.right:
            target_location = self.config.left
        else:
            return None

        if search_for is None:
            search_for = source_location + "_"
        if replace_with is None:
            replace_with = target_location + "_"

        # 1. Duplicate the component (children come along by default)
        twin = self.duplicate(search_for=search_for, replace_with=replace_with)

        # 2. Switch the Location option on the twin
        twin.option("Location").set(target_location)

        # 4. Mirror the transforms of the declared bones
        bones = self.recursive_mirror_items(self) # [name for name in self.mirror_mixin_items_to_mirror() if name]
        if bones:
            aniseed_toolkit.mirror.global_mirror(
                transforms=bones,
                across=self.MIRROR_PLANE,
                behaviour=True,
                name_replacement=[search_for, replace_with],
            )

        return twin

    # ----------------------------------------------------------------------------------
    # Declarative surface -- components override to describe their bones.
    # ----------------------------------------------------------------------------------
    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Return the list of scene-node names representing this component's
        bones. These transforms will be reflected across the mirror plane
        onto the twin side using ``aniseed_toolkit.mirror.global_mirror``.

        Default: empty list (no scene-side mirroring).
        """
        return []

    def mirror_mixin_parent_item(self) -> str:
        """
        """
        return ""

    # ----------------------------------------------------------------------------------
    # UI entry point -- prompts the user for the search:replace expression,
    # then calls mirror() with the collected arguments. Wired up via
    # mixin_functions above.
    # ----------------------------------------------------------------------------------
    def _invoke_mirror_from_ui(self):
        source_location = self.option("Location").get()

        if source_location == self.config.left:
            target_location = self.config.right
        elif source_location == self.config.right:
            target_location = self.config.left
        else:
            return None

        default_expression = f"{source_location}_:{target_location}_"

        user_data = scribble.get(self._SCRIBBLE_KEY)
        prior = user_data.get("expression", default_expression)

        response = qtility.request.text(
            title="Mirror Component",
            message=(
                "Enter a search-and-replace expression to apply to the "
                "twin's data.\n\n"
                "Format: search:replace  (both sides are treated as regex)\n\n"
                f"Default swaps the location prefix: \"{default_expression}\""
            ),
            text=prior,
        )

        if not response:
            return None

        if ":" not in response:
            qtility.request.message(
                title="Mirror Component",
                message="Could not parse the search:replace expression.",
            )
            return None

        # -- Remember for next time
        user_data["expression"] = response
        user_data.save()

        search_for, replace_with = response.split(":", 1)
        return self.mirror(search_for=search_for, replace_with=replace_with)

    @staticmethod
    def recursive_mirror_items(component):
        results = []

        results.extend(
            [
                item
                for item in component.mirror_mixin_items_to_mirror()
                if item
            ]
        )
        for child in component.children:
            results.extend(child.recursive_mirror_items(child))

        return results
