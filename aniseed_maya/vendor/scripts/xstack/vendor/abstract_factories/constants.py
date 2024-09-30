import logging


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger('abstract_factories')


class FactoryItemModes:

    Types = 'types'             # Store subclasses of abstract.
    Instances = 'instances'     # Store subclass instances of abstract.
