"""
This module is here to manage when the serialised data format
changes.

It will cycle through all the old formats, raising the format
structure up to the latest format.
"""

def to_latest(data: dict) -> dict:
    """
    This will raise the given data format to the latest format.

    Args:
        The data block to raise ot the latest format where required.

    Returns:
        The data in the latest format.
    """
    # -- If there is no data given then we do nothing but
    # -- return what we were given.
    if not data:
        return data

    # -- Cycle the converters in order, and each converter will
    # -- raise the format to the subsequent version.
    for converter in converters:
        data = converter(data)

    # -- Return the raised data format.
    return data


def original_to_galaxy(data):
    """
    This will convert data from the original format to the galaxy
    format. The galaxy format being the second format type.
    """
    # -- If this data is not in an original format we do not
    # -- need to convert.
    if data.get("format", None) != None:
        return data

    # -- We have an original data file, so we need to convert to
    # -- the galaxy format.
    new_data = dict(
        label=data["label"],
        tree=list(),
        additional_data=data.get("additional_data", dict())
    )

    def add_children(parent_block, build_order_data):
        for child_data in build_order_data["children"]:
            child_uuid = child_data["uuid"]
            child_component_data = data["components"][child_uuid]
            galaxy_child_data = _convert_block_to_galaxy(child_component_data)
            parent_block["children"].append(galaxy_child_data)
            # -- Add the children
            add_children(parent_block=galaxy_child_data, build_order_data=child_data)

    # -- Cycle the build order
    for build_order_item in data["build_order"]:
        uuid = build_order_item["uuid"]
        component_data = data["components"][uuid]
        galaxy_component_data = _convert_block_to_galaxy(component_data)

        # -- Add the new data
        new_data["tree"].append(galaxy_component_data)

        # -- Add the children
        add_children(galaxy_component_data, build_order_item)

    import json
    print(json.dumps(new_data, indent=4))
    return new_data

def _convert_block_to_galaxy(block):
    new_block = dict()
    new_block["label"] = block["label"]
    new_block["uuid"] = block["uuid"]
    new_block["component_type"] = block["component_type"]
    new_block["enabled"] = block["enabled"]
    new_block["options"] = dict()
    new_block["inputs"] = dict()
    new_block["children"] = list()

    for option in block["options"]:
        new_block["options"][option["name"]] = option["value"]

    for input_ in block["inputs"]:
        new_block["inputs"][input_["name"]] = input_["value"]

    return new_block


# -- All data is run through this converter list
converters = [
    original_to_galaxy,
]