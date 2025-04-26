import qtility
import scribble
import collections
import aniseed_toolkit
import maya.cmds as mc


MIRROR_PLANES = {
    "Z": 'XY',
    "X": 'YZ',
    "Y": 'XZ',
}


class GlobalMirrorTool(aniseed_toolkit.Tool):

    identifier = "Global Mirror"
    categories = [
        "Transforms",
    ]

    def run(
        self,
        transforms: list[str] or str = None,
        across: str = "XY",
        behaviour: bool = True,
        name_replacement: dict = None,
    ):
        """
        This function is taken from github with a minor modification. The
        author and credit goes to Andreas Ranman.

        Github Url:
            https://gist.github.com/rondreas/1c6d4e5fc6535649780d5b65fc5a9283

        Mirrors transform across hyperplane.

        Args:
            transforms: list of Transform or string.
            across: plane which to mirror across (XY, YX or XZ).
            behaviour: If true, it should mirror the rotational behaviour too
            name_replacement : a tuple of length two, where the first part should
                be replaced with the second part
        """

        # No specified transforms, so will get selection
        if not transforms:
            transforms = mc.ls(sl=True)

        # -- If we're not given a value for "across", prompt for
        # -- one
        across = across or self.ask_for_mirror_plane()

        # Validate plane which to mirror across,
        if across not in ('XY', 'YZ', 'XZ'):
            raise ValueError(
                "Keyword Argument: 'across' not of accepted value ('XY', 'YZ', 'XZ').")

        # -- Ask for any name replacement data if required
        if name_replacement is None:
            name_replacement = self.ask_for_rename_data()

        stored_matrices = collections.OrderedDict()

        for transform in transforms:

            node_type = mc.nodeType(transform)

            allowable_types = [
                "transform",
                "joint",
            ]

            if node_type not in allowable_types:
                print(f"{transform} is not a transform or joint, skipping")
                continue

            # Get the worldspace matrix, as a list of 16 float values
            mtx = mc.xform(transform, q=True, ws=True, m=True)

            # Invert rotation columns,
            rx = [n * -1 for n in mtx[0:9:4]]
            ry = [n * -1 for n in mtx[1:10:4]]
            rz = [n * -1 for n in mtx[2:11:4]]

            # Invert translation row,
            t = [n * -1 for n in mtx[12:15]]

            # Set matrix based on given plane, and whether to include behaviour or not.
            if str(across) == 'XY':
                mtx[14] = t[2]  # set inverse of the Z translation

                # Set inverse of all rotation columns but for the one we've set translate to.
                if behaviour:
                    mtx[0:9:4] = rx
                    mtx[1:10:4] = ry

            elif str(across) == 'YZ':
                mtx[12] = t[0]  # set inverse of the X translation

                if behaviour:
                    mtx[1:10:4] = ry
                    mtx[2:11:4] = rz
            else:
                mtx[13] = t[1]  # set inverse of the Y translation

                if behaviour:
                    mtx[0:9:4] = rx
                    mtx[2:11:4] = rz

            stored_matrices[transform] = mtx

        for transform in stored_matrices:
            target = transform

            if name_replacement:
                target = target.replace(
                    name_replacement[0],
                    name_replacement[1],
                )

            mc.xform(
                target,
                ws=True,
                m=stored_matrices[transform]
            )

    def ask_for_mirror_plane(self):

        mirror_plane = qtility.request.item(
            title="Mirroring",
            message="Please select the axis you want to mirror across",
            items=sorted(
                MIRROR_PLANES.keys(),
            ),
            editable=False,
        )

        if not mirror_plane:
            return None

        return MIRROR_PLANES[mirror_plane]


    def ask_for_rename_data(self):

        user_data = scribble.get("mirror_across_options")

        replacement_data = qtility.request.text(
            title="Mirroring",
            message=(
                "You can (optionally) provide a search and replace. \n"
                "If you do, this will mirror the selected transforms "
                "over to the objects with the replaced "
                "name. "
                "\n\n"
                "Use the format 'replace_this:with_this"
                "\n\n"
                "If you leave it blank, it will mirror the selected objects"
            ),
            text=user_data.get("mirror_expression", "")
        )

        if not replacement_data:
            return

        if ":" not in replacement_data:
            qtility.request.message(
                title="Mirroring",
                message="Could not resolve the remapping format",
            )
            return

        # -- Store the users expression so they do not always
        # -- have to retype it
        user_data["mirror_expression"] = replacement_data
        user_data.save()

        return [
            replacement_data.split(":")[0],
            replacement_data.split(":")[1],
        ]


class InvertTranslationTool(aniseed_toolkit.Tool):

    identifier = "Invert Translation"
    categories = [
        "Transforms",
    ]

    def run(self, transforms: list[str] = None) -> None:
        """
        This will invert the translation channels of a node

        Args:
            transforms: List of transforms to invert the translation of

        Returns:
            None
        """
        if not transforms:
            transforms = mc.ls(sl=True, type="joint")

        parent_map = dict()

        for transform in transforms:
            for axis in ["tx", "ty", "tz"]:

                mc.setAttr(
                    f"{transform}.{axis}",
                    mc.getAttr(f"{transform}.{axis}") * -1,
                )
