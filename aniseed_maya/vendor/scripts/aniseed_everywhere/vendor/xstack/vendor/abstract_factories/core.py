import inspect
import types

from . import utils
from .constants import LOGGER, FactoryItemModes


# ------------------------------------------------------------------------------
class _AbstractFactory(object):
    """
    AbstractFactory for creating a 'loose' kind of abstract factories.
    Direct interaction with items is also possible, for convenience (whilst contradicting the nature
    of abstract design pattern).

    :param type abstract: Abstract type to use. Only subclasses of this type will be supported.
    :param list[str]|str|None paths: Path(s) to immediately find abstracts in. Search is recursive.
    :param list[ModuleType]|ModuleType|None modules: Module(s) to immediately find abstracts in. Search is surface level.
    :param str|Callable name_key: Item name identifier. Defaults to class name.
        If str given, will get the item's value for that attribute, property or method.
        If callable given, will expect the callable to accept the item as an argument and will use the returned value.
    :param str|Callable|None version_key: Item version identifier. Defaults to None, where versioning is not supported.
        If str given, will get the item's value for that attribute, property or method.
        If callable given, will expect the callable to accept the item as an argument and will use the returned value.
        If None given, versioning will not be supported (first registered item will only be used).
    :param bool unique_items_only: True to only store unique items, False to support non-unique.
        Uniqueness is a list membership test (list.__contains__).
    :param FactoryItemModes|str item_mode: Factory item mode. Determine they type of Item to store (types or instances).

    """

    def __init__(self,
                 abstract,
                 paths=None,
                 modules=None,
                 name_key='__name__',
                 version_key=None,
                 unique_items_only=True,
                 item_mode=FactoryItemModes.Types):
        if not inspect.isclass(abstract):
            raise TypeError('Abstract is required to be a class, received {}.'.format(type(abstract)))

        self._abstract = abstract

        self._name_key = name_key
        self._version_key = version_key
        self._unique_items_only = unique_items_only

        if item_mode not in (FactoryItemModes.Types, FactoryItemModes.Instances):
            raise ValueError(
                'FactoryMode expected to be Mode.Types ({}) or Mode.Instances ({}). '
                'Received {}.'.format(FactoryItemModes.Types, FactoryItemModes.Instances, self.item_mode)
            )

        self._item_mode = item_mode

        self._items = []

        if paths:
            for path in utils.ensure_iterable(paths):
                self.register_path(path)

        if modules:
            for module in utils.ensure_iterable(modules):
                self.register_module(module)

    # --------------------------------------------------------------------------
    def __repr__(self):
        return '{}(items={})'.format(type(self).__name__, len(self._items))

    # --------------------------------------------------------------------------
    @property
    def abstract(self):
        return self._abstract

    @property
    def unique_items_only(self):
        return self._unique_items_only

    @property
    def item_mode(self):
        return self._item_mode

    # --------------------------------------------------------------------------
    def _is_viable_item(self, item):
        if self.item_mode == FactoryItemModes.Types:
            if not inspect.isclass(item):
                return False
            elif item is self._abstract:
                return False
            elif not issubclass(item, self._abstract):
                return False

        else:
            if inspect.isclass(item):
                return False
            elif type(item) is self._abstract:
                return False
            elif not isinstance(item, self._abstract):
                return False

        return True

    def _item_is_registered(self, item):
        return item in self._items

    def _add_item(self, item):
        if self._is_viable_item(item):
            if not self.unique_items_only or not self._item_is_registered(item):
                LOGGER.debug('Adding item {}.'.format(item))
                self._items.append(item)
                return 1
        return 0

    def _remove_item(self, item):
        count = 0
        while self._item_is_registered(item):
            LOGGER.debug('Removing item {}.'.format(item))
            self._items.remove(item)
            count += 1
        return count

    # --------------------------------------------------------------------------
    def get_name(self, item):
        """
        Get the name value for <item>.
        :param type|object item: Abstract subclass to use.
        :rtype: str
        """
        if callable(self._name_key):
            name = self._name_key(item)

        # If using instances, defer missing name attributes to the class (ie __name__).
        elif self.item_mode == FactoryItemModes.Instances:
            name = getattr(item, self._name_key, getattr(type(item), self._name_key, None))
        else:
            name = getattr(item, self._name_key)
        return name() if callable(name) else name

    def get_version(self, item):
        """
        Get the version value for <item>, if available.
        :param type|object item: Abstract subclass to use.
        :rtype: int|float|None
        """
        version = None
        if not self._version_key:
            return version

        if callable(self._version_key):
            version = self._version_key(item)
        else:
            try:
                # If using instances, defer missing name attributes to the class.
                if self.item_mode == FactoryItemModes.Instances:
                    version = getattr(item, self._version_key, getattr(type(item), self._version_key, None))
                else:
                    version = getattr(item, self._version_key)
            except AttributeError as e:
                LOGGER.debug(
                    'Failed to get Version from {} using '
                    'version_identifier "{}" :: {}.'.format(item, self._version_key, e)
                )
        return version() if callable(version) else version

    def get(self, name, version=None):
        """
        Get the item matching <name> and <version>.
        If no version is provided, return the first item matching the given name.
        If no matching version is found, return None.
        :param str name: Name to get the item for.
        :param int|float|None version: Version to get. None to get latest.
        :rtype: type|object|None
        """
        name_matches = (
            item
            for item in self._items
            if self.get_name(item) == name
        )
        versions = {
            self.get_version(item): item
            for item in name_matches
        }
        if not versions:
            LOGGER.warning('{} has no matching items for {}.'.format(self, name))
            return None

        # Return latest version
        if version is None:
            return versions[max(versions)]

        return versions.get(version, None)

    def names(self):
        """
        Get all unique names for registered items.
        :rtype: list[str]
        """
        results = {
            self.get_name(item)
            for item in self._items
        }
        return list(results)

    def versions(self, name):
        """
        Get all versions the registered item using <name> (descending).
        :param str name: Plugin name to get versions for.
        :rtype: list[int|float|None]
        """
        # If we're not able to detect versions, then we don't try to.
        if not self._version_key:
            return []

        results = [
            self.get_version(item)
            for item in self._items
            if self.get_name(item) == name
        ]
        results.sort()
        return results

    def items(self):
        """
        Get the registered items.
        :rtype: list[type|object]
        """
        return list(self._items)

    def clear(self):
        """Clear the registered items."""
        del self._items[:]

    # --------------------------------------------------------------------------
    def register_item(self, item):
        """
        Register <item> with the factory.
        :param type|object item: Plugin to register with the factory.
        :return: True if <item> was registered successfully.
        :rtype: bool
        """
        if self._add_item(item):
            return True
        return False

    def deregister_item(self, item):
        """
        Deregister <item> from the factory.
        :param type|object item: Plugin to deregister with the factory.
        :return: True if <item> was deregistered successfully.
        :rtype: bool
        """
        if self._remove_item(item):
            return True
        return False

    def register_module(self, module):
        """
        Find and register any viable items found in <module>.
        If <module> is a package, submodules are not automatically imported or registered.
        ModuleTypes in <module> are not checked, only valid items.
        :param ModuleType module: Path to use.
        :return int: Number of registered items.
        """
        count = 0

        if not isinstance(module, types.ModuleType):
            return count

        for item in module.__dict__.values():
            count += self._add_item(item)

        return count

    def register_path(self, path, recursive=True):
        """
        Find and register any viable items found in <path>.
        :param str path: Path to use.
        :param bool recursive: True to search nested directories. False to only search immediate files.
        :return int: Number of registered items.
        """
        count = 0

        for filepath in utils.iter_python_files(path, recursive=recursive):
            module = utils.import_from_filepath(filepath)
            if module:
                count += self.register_module(module)

        return count


# ------------------------------------------------------------------------------
class AbstractTypeFactory(_AbstractFactory):
    """
    AbstractFactory for registering and accessing Types (classes).
    Useful when instances of registered types are not to be managed by the factory.

    :param type abstract: Abstract type to use. Only subclasses of this type will be supported.
    :param list[str]|str|None paths: Path(s) to immediately find abstracts in. Search is recursive.
    :param list[ModuleType]|ModuleType|None modules: Module(s) to immediately find abstracts in. Search is surface level.
    :param str|Callable name_key: Item name identifier. Defaults to class name.
        If str given, will get the item's value for that attribute, property or method.
        If callable given, will expect the callable to accept the item as an argument and will use the returned value.
    :param str|Callable|None version_key: Item version identifier. Defaults to None, where versioning is not supported.
        If str given, will get the item's value for that attribute, property or method.
        If callable given, will expect the callable to accept the item as an argument and will use the returned value.
        If None given, versioning will not be supported (first registered item will only be used).
    :param bool unique_items_only: True to only store unique items, False to support non-unique.
        Uniqueness is a list membership test (list.__contains__).

    """

    def __init__(self,
                 abstract,
                 paths=None,
                 modules=None,
                 name_key='__name__',
                 version_key=None,
                 unique_items_only=True):
        super(AbstractTypeFactory, self).__init__(
            abstract=abstract,
            paths=paths,
            modules=modules,
            name_key=name_key,
            version_key=version_key,
            unique_items_only=unique_items_only,
            item_mode=FactoryItemModes.Types,
        )


class AbstractInstanceFactory(_AbstractFactory):
    """
    AbstractFactory for registering and accessing instances.
    Useful when instances are needed to be managed by a factory. This could include a factory of factories for example.

    :param type abstract: Abstract type to use. Only subclasses of this type will be supported.
    :param list[str]|str|None paths: Path(s) to immediately find abstracts in. Search is recursive.
    :param list[ModuleType]|ModuleType|None modules: Module(s) to immediately find abstracts in. Search is surface level.
    :param str|Callable name_key: Item name identifier. Defaults to class name.
        If str given, will get the item's value for that attribute, property or method.
        If callable given, will expect the callable to accept the item as an argument and will use the returned value.
    :param str|Callable|None version_key: Item version identifier. Defaults to None, where versioning is not supported.
        If str given, will get the item's value for that attribute, property or method.
        If callable given, will expect the callable to accept the item as an argument and will use the returned value.
        If None given, versioning will not be supported (first registered item will only be used).
    :param bool unique_items_only: True to only store unique items, False to support non-unique.
        Uniqueness is a list membership test (list.__contains__).

    """

    def __init__(self,
                 abstract,
                 paths=None,
                 modules=None,
                 name_key='__name__',
                 version_key=None,
                 unique_items_only=True):
        super(AbstractInstanceFactory, self).__init__(
            abstract=abstract,
            paths=paths,
            modules=modules,
            name_key=name_key,
            version_key=version_key,
            unique_items_only=unique_items_only,
            item_mode=FactoryItemModes.Instances,
        )
