"""
xstack is a hierarchical component execution framework. Components as classes
which expose parameters (Requirements and Options) and implement a run method
which is exectuted.

The stack itself is a hierarchical list, where a component can be made a child
or parent of other components. The execution of the stack will always respect
the hierarchical order.

The stack can be triggered to execute the whole stack, all children of a particular
component (including itself) or just a single component.

Component classes are searched for through an abstract factory. You can declare
folder paths using the XSTACK_COMPONENT_PATHS environment variable, or you can
register component classes directly using any of the following:

```
    stack = Stack()
    stack.component_library.register_path(path)
    stack.component_library.register_module(path_to_py_file)
    stack.component_library.register_item(component_class)
```

Components can be super simple or quite complex depending on its needs. Here is an
example of a very simple Component:

```
    import xstack

    class MyComponent(xstack.Component):

        identifier = "MyCustomComponent"

        def run(self):
            print("Running in my custom component")
```

However, a component can also expose Requirements and Options. Any external code
or tools should only ever interact with the component through these two methods.

Requirements and Options are almost identical at a code level, but conceptually they
are quite different. A Requirement is considered to be an expected input needed in
order to evaluate the component whilst an Option is considered to be something that
alters how the end result my appear.

At a code level, the only different is that Requirements can be set to always
validate, and if they do not have a value set for them they will fail validation
during the building of the stack.

Here is an example of a component using options and requirements.

```
    class ResprayVehicle(xstack.Component):
        identifier = "respray_vehicle"

        def __init__(self, *args, **kwargs):
            super(ResprayVehicle, self).__init__(*args, **kwargs)

            self.declare_requirement(
                name="vehicle_instance",
                value=None,
                validate=True,
            )

            self.declare_option(
                name="color",
                value="orange",
            )

        def run(self):
            vehicle = self.requirement("vehicle_instance").get()
            color = self.option("color").get()

            print(f"respraying {vehicle} to be {color}")
```
In this example we see that we have exposed "vehicle_instance" as a requirement as
in this instance, we always need a vehicle to paint. We then expose the color as an
option with a default value.

Registering the components with the stack does not add them to the stack, it just
makes them available to the stack. You can add components to the stack using the
following syntax:

```
    stack = Stack()

    stack.add_component(
        label="Example",
        component_type="MyCustomComponentIdentifier",
    )
```

All components must inherit from xstack.Component, and therefore you will need to
provide your class with an identifier. This is the component_type.

Once a component has been added to the stack you can execute that stack using

    stack.build()

Stacks are hierarchical, so you can add multiple components and form a hierarchical
relationship, such as...

```
    stack = Stack()

    # -- Create three components, they will execute in the order
    # -- they are added by default
    component_a = stack.add_component(
        label="A",
        component_type="MyCustomComponent",
    )

    component_b = stack.add_component(
        label="B",
        component_type="MyCustomComponent",
    )

    component_c = stack.add_component(
        label="C",
        component_type="MyCustomComponent",
    )

    # -- At the moment, the order is completely flat, and we can choose
    # -- to change that order by doing this. Component A was added first, so it
    # -- would have a build position of zero by default. By setting it to 1 it means
    # -- that component b will now move to the top of the list, and component a will
    # -- execute after it
    stack.set_build_position(
        component_a,
        index=1,
    )

    # -- As well as changing the order, we can make it hierarchical. Lets make
    # -- component_a be a child of component_c. By doing this we can always guarantee
    # -- that component_a will always execute after component_c, even if component_c
    # -- is moved in the hierarchy.
    stack.set_build_position(
        component_a,
        parent=component_c,
    )
```
Whilst a hierarchical structure in this form can always be flattened - and is always
executed in a linear fashion, it can make for a much more intuitive format for
categories of executions.
"""
# -- Expose the stack. This is the main class of the module and handles the
# -- execution of the components
from .stack import Stack

# -- Expose the Component. All components must ultimately inherit from this class
from .component import Component

from . import address
from . import constants

__version__ = "0.1.15"