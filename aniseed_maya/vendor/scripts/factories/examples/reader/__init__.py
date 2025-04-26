"""
This example shows how we can utilise a plugin/factory pattern to 
make it easy to read file contents easily without having to hard code
readers into the core of our system.

Instead our core contains a factory, and we add plugins which are capable
of handling different file types. We can then ask each plugin whether the
plugin is able to parse the file - the first plugin to say yes is used and the
resulting data is returned.

You can try this example by running:

.. code-block:: python

    >>> from factories.examples import reader
    >>> 
    >>> # -- Instance a reader
    >>> data_reader = reader.DataReader()
    >>> 
    >>> # -- Read some data from an ini file
    >>> data = data_reader.read(reader.ini_path)
    >>> print(data)
    >>> 
    >>> # -- Now read some json data
    >>> data = data_reader.read(reader.json_path)
    >>> print(data)

"""
import os

from .core import(
    DataReader,
    ReaderPlugin,
)

# -- Some convience variables for testing this example
ini_path = os.path.join(
    os.path.dirname(__file__),
    'data',
    'data.ini',
)

json_path = os.path.join(
    os.path.dirname(__file__),
    'data',
    'data.json',
)
