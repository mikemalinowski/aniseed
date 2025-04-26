"""
This module holds functionality to apply and generate styling information
to widgets
"""
import os
import re
import typing

from PySide2 import QtWidgets


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def apply(
        styles: typing.List[typing.AnyStr],
        apply_to: QtWidgets.QWidget,
        **kwargs
) -> None:
    """
    Applies all the given styles in order (meaning each will override any
    overlapping elements of the previous).

    All kwargs are considered replacements when wrangling your stylesheet.
    This allows you to place variables into your css file and have them resolved
    at runtime.

    Args
        styles: This can be a single stylesheet or a list of stylesheets.
            The stylesheet can be given in three different forms (and is checked
            in this order):

                * An absolute filepath to a css/qss file

                * A Name of any stylesheet which exists in any location defined
                    within the QUTE_STYLE_PATH environment variable

                * Actual stylesheet data


        apply_to: The QWidget which should have the stylesheet applied
        kwargs: Any string replacements where the key is a regex and the
            value is the replacement string

    Returns:
        None
    """
    # -- Start collating our style data
    compounded_style = ''

    for given_style in styles:

        extracted_style = None

        if ";" in given_style:
            extracted_style = given_style

        else:
            # -- Firstly we check if we're given an absolute path which
            # -- resolves
            if not os.path.exists(given_style):
                constants.log("%s does not exist" % given_style)
                continue

            with open(given_style, 'r') as f:
                extracted_style = f.read()

        # -- If we still do not have an extracted style then we need
        # -- to report a warning
        if not extracted_style:
            constants.log.warning(
                'Could not extract or locate the style : %s' % given_style
            )
            continue

        # -- Add this extracted data to the compounded style
        compounded_style += '\n' + extracted_style

    # -- We need to combine the kwargs with the defaults
    styling_parameters = dict()
    styling_parameters.update(kwargs)

    # -- Now that we have compounded all our style information we can cycle
    # -- over it and carry out any replacements
    for regex, replacement in styling_parameters.items():
        regex = re.compile(regex)
        compounded_style = regex.sub(replacement, compounded_style)

    # -- Apply the composed stylesheet
    apply_to.setStyleSheet(compounded_style)


# ------------------------------------------------------------------------------
def compoundedStylesheet(widget: QtWidgets.QWidget) -> typing.AnyStr:
    """
    This will return the entire stylesheet which is affecting this widget.
    The resulting stylesheet will be the widgets stylesheet, and the
    stylesheet of all its parents.

    The order is such that the widgets style is last, and the root level
    widgets style is first - meaning you can apply the returned stylesheet
    to create the exact same result.

    Args:
        widget: The QWidget to resolve the stylesheet from
    Returns:
        The hierarchical stylesheet
    """
    all_data = [widget.styleSheet()]

    while widget.parentWidget():
        # -- Iterate to the parent
        widget = widget.parentWidget()

        # -- Take the stylesheet, or an empty string if there
        # -- is no stylesheet
        all_data.append('' or widget.styleSheet())

    # -- Now we reverse the list, so the base parent comes first and the leaf
    # -- style comes last
    all_data.reverse()

    # -- Finally, we join it all together into a single string
    all_data = '\n'.join(all_data)

    return all_data
