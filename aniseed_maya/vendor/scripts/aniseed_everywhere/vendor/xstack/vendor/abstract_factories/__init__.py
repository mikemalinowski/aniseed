"""
Abstract Factories
==================

A collection of classes to support the Abstract Factory design pattern, providing a clear abstraction
layer for scalable data in dynamic environments.

This package includes the following main classes:

- `AbstractTypeFactory`: A factory class for instantiating abstract types (classes).
- `AbstractInstanceFactory`: A factory class for instantiating abstract instances (objects).

Both factories support registration of items directly, from modules, or from paths (filepaths or directories).
They also optionally support identifying items by name and version.

Practical Applications
----------------------

This package is particularly useful in scenarios where you need to manage and version various
components or behaviors, such as in content creation for film, TV, games, or rigging systems.

Example usage:

.. code-block:: python

    >>> from abstract_factories import AbstractTypeFactory, AbstractInstanceFactory
    >>>
    >>> class AbstractVehicle(object):
    ...     def __init__(self, make=None):
    ...         self.make = make
    ...
    ...     def start(self):
    ...         raise NotImplementedError()
    >>>
    >>> class Car(AbstractVehicle):
    ...     def start(self):
    ...         print('Vrooom...')
    >>>
    >>> # Type Factory
    >>> type_factory = AbstractTypeFactory(AbstractVehicle)
    >>> type_factory.register_item(Car)
    >>> assert type_factory.get('Car') is Car
    >>>
    >>> # Instance Factory
    >>> honda = Car('Honda')
    >>> instance_factory = AbstractInstanceFactory(AbstractVehicle, name_key='make')
    >>> instance_factory.register_item(honda)
    >>> assert instance_factory.get('Honda') is honda

"""
from .constants import LOGGER, FactoryItemModes

from .core import AbstractTypeFactory, AbstractInstanceFactory

"""
MIT License

Copyright (c) 2024 Lee Dunham leedunham@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""