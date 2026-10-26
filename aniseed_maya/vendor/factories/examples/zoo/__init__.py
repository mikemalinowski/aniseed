"""
This example represents a simple example of plugin usage without
expanding to functionality such as versioning. 

In this example we consider the Zoo object as being the central component
and all animals are then represented by plugins. This means you can always
add more animals to the zoo without having to alter key functionality within
the Zoo class.

Using this example code you can see how we can build some (albeit basic)
functionality of a zoo without hard coding in any animal types. In this way
we can extend the contents of zoo to include new animals without ever having
to touch the core zoo code. This is a fundamental principal of the plugin
architecture.

.. code-block:: python

    >>> import random
    >>> import factories.examples.zoo
    >>> 
    >>> # -- Create a zoo
    >>> zoo = factories.examples.zoo.Zoo()
    >>> 
    >>> # -- Add a random amount of animals to our zoo
    >>> for i in range(random.randrange(5, 20)):
    >>> zoo.add_animal(
    ...         random.choice(
    ...             zoo.appropriate_animals(),
    ...         ),
    ...     )
    >>> 
    >>> # -- Now print off the pens in the zoo
    >>> print(
    ...     'Our zoo has the following pens: %s' % (
    ...         '; '.join(
    ...             zoo.pens()
    ...         ),
    ...     )
    ... )
    >>> 
    >>> # -- Now lets visit each pen
    >>> for pen in zoo.pens():
    >>>     zoo.visit_pen(pen)
    >>> 
    >>> # -- Now we will cycle time, printing our animal count
    >>> day = 0
    >>> while zoo.animals():
    ...     print('Day %s' % day)
    ...     print('\tToday our zoo has %s animals' % len(zoo.animals()))
    ...     zoo.next_day()
    ...     day += 5
    >>> 
    >>> print('All our animals have died.')

In this example we can continually add new animals and the functionality - or
in this case the print statements - will increase without having to edit the
zoo itself.
You can give this a try simply by either dropping a new .py file into the
animals subfolder, or by adding a new animal class into one of the pre-existing
.py files.
"""
from .zoo import (
    Zoo,
    Animal,
)
