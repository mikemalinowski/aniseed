import typing
from pymxs import runtime as mxs

from . import items


def add_string_attribute(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should add an attribute to the item, and where the attributes are
    typed, it should be a string

    Args:
        item: The item or item name to add the attribute to
        attribute_name: The name of the attribute
        value: The value of the attribute
    """
    return _add_property(
        item,
        attribute_name,
        "String",
        value,
    )


def add_float_attribute(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should add an attribute to the item, and where the attributes are
    typed, it should be a float
    """
    return _add_property(
        item,
        attribute_name,
        "Float",
        value,
    )


def set_value(item: object, attribute_name: str, value: typing.Any) -> None:
    """
    This should set the attribute with the given name on the given item to the
    given value
    """
    # if isinstance(value, str):
    #     value = '"%s"' % value
    #
    # else:
    #     value = str(value)

    # -- Start by trying for custom attributes
    container_count = mxs.custAttributes.count(item)
    for i in range(container_count + 1):
        container = mxs.custAttributes.get(item, i)
        if hasattr(container, attribute_name):
            setattr(container, attribute_name, value)
            return

    # -- To reach here we're not dealing with a custom attribute
    # -- so we try and set the item directly or through the baseObject
    try:
        item_name = items.get_name(item)
        command = f"{item_name}.{attribute_name} = {value}"
        mxs.execute(command)

    except RuntimeError:
        if 'baseObject' not in attribute_name:
            set_attribute(
                item,
                'baseObject.%s' % attribute_name,
                value,
            )


def get_value(item: object, attribute_name: str) -> typing.Any:
    """
    This should look on the item for an attribute of this name and return its value
    """
    # -- Start by trying for custom attributes
    container_count = mxs.custAttributes.count(item)
    for i in range(container_count + 1):
        container = mxs.custAttributes.get(item, i)
        if hasattr(container, attribute_name):
            return getattr(container, attribute_name)

    try:
        return mxs.execute(f"{item}.{attribute_name}")

    except RuntimeError:
        if 'baseObject' not in attribute_name:
            return get_attribute(
                item,
                'baseObject.%s' % attribute_name,
            )

    return None


def has_attribute(item: object, attribute_name: str) -> bool:
    """
    This should check if an item has an attribute of this name
    """
    return hasattr(
        item,
        attribute_name,
    )


def _add_property(item, name, property_type, value=None):

    # -- Attributes are better exposed in pymxs rather than
    # -- MaxPlus, so the internals of this function will work
    # -- in pymxs
    rollouts = dict(
        Float='spinner %s "%s" type: #%s' % (
                name,
                name.title(),
                property_type
        ),
        String="edittext %s \"%s:\" Width:140 Height:17 Align:#Center Offset:[0,0] Type:#String labelOnTop:false readonly:False" % (
            name,
            name.title(),
        )
    )

    # -- If no block address is specified we automatically add one
    if '.' not in name:
        name = '%s.%s' % (
            name,
            name,
        )

    # -- Break out the block name and the attribute name
    block_name, attr_name = name.split('.')

    # -- If the block already exists then we need to get the definition
    # -- of that block, otherwise we need to create a new definition
    block = None
    existing_definition = None

    # -- Cycle over our attr defs on this object
    attr_defs = mxs.custAttributes.getDefs(item)

    for attr_def in attr_defs or list():

        # -- We only care about blocks which share the block name
        if block_name == str(attr_def.name):

            # -- Get the source data for this attribute definition
            block = attr_def.source[:]
            existing_definition = attr_def
            break

    # -- If this is not a pre-existing block we create a new definition
    # -- otherwise we flag it as requiring redefinition
    block = block or _new_block_definition(block_name)

    # -- We now need to cycle over all the source and inject our new
    # -- attribute into it
    redefined_lines = list()
    lines = block.splitlines()

    # -- We now need to cycle over the definition source, and manipulate
    # -- it to add in our attribute
    idx = -1
    while True:

        # -- Increment our counter regardless of what happens
        idx += 1

        if idx >= len(lines):
            break

        # -- Get the current line
        line = lines[idx]

        # -- Check if we need to start wrangling a parameter. By default
        # -- we add new parameters to the top
        if line.strip().startswith('Parameters'):
            redefined_lines.append(line)
            redefined_lines.append(lines[idx + 1])
            redefined_lines.append(
                '\t\t%s type:#%s ui:%s' % (attr_name, property_type, attr_name))
            idx += 1
            continue

        # -- Check if we need to start wrangling the rollout of a
        # -- parameter
        elif line.strip().lower().startswith('rollout'):
            redefined_lines.append(line)
            redefined_lines.append(lines[idx + 1])

            redefined_lines.append(
                f"\t\t{rollouts[property_type]}"
            )
            # redefined_lines.append('\t\tspinner %s "%s" type: #%s' % (
            #     attr_name, attr_name.title(), property_type))
            idx += 1
            continue

        else:
            redefined_lines.append(line)

    # -- We now stitch all the lines back together into a single string
    updated_block = '\n'.join(redefined_lines)

    # -- Finally, we either update the definition or add it depending
    # -- on whether its new or not
    if existing_definition:
        mxs.custAttributes.redefine(
            existing_definition,
            updated_block,
        )

    else:
        mxs.custAttributes.add(
            item,
            mxs.execute(updated_block),
        )


def _new_block_definition(block_name):
    """
    This will return a new block definition with the given block name

    :param block_name: Name of the block to define

    :return: str
    """
    return """
        myData = attributes "%s" version:1
        (
                                        -- Define the actual parameters
                                        Parameters main rollout:params
                                        (
                                        )

                                        -- Build the ui element
                                        rollout params "%s"
                                        (
                                        )
        )
        """ % (block_name, block_name)
