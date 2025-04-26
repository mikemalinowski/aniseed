# Aniseed (Version 2.*)

Aniseed is an application embedded (Maya) rigging tool. 

You can view a quick introduction video here:
https://youtu.be/rNy7F64nDiw

![Rig Image](aniseed_maya/documentation/images/aniseed_rig.png)

It takes a Joint-First approach whereby the user is expected to provide/draw the 
joint hierarchy (though some components expose functionality to do this for you!), and
you can then point the rig components to the joints you want that component to drive. 

Some components also expose functionality to generate manipulation guides to help 
manipulate joints in a more contextually relevant way (for example the spline spine), 
but it is an important and fundamental aspect of Aniseed that the skeleton is the 
authority. This is a purposeful choice, particularly as game engines require a rigger
to be very concious of the joint transforms and maintaining those transforms whilst
editing and extending rigs. 

Aniseed itself can be thought of as an execution stack, where the rigger can select
any components (or the rig as a whole) and choose to build that stack. Aniseed will then
proceed to execute each component in the order it is presented within the stack.

This approach makes aniseed incredibly flexible, as a component does not have to 
specifically drive joints, or could simply modify what has been been before it (a great
example of this is the space switching mechanism).

<span style="color:orangered">
IMPORTANTE NOTE: Aniseed is now at version two. For general users the major version
bump will not affect you (all pre-existing components, saves etc will continue to 
work). For developers, please ensure you read the note below and familiarise yourself
with aniseed_toolkit.
</span>

```markdown
Version 2.*

What is new in version 2?
The user flow and primary tool for rigging with aniseed has remained unchanged in 
version two. Its still focused entirely on the build stack, and all pre-existing
components work just as they did before. 

However, in the first iteration I found that there was too much "rigging logic" within
the aniseed module itself. Whilst aniseed -is- a rigging tool, it should be considered
a rigging framework with the flexibility for anyone to build rigs, or author components
to their own standards. Therefore the concept of what a control is, or how softik 
should work etc should not be part of the aniseed module, but instead be part of 
either components or utility functionality. 

That way a user or studio is able to take Aniseed as a bare bones framework and build 
out their own set of components specifically for their requirements, conventions and
standards.

Therefore in version 2.* the aniseed.utils has been removed completely - as this is 
where much of the rig assumptions were being made. Instead there is now a completely
new module called aniseed_toolkit. This contains "tools" which can be used within 
components to create controls, get upvector locations etc. But it is entirely the 
choice of the component author as to whether they use them or not. This means the 
core of aniseed stays free of convention-specific expansion.

```

# Installing

### Using the Drag & Drop Installer
To install aniseed within Maya download the release and unzip it into your downloads folder. 

Navigate into the unzipped folder and you will see a drag_drop_install.py file. Simply drag 
and drop that into the Maya viewport. This will start the installation process.

By default, the aniseed module will be installed in your maya's user location within the
module's folder. 

A video walkthrough of installing Aniseed can be found here:

https://youtu.be/hMnltJR2OWE


### Manually Installing
Aniseed is packaged as a *Maya Module*, therefore to manually install it you should
upzip the release, then place the .mod and the aniseed_maya folder within one of the 
MAYA_MODULE_PATH locations. 

# Launching

Aniseed will show in the main menu when you switch to the rigging workspace. To launch
the main tool, choose "Anseed Builder".

![Aniseed Menu](aniseed_maya/documentation/images/aniseed_menu.png)

All of aniseed is also fully exposed through Python. You can launch the Aniseed Builder
using the following python code

```python
import aniseed
aniseed.app.launch()
```

Note: All functionality available through the UI is also available in a headless/code-only
form as well.

# Getting Started with Aniseed

When you first launch Aniseed, it will look like the image shown below. This is what
you will see when there is no rig present within the scene. 


![Aniseed Menu](aniseed_maya/documentation/images/aniseed_no_rig.png)

The menu at the top allows you to create new rigs, switch between rigs in the scene
as well as exposing various bone mand shape manipulation tools. 

You can view a walkthrough of building your first rig in aniseed here:
https://youtu.be/oC2FzNgI_9o

## Creating a new Rig

Click File/New Rig

![Aniseed Menu](aniseed_maya/documentation/images/aniseed_create_new_rig_menu.png)

This will ask you  for a name for your rig. This is simply the name it will assign to
the rig node adn you can change this at any time. 

Your tool should now appear like this:

![Aniseed Menu](aniseed_maya/documentation/images/aniseed_created_new_rig.png)

"Rig : MyExampleRig" is our actual rig. All components we create will be a child of 
this in some form. The "Rig Configuration" is a special component - all rigs MUST have
a "Rig Configuration" component. By default Aniseed will create this for  you, however
if you're working in a studio pipeline where you dont want a rig configuration or you 
want to specify your own to be created automatically you can do this through the 
preferences (Edit/Preferences).

If you select the "Rig Configuration" component you will see that you are presented
with all its options. This allows you to tailor the conventions the tool will use when
building the rig. 

Components may expose any (or all) of the following:

### Requirements
These are fields that you are expected to fill in. They are typically mandatory for the
component to build and usually represent objects which that component needs.

### Options
These are fields that allow you to tailor the result of the component. This may allow 
you to change the behaviour of the component or the naming of the component etc. These
are usually predefined with default values.

### Outputs
These are fields which the selected component promises to populate as part of its 
execution. Typically with requirements (or any field that expects an object), you can 
chooes to either enter the objects name, or you can provide an "address" to an output
field. By using the address you're not hard coding the naming convention into your
setup. This is covered in more detail below.

## Adding Components & Building
This is the absolute minimum for a rig - if you right click the "Rig : MyExampleRig"
you will be presented with a context menu. From this menu you can select "Build", and 
that will execute (build) all the components declared in the rig. In this case, nothing 
will change in the scene, as the only component (the configuration component) does not 
actually do anything in of itself. However, you should see it go green to say that it 
was successfully executed.

Right click the Rig node again, and this time choose "Add Component". This will present
you with a dialog showing all the available components. 

![Aniseed Add Component](aniseed_maya/documentation/images/aniseed_add_component.png)

As well as showing you all the available components, you can click a component and 
see any help text that component offers. Some components will also expose some of their
options to you through this dialog as well. Its worth noting that any options you set
in this dialog can be changed later too.

## Example Workflow

To demonstrate this, select the "Mechanics : Two Bone IK" component and set the location
option to "md", then click "Add". This will add that component to the aniseed stack. Now
you can click that component and see that it requires a Parent as well as a Root joint
and a Tip joint (as shown below).

![Aniseed Add Component](aniseed_maya/documentation/images/aniseed_editing_a_component_01.png)

All three of the requirements for this component require "objects" (i.e, nodes in the 
scene). This field has two buttons next to it, the button highlighted in orange will 
fill the field with the selected object whilst the butten highlighted in yellow will 
select the object in the scene. Start by selecting the rig node in the outliner and then
clicking the "Set From Scene" button. This will place the nodes name into that field. 

Now draw three joints in a hierarchy within your scene. Select the first joint and fill
in the "Root Joint" field, then select the last joint and fill in the "Tip Joint" field.

Lets go ahead a test our rig - right click the "Rig : MyExample" section at the top of
the Aniseed tool and choose "Build/Build Rig". You should see the components go green 
and a set of IK controls built around your skeleton. 

This is the most simplistic way of using Aniseed, where you're working with the stack 
as a Linear Execution Stack (i.e, building all components from top to bottom).

## Iterative Building Workflow

In reality, when we build rigs we rarely get things exactly as we want them first time. 
Quite often we will want to rebuild our rig, then change some settings or extend it 
further and rebuild it again. This process is usually repeated a lot during the lifespan
of a rig in production - and it is why dedicated rigging tools such as Aniseed exist. 

Therefore, simply executing all components from top to bottom is not incredibly 
efficient. If we take the example above, if we hit build again, we would end up with 
another set of IK controls for each time we built our rig. Therefore it would require 
the rigger to clean the scene up each time. 

This is why Aniseed allows you to execute "sub sections" of a stack rather than the 
whole stack. This way you can group your stack its different sets of functionality
which can be invoked for different purposes. 

You can see this in practice if you right click the "Rig Configuration" item and choose
"Create Initial Component Structure". This initial rig structure is intended as a 
"good practice starting point". As you can see in the image below, it defines an inital 
rig structure - this just creates a series of group nodes to help keep our skeleton, 
geometry and controls seperate from one another. 

We then have a "Make Rig Editable" section. This has nodes which specifically look over
the control rig, store shape information and then delete the control rig. 

The "Build Control Rig" does what it says on the tin. This section creates a global 
control root, re-applies control shapes and applies control colours. 

![Aniseed Add Component](aniseed_maya/documentation/images/aniseed_basic_iterative_stack.png)


# Aniseed Toolkit

The Aniseed Toolkit is both a user facing tool and a code factory which can be called
and used by components or other tools. 

You can launch the user facing tool through either the Aniseed menu or through the 
Tools menu within aniseed. This will present you with a list of available tools which 
you can double click to instigate. To see documentation relating to the tool simply
hover your cursor over the tool - the tooltip will show the documentation.

There are (currently) two classifications of tools which you can switch between. These
are:

* Animation
![Aniseed Toolkit - Animation](aniseed_maya/documentation/images/toolkit_animation.png)

* Rigging
![Aniseed Toolkit - Rigging](aniseed_maya/documentation/images/toolkit_rigging.png)

# Using Aniseed 

This area of the documentation is still to be completed. But there are some video walkthrough guides:

Part00 Installing Aniseed :
https://youtu.be/hMnltJR2OWE

Part01 The Principals Of Aniseed :
https://youtu.be/krWXOA1ZJwA

Part02 Creating An Iterative Execution Stack :
https://youtu.be/xXWkc2qq0YU

Part03 Working With Joints PartA :
https://youtu.be/tdYFYp4Ynvo

Part03 Working With Joints PartB :
https://youtu.be/7ZX-4sF7-wk

Part04 Creating A Biped :
https://youtu.be/Id81lMvX_RI

Part05 Modelling And Rigging Poses :
https://youtu.be/lawT3pwYmHs

Part06 Space Switches :
https://youtu.be/Ms6fq9Sw11I

Part07 Saving And Loading Rigs :
https://youtu.be/hnETOU7BY9g

Part08 Writing Your Own Components :
https://youtu.be/QdxxNme4GhQ

Other Videos:

Using Attribute Linking : https://www.youtube.com/watch?v=Dq4BQHALcEk&feature=youtu.be


# Coding With Aniseed

If you want to add your own rigging components you can either:

* Place your components within the aniseed/components folder (or subfolder). This
is useful for small development studios or individuals.


* Place your components in a folder and declare that folder path in an environment
variable called ANISEED_RIG_COMPONENT_PATHS. This option is particularly useful
for larger development studio's whom have a requirement to keep open source code
seperate from their internally developed code.

## Aniseed Classes

The Rig class is the one you will typically use as the entrypoint to working with Aniseed
at a code level. The rig class gives a pointer to the node representing the rig as well as 
containing all the information about the components that form to make up the rigs execution. 

Crucially it also gives access to the rigs configuration - which is covered below.

You can create a new rig using the following code. This will create a rig called MyNewRig
in the scene. It will expose all the components that are available to aniseed out the box.

```python
import aniseed

new_rig = aniseed.MayaRig(label="MyNewRig")
```

Alternatively, if there is already a rig in the scene, assuming the rig transform is called
MyNewRig, you can do...

```python
import aniseed

new_rig = aniseed.MayaRig(host="MyNewRig")
```

Now that you have a rig class instanced, you can start adding components to your rig. In this
example we add some basic components to demonstrate. 

```python
new_component = new_rig.add_component(
    component_type="simple_fk",
)
```


As well as just adding the component, we can define options and requirement values at the same
time as adding the component, like so:

```python
new_component = new_rig.add_component(
    component_type="simple_fk",
    requirements={
        "Parent": "Foobar",
        "Joints To Drive": ["A", "B", "C"],
    },
    options={
        "Label": "Head",
    }
)
```

The approach above allows you to specify values at the time of the components creation. However, 
you can also set these values directly on the component after creation too. This is done like this:

```python
new_component = new_rig.add_component(
    component_type="simple_fk",
)
new_component.requirement("Parent").set("Foobar")
new_component.requirement("Joints To Drive").set(["A", "B", "C"])
new_component.option("Label").set("Head")
```

The result between these two examples is exactly the same.

Now that we have components in our rig, we can build it. To do this is simply:

```python
new_rig.build()
```

That will run through all the components in the rig and execute them.

Note that a rig must **ALWAYS** have a Rig Configuration component added to it in 
order to build. A RigConfiguration is nothing more than a component that exposes a
specific set of parameters and functions that allow a user to tailor how a rig is
built. 

Aniseed comes packaged with a rig configuration which is designed to be flexible, 
however if you find that you need something more, you can always subclass the RigConfiguration
component and implement your own. This is explained below.

Everything you do through the UI can be scripted. Here is an example of building a
rig with spine and legs

```python
import aniseed

# -- Start by create a new rig
rig = aniseed.MayaRig(label="ExampleRig")

# -- Add a rig configuration to the rig
rig.add_component(
    component_type="Rig Configuration : Standard",
    label="Configuration",
)

# -- The rig configuration has a custom function to 
# -- allow for a basic rig structure to be made
rig.config().create_component_structure()

# -- Now add a spine component as a child of the global srt component. Note
# -- that the global srt component is generated for us from the rig
# -- configuration
spine_component = rig.add_component(
    component_type="Standard : Spline Spine",
    label="Spine",
    parent=rig.find("Global SRT"),
)

# -- Rather than build the skeleton manually, we will let the component
# -- do this for us
spine_component.user_func_build_skeleton(joint_count=6)

# -- In this example, we're setting the parent attribute
# -- to the address of the main control of the srt. We use the address
# -- rather than a hard coded name to allow for naming flexibility
spine_component.requirement("Parent").set(
    rig.find("Global SRT").output("Main Control").address()
)

# -- Now we add the left leg component. Note that in this example we're
# -- specifying the parent requirement at the time of adding it rather
# -- that setting the attribute after the fact
left_leg_component = rig.add_component(
    component_type="Standard : Leg",
    label="Leg LF",
    parent=spine_component,
    options={"Location": "lf"},
    requirements={
        "Parent": spine_component.output("Root Transform").address()
    }
)

# -- Now we create the skeleton. By default this will also generate 
# -- a guide for us. Both the option of creating a skeleton and a guide
# -- is specific to any given component. 
left_leg_component.user_func_create_skeleton(
    parent=spine_component.requirement("Root Joint").get(),
    upper_twist_count=3,
    lower_twist_count=3,
)

# -- Now we do exactly the same for the right leg. Note that the leg component
# -- will mirror itself if its build with the right side set. This is a logic
# -- choice in the component itself rather than a framework choice. 
right_leg_component = rig.add_component(
    component_type="Standard : Leg",
    label="Leg RT",
    parent=spine_component,
    options={"Location": "rt"},
    requirements={
        "Parent": spine_component.output("Root Transform").address()
    }
)

right_leg_component.user_func_create_skeleton(
    parent=spine_component.requirement("Root Joint").get(),
    upper_twist_count=3,
    lower_twist_count=3,
)

# -- Finally, because all the components we have added in this example use
# -- guides, we need to remove them before we build the rig. 
spine_component.user_func_remove_guide()
left_leg_component.user_func_remove_guide()
right_leg_component.user_func_remove_guide()

# -- Finally, we build the control rig. 
rig.build()

# -- At any point we can put the rig back into an editable state by doing
# -- the following
editable_stack = rig.find("Make Rig Editable")
rig.build(build_below=editable_stack)
```

## Adding Components

Components are where most of the code exists within any Aniseed deployment. It is 
utlimately where all your rig building code resides. Out the box aniseed comes with 
a library of components that will hopefully allow you to create a variety of rigs
but you can also extend it with your own additional components as well.

To do this, you will need to subclass the aniseed.RigComponent class. Here is a 
documented example:

```python

import aniseed
import maya.cmds as mc


# -- The name of the class is not important but it must inherit
# -- from the RigComponent class
class MyCustomComponent(aniseed.RigComponent):
    
    # -- All components require a unique identifier string
    # -- to allow it to be dinstinguishable from other 
    # -- components
    identifier = "my_custom_component_example"
    
    # -- We need to re-implement the __init__. This is where we declare
    # -- any options and requirements the component should have
    def __init__(self, *args, **kwargs):
        super(MyCustomComponent, self).__init__(*args, **kwargs)

        # -- Here we are defining a requirement. A requirement is considered
        # -- to be an input that this component needs fullfilling by the user
        # -- in order to execute.
        # -- Note that we can set validate to either true or false. If it is
        # -- true then the requirement will be tested before execution to ensure
        # -- that the user has a set a value. 
        self.declare_requirement(
            name="Parent Node",
            value=None,
            validate=True,
        )

        # -- Now we will declare an option. Options are much like requirements
        # -- except they are not typically mandatory and serve more to allow a
        # -- user to tailor the execution of the component
        self.declare_option(
            name="Name Prefix",
            value=""
        )
    
    # -- The run function is what is executed when a rig is built
    def run(self):
        
        # -- In our example we are just going to create a transform 
        # -- node and name and parent it to demonstrate how we access
        # -- the properties we have declared
        
        # -- Notice that when we access the requirement, we use .get()
        # -- in order to get the actual value from the property
        parent = self.requirement("Parent Node").get()
        
        # -- We now do the same for the options
        prefix = self.option("Name Prefix").get()
        
        # -- At this point we're now just running vanilla maya code. 
        node = mc.createNode("transform")
        
        mc.parent(
            node,
            parent,
        )

        mc.rename(
            node,
            prefix + "MyNode",
        )
```

By default, the aniseed application will attempt to display requirements and options
in the UI based on the variable type that they are set to. For instance, if you set 
a requirement as a string it will show it as a text field in the ui.

However, quite often we want to display our options in richer ways. For instance, whilst
an object might be a string, it is useful to have a mechanism to allow the user to set it
from the current selection, or to select the object.

This is done through the `option_widget` and `requirement_widget` functions which can
be re-implemented. Here is an example:

```python

import aniseed
import PySide6


# -- The name of the class is not important but it must inherit
# -- from the RigComponent class
class MyCustomComponent(aniseed.RigComponent):

class MyCustomWidget()
```

That is a simple example of implementing a custom component in aniseed. In order to 
utilise your component it will need to be placed in a location where aniseed is set
to search. 

If you store your components outside of the aniseed base location (which is recommended)
then you will need to pass your component folder to the rig at time of instancing using

```python
import aniseed

rig = aniseed.MayaRig(
    label="foo",
    component_paths=["my/path/to/my/components"]
)
```

Alternatively you can add your component path to the following environment variable:
`ANISEED_RIG_COMPONENT_PATHS`

For studio deployments it is strongly recommended to use the environment variable approach 
and to keep your custom components seperate from the aniseed deployment.

## Aniseed Toolkit Code

When using tools within code (i.e, in components or your own tools), you can simply
use this syntax to instigate it:

```python
import aniseed_toolkit

distance = aniseed_toolkit.run("Get Distance Between", node_a, node_b)
```
This will run the `Get Distance Between` tool with `node_a` and `node_b` being
passed as arguments. 

You can find a list of tools here:
[asd](asd)

To write a tool, you simply inherit from the `aniseed_toolkit.Tool` class and 
implement the run function with whatever arguments you require. Its highly recommended
that you use keyword arguments (due to the blind nature of tools), and make them typed.

```python
import aniseed_toolkit
import maya.cmds as mc

class MyExampleTool(aniseed_toolkit.Tool):
    
    identifier = "Move By 5"
    
    def run(self, node: str = "", axis: str = "x") -> float:
        """
        Simple example to show how a tool can be constructed. This tool will take
        the given node and move it on a specific axis 5 units. 
        
        Args:
            node: The node to move
            axis: the axis in which to move it (x, y, z)
        
        Returns:
            The final value of the attribute
        """
        attribute = f"{node}.translate{axis.upper()}"
        mc.setAttr(
            attribute,
            mc.getAttr(attribute) + 5,
        )
        return mc.getAttr(attribute)
```

It is worth noting that it is recommended to use google style docstrings for the tool
if you plan to use the auto generation of documentation, as this specifically expects
that style for parsing.

We can then call this tool in the same way as the example above shown. For example:

```python
import aniseed_toolkit
import maya.cmds as mc

my_node = mc.createNode("transform")
distance = aniseed_toolkit.run("Move By 5", node=my_node, axis="y")
```

## Utils 

Rigging code is typically filled with repetative tasks. Aniseed comes with some utility
functionality you may find useful. However, its worth noting that there is no requirement
to use any of the utility functionality
