# Table of Contents

- [Controls](#Controls)

  - [`Get By Location`](#Get-By-Location)

  - [`Get Opposites`](#Get-Opposites)

  - [`Select Alternate Controls`](#Select-Alternate-Controls)

  - [`Select Controls`](#Select-Controls)

  - [`Select Controls By Location`](#Select-Controls-By-Location)

  - [`Select Filtered Controls`](#Select-Filtered-Controls)

  - [`Select Opposite`](#Select-Opposite)

  - [`Zero Rig`](#Zero-Rig)

  - [`Zero Selection`](#Zero-Selection)

- [Creation](#Creation)

  - [`Create Guide`](#Create-Guide)

  - [`Create Guide Tween`](#Create-Guide-Tween)

- [Joints](#Joints)

  - [`Copy Joint Attributes`](#Copy-Joint-Attributes)

  - [`Deserialise Nodes From Dict`](#Deserialise-Nodes-From-Dict)

  - [`Get Chain Length`](#Get-Chain-Length)

  - [`Get Joint Writer Supported Types`](#Get-Joint-Writer-Supported-Types)

  - [`Get Joints Between`](#Get-Joints-Between)

  - [`Load Joints File`](#Load-Joints-File)

  - [`Move Joint Orients to Rotation`](#Move-Joint-Orients-to-Rotation)

  - [`Move Joint Rotations To Orients`](#Move-Joint-Rotations-To-Orients)

  - [`Replicate Chain`](#Replicate-Chain)

  - [`Replicate Entire Chain`](#Replicate-Entire-Chain)

  - [`Replicate Joint`](#Replicate-Joint)

  - [`Reverse Chain`](#Reverse-Chain)

  - [`Roll Joints`](#Roll-Joints)

  - [`Serialise Nodes To Dict`](#Serialise-Nodes-To-Dict)

  - [`Write Joints File`](#Write-Joints-File)

- [Math](#Math)

  - [`Direction Between`](#Direction-Between)

  - [`Distance Between`](#Distance-Between)

  - [`Get Factor Between`](#Get-Factor-Between)

- [Misc](#Misc)

  - [`Get MObject`](#Get-MObject)

  - [`MObject Name`](#MObject-Name)

- [Pinning](#Pinning)

  - [`Create Pins`](#Create-Pins)

  - [`Get Joint From Pin`](#Get-Joint-From-Pin)

  - [`Get Pin From Node`](#Get-Pin-From-Node)

  - [`Is Pinned`](#Is-Pinned)

  - [`Pin Hierarchy`](#Pin-Hierarchy)

  - [`Remove All Pins`](#Remove-All-Pins)

  - [`Remove Pins`](#Remove-Pins)

- [Posing](#Posing)

  - [`Pose Copy`](#Pose-Copy)

  - [`Pose Copy (WorldSpace)`](#Pose-Copy-(WorldSpace))

  - [`Pose Paste`](#Pose-Paste)

  - [`Pose Paste (WorldSpace)`](#Pose-Paste-(WorldSpace))

- [Rigging](#Rigging)

  - [`Calculate Four Spline Positions From Joints`](#Calculate-Four-Spline-Positions-From-Joints)

  - [`Create Soft Ik`](#Create-Soft-Ik)

  - [`Create Spline Setup`](#Create-Spline-Setup)

  - [`Create Twist Setup`](#Create-Twist-Setup)

  - [`Create Two Bone IKFK`](#Create-Two-Bone-IKFK)

- [Selection](#Selection)

  - [`Get By Location`](#Get-By-Location)

  - [`Get Opposites`](#Get-Opposites)

  - [`Select Alternate Controls`](#Select-Alternate-Controls)

  - [`Select Controls`](#Select-Controls)

  - [`Select Controls By Location`](#Select-Controls-By-Location)

  - [`Select Filtered Controls`](#Select-Filtered-Controls)

  - [`Select Opposite`](#Select-Opposite)

  - [`Zero Rig`](#Zero-Rig)

  - [`Zero Selection`](#Zero-Selection)

- [Shapes](#Shapes)

  - [`Apply Shape`](#Apply-Shape)

  - [`Apply Shape Color`](#Apply-Shape-Color)

  - [`Apply Shape Color Prompt`](#Apply-Shape-Color-Prompt)

  - [`Combine Shapes`](#Combine-Shapes)

  - [`Copy Shape`](#Copy-Shape)

  - [`Get Shape List`](#Get-Shape-List)

  - [`Get Up Axis Shape Rotation Vector`](#Get-Up-Axis-Shape-Rotation-Vector)

  - [`Load Rig Control Shapes From File`](#Load-Rig-Control-Shapes-From-File)

  - [`Mirror Across`](#Mirror-Across)

  - [`Mirror All Shapes Across`](#Mirror-All-Shapes-Across)

  - [`Mirror Shape`](#Mirror-Shape)

  - [`Offset Shapes`](#Offset-Shapes)

  - [`Paste Shape`](#Paste-Shape)

  - [`Read Shape From File`](#Read-Shape-From-File)

  - [`Read Shape From Node`](#Read-Shape-From-Node)

  - [`Rotate Shape From Up Axis`](#Rotate-Shape-From-Up-Axis)

  - [`Rotate Shapes`](#Rotate-Shapes)

  - [`Save All Rig Control Shapes`](#Save-All-Rig-Control-Shapes)

  - [`Save Shape`](#Save-Shape)

  - [`Scale Shapes`](#Scale-Shapes)

  - [`Select Shapes`](#Select-Shapes)

  - [`Snap Shape To Node Transform`](#Snap-Shape-To-Node-Transform)

- [Skinning](#Skinning)

  - [`Copy Skin To Unskinned Meshes`](#Copy-Skin-To-Unskinned-Meshes)

  - [`Disconnect All Skins`](#Disconnect-All-Skins)

  - [`Interp : Apply Interpolation`](#Interp-:-Apply-Interpolation)

  - [`Interp : Set Target A Weights`](#Interp-:-Set-Target-A-Weights)

  - [`Interp : Set Target B Weights`](#Interp-:-Set-Target-B-Weights)

  - [`Load Skin File`](#Load-Skin-File)

  - [`Reconnect All Skins`](#Reconnect-All-Skins)

  - [`Save Skin File`](#Save-Skin-File)

- [Transforms](#Transforms)

  - [``](#)

  - [`Align Bones For Ik`](#Align-Bones-For-Ik)

  - [`Apply Relative Matrix`](#Apply-Relative-Matrix)

  - [`Calculate Upvector Position`](#Calculate-Upvector-Position)

  - [`Clear Constraints`](#Clear-Constraints)

  - [`Create Locator At Center`](#Create-Locator-At-Center)

  - [`Get Chain Facing Direction`](#Get-Chain-Facing-Direction)

  - [`Get Direction Class`](#Get-Direction-Class)

  - [`Get Relative Matrix`](#Get-Relative-Matrix)

  - [`Global Mirror`](#Global-Mirror)

  - [`Invert Translation`](#Invert-Translation)

  - [`Position Between`](#Position-Between)

- [Visibility](#Visibility)

  - [`Create Aim Hierarchy`](#Create-Aim-Hierarchy)

  - [`Create Blend Chain`](#Create-Blend-Chain)

  - [`Find All Children With Tag`](#Find-All-Children-With-Tag)

  - [`Find All With Tag`](#Find-All-With-Tag)

  - [`Find First Child With Tag`](#Find-First-Child-With-Tag)

  - [`Get Tag Data`](#Get-Tag-Data)

  - [`Has Tag`](#Has-Tag)

  - [`Hide Nodes`](#Hide-Nodes)

  - [`Show Nodes`](#Show-Nodes)

  - [`Tag Node`](#Tag-Node)

# Controls

--------------------

### Get By Location

Identifier : `Get By Location`

#### Overview

 This will return the opposite controls for the given controls

#### Args

- `controls`: List of controls to get the opposites for. If none are given then the selection will be used.

#### Returns



--------------------

### Get Opposites

Identifier : `Get Opposites`

#### Overview

 This will return the opposite controls for the given controls

#### Args

- `controls`: List of controls to get the opposites for. If none are given then the selection will be used.

#### Returns



--------------------

### Select Alternate Controls

Identifier : `Select Alternate Controls`

#### Overview

 This will zero out all the animatable channels for the given node

#### Args

- `node`(*str*): The node to zero out (reset)

#### Returns

- None

--------------------

### Select Controls

Identifier : `Select Controls`

#### Overview

 This will select all the controls for the given rig (if there is a selection or all the controls in all rigs if there is not a selection).

#### Args

#### Returns



--------------------

### Select Controls By Location

Identifier : `Select Controls By Location`

#### Overview

 This will zero out all the animatable channels for the given node

#### Args

- `node`(*str*): The node to zero out (reset)

#### Returns

- None

--------------------

### Select Filtered Controls

Identifier : `Select Filtered Controls`

#### Overview

 This will zero out all the animatable channels for the given node

#### Args

- `node`(*str*): The node to zero out (reset)

#### Returns

- None

--------------------

### Select Opposite

Identifier : `Select Opposite`

#### Overview

 This will select controls of the opposing location (side)

#### Args

#### Returns



--------------------

### Zero Rig

Identifier : `Zero Rig`

#### Overview

 This will zero out all the animatable channels for the selected controls.

#### Args

- `key_on_reset (bool, optional)`: If True, the objects will be keyed after being reset

#### Returns

- None

--------------------

### Zero Selection

Identifier : `Zero Selection`

#### Overview

 This will zero out all the animatable channels for the selected controls.

#### Args

- `key_on_reset (bool, optional)`: If True, the objects will be keyed after being reset

#### Returns

- None

# Creation

--------------------

### Create Guide

Identifier : `Create Guide`

#### Overview

 Creates a simple guide control object to transform a joint

#### Args

- `joint`(*str*): The joint to drive with this guide

- `parent`: The parent of this guide

- `position_only`(*bool*): If True, the joint will only be position constrained to the guide control

- `shape`(*str*): The shape of the guide control (accessible via aniseed_toolkit/_resources/shapes

- `scale`(*float*): The scale of the guide control shape

- `link_to`: If given, a guide line will be drawn between this node and the linked node

#### Returns

- Name of the guide control node

--------------------

### Create Guide Tween

Identifier : `Create Guide Tween`

#### Overview

 Creates a blended constraint

#### Args

#### Returns



# Joints

--------------------

### Copy Joint Attributes

Identifier : `Copy Joint Attributes`

#### Overview

 Copies all the transform and joint specific attribute data from the first given joint to the second.

#### Args

- `from_this`(*str*): The joint to copy values from

- `to_this`(*str*): The joint to copy values to

- `link`(*bool*): If true, instead of setting values, the attributes will be connected.

#### Returns

- None

--------------------

### Deserialise Nodes From Dict

Identifier : `Deserialise Nodes From Dict`

#### Overview

 This will take a dictionary (in the format returned by SerialiseNodesToDict) and generate nodes based on that description.

#### Args

- `root_parent`(*str*): The node the newly created structure should reside under

- `dataset`: The dictionary of data

- `apply_names`(*bool*): Whether to apply the names to the created nodes

- `invert`(*bool*): Whether translations should be inverted or not (useful when mirroring)

- `worldspace_root`(*bool*): If true, the values will be applied in worldspace

#### Returns

- Dictionary where the key is the name as defined in the data and the value

--------------------

### Get Chain Length

Identifier : `Get Chain Length`

#### Overview

 This will calculate the length of the chain in total.

#### Args

- `start`(*str*): The joint from which to start measuring

- `end`(*str*): The joint to which measuring should end

- `log_result`(*bool*): If true, the result should be printed

#### Returns

- The total length of all the bones in the chain

--------------------

### Get Joint Writer Supported Types

Identifier : `Get Joint Writer Supported Types`

#### Overview

 This will return a list of supported node types which are supported in the joint writing tools.

#### Args

#### Returns

- List of node types which are supported

--------------------

### Get Joints Between

Identifier : `Get Joints Between`

#### Overview

 This will return all the joints in between the start and end joints including the start and end joints. Only joints that are directly in the relationship chain between these joints will be included.

#### Args

- `start`(*str*): The highest level joint to search from

- `end`(*str*): The lowest level joint to search from.

- `Return:`: Return: List of joints

#### Returns



--------------------

### Load Joints File

Identifier : `Load Joints File`

#### Overview

 This will parse the given json file and generate the structure defined within it.

#### Args

- `root_parent`(*str*): The node the newly created structure should reside under

- `filepath`(*str*): The absolute path to the json file

- `apply_names`(*bool*): Whether to apply the names to the created nodes

- `invert`(*bool*): Whether translations should be inverted or not (useful when mirroring)

- `worldspace_root`(*bool*): If false, the root of the structure will be matched in worldspace

#### Returns

- Dictionary where the key is the name as defined in the data and the value

--------------------

### Move Joint Orients to Rotation

Identifier : `Move Joint Orients to Rotation`

#### Overview

 Moves the values from the joint orient of the node to the rotation whilst retaining the transform of the node.

#### Args

- `joints`: The joint to alter

#### Returns

- None

--------------------

### Move Joint Rotations To Orients

Identifier : `Move Joint Rotations To Orients`

#### Overview

 Moves the rotations on the given joints to the joint orients attributes (zeroing the rotations).

#### Args

- `joints`: List of joints to move the rotation attributes for

#### Returns

- None

--------------------

### Replicate Chain

Identifier : `Replicate Chain`

#### Overview

 Given a start and end joint, this will replicate the joint chain between them exactly - ensuring that all joint attributes are correctly replicated.

#### Args

- `from_this`(*str*): Joint from which to start duplicating

- `to_this`(*str*): Joint to which the duplicating should stop. Only joints between this and from_this will be replicated.

- `parent`(*str*): The node the replicated chain should be parented under

- `world`(*bool*): Whether to apply the first replicated chains transform in worldspace, otherwise it will be given the same local space attribute data.

- `replacements`: A dictionary of replacements to apply to the duplicated joint names.

#### Returns

- List of new joints

--------------------

### Replicate Entire Chain

Identifier : `Replicate Entire Chain`

#### Overview

 Given a starting point, this will replicate (duplicate) the entire joint chain. It allows for you to specify the parent for the duplicated chain, as well as optionally attribute-link it.

#### Args

- `joint_root`(*str*): The joint from which to duplicate from

- `parent`(*str*): The parent node for the duplicated chain

- `link`(*bool*): If true, then the attributes will be linked together

- `copy_local_name`(*bool*): If true, then the name of the joint being duplicated will be used as the name of the joint being created (minus namespace)

#### Returns

- The newly duplicated root joint

--------------------

### Replicate Joint

Identifier : `Replicate Joint`

#### Overview

 Replicates an individual joint and makes it a child of the given parent.

#### Args

- `joint`(*str*): Joint to replicate

- `parent`(*str*): Node to parent the new node under

- `link`(*bool*): If True then the attributes of the initial joint will be used as driving connections to this joint.

- `copy_local_name`(*bool*): If true, the joint will be renamed to match that of the joint being copied (ignoring namespaces)

#### Returns

- The name of the created joint

--------------------

### Reverse Chain

Identifier : `Reverse Chain`

#### Overview

 Reverses the hierarchy of the joint chain.

#### Args

- `joints`: List of joints in the chain to reverse

#### Returns

- The joint chain in its new order

--------------------

### Roll Joints

Identifier : `Roll Joints`

#### Overview

 Moves the rotations on the given joints to the joint orients attributes (zeroing the rotations).

#### Args

- `joints`: List of joints to move the rotation attributes for

#### Returns

- None

--------------------

### Serialise Nodes To Dict

Identifier : `Serialise Nodes To Dict`

#### Overview

 This will store the given nodes and their attributes to a dictionary

#### Args

- `nodes`(*type*): List of nodes to serialise

#### Returns

- dict of the dataset in the format supported by the joint writing tools

--------------------

### Write Joints File

Identifier : `Write Joints File`

#### Overview

 This will take the given nodes and serialise them to a json file and save that json file to the given filepath.

#### Args

- `nodes`: List of nodes to serialise

- `filepath`: The filepath to save the json file

#### Returns

- None

# Math

--------------------

### Direction Between

Identifier : `Direction Between`

#### Overview

 This will return a direction vector (normalised vector) between the two nodes

#### Args

- `node_a`(*str*): The object to measure from

- `node_b`(*str*): The object to measure to

- `print_result`(*bool*): If true, the result will be printed

#### Returns

- The direction vector between the two nodes

--------------------

### Distance Between

Identifier : `Distance Between`

#### Overview

 Returns the distance between two objects

#### Args

- `node_a`(*str*): The object to measure from

- `node_b`(*str*): The object to measure to

- `print_result`(*bool*): If true, the result will be printed

#### Returns

- The distance between two objects

--------------------

### Get Factor Between

Identifier : `Get Factor Between`

#### Overview

 This will return a factor (between zero and one) for how close the given node is between the from_this and to_this nodes.

#### Args

- `node`(*str*): The node to monitor

- `from_this`(*str*): The first node to compare to

- `to_this`(*str*): The second node to compare to

#### Returns

- The factor for how close the given node is between the from_this and to_this

# Misc

--------------------

### Get MObject

Identifier : `Get MObject`

#### Overview

 Given the name of a node, this will return the MObject representation. This means we can track the node easily without having to worry about name changes.

#### Args

- `name`(*str*): Name of the node to get a pointer to

#### Returns

- MObject reference

--------------------

### MObject Name

Identifier : `MObject Name`

#### Overview

 This will return the name of the MObject pointer

#### Args

- `mobject`: MObject pointer

#### Returns

- Name of the node

# Pinning

--------------------

### Create Pins

Identifier : `Create Pins`

#### Overview

 This will create a pin for the given joints. Pins are used to lock the transforms of a joint to a controller which is typically in worldspace. This makes it easy to manipulate joints without altering their children.

#### Args

- `joints`: List of joints to pin

#### Returns

- List of created pins.

--------------------

### Get Joint From Pin

Identifier : `Get Joint From Pin`

#### Overview

 This will attempt to find the joint from a pin setup. If the joint itself is given, the same joint will be returned.

#### Args

- `item`(*str*): The node to inspect

#### Returns

- The joint being pinned (or None if no joint was found)

--------------------

### Get Pin From Node

Identifier : `Get Pin From Node`

#### Overview

 This will return the pin control for the given node. If the pin control was the item given it will just be returned.

#### Args

- `item`(*str*): The item to find the pin for

#### Returns

- The pin control

--------------------

### Is Pinned

Identifier : `Is Pinned`

#### Overview

 This will test whether the given item is already pinned or not.

#### Args

- `joint`: The item to test

#### Returns

- True if the joint is pinned

--------------------

### Pin Hierarchy

Identifier : `Pin Hierarchy`

#### Overview

 This will pin all joints in the entire hierarchy starting from the given root.

#### Args

- `root`: The joint to start pinning from

#### Returns

- List of created pin controls

--------------------

### Remove All Pins

Identifier : `Remove All Pins`

#### Overview

 This will remove all pins in the entire scene

#### Args

#### Returns



--------------------

### Remove Pins

Identifier : `Remove Pins`

#### Overview

 This will remove any pins which are pinning any of the nodes in the given list.

#### Args

- `items`: List of nodes to remove pins for

#### Returns

- None

# Posing

--------------------

### Pose Copy

Identifier : `Pose Copy`

#### Overview

 This will store the current local space transform of the selected controls and store them.

#### Args

- `nodes`: List of nodes to store. If none are given then the selection will be used

#### Returns



--------------------

### Pose Copy (WorldSpace)

Identifier : `Pose Copy (WorldSpace)`

#### Overview

 This will store the current local space transform of the selected controls and store them.

#### Args

- `nodes`: List of nodes to store. If none are given then the selection will be used

#### Returns



--------------------

### Pose Paste

Identifier : `Pose Paste`

#### Overview

 This will apply the previously stored local space transforms back to the objects. If "Selection Only" is turned on, then the pose will only be applied to matching objects which are also selected.

#### Args

#### Returns



--------------------

### Pose Paste (WorldSpace)

Identifier : `Pose Paste (WorldSpace)`

#### Overview

 This will apply the previously stored world space transforms back to the objects. If "Selection Only" is turned on, then the pose will only be applied to matching objects which are also selected.

#### Args

#### Returns



# Rigging

--------------------

### Calculate Four Spline Positions From Joints

Identifier : `Calculate Four Spline Positions From Joints`

#### Overview

 This will determine the positions for a bezier spline in order to keep the joints transforms.

#### Args

- `joints`(*str*): List of joints

#### Returns



--------------------

### Create Soft Ik

Identifier : `Create Soft Ik`

#### Overview

 This will create a Soft IK setup to a pre-existing three bone IK setup.

#### Args

- `root`(*str*): The starting root of the joint in the three bone setup

- `target`(*str*): A node which we can track for distances (typically whatever is driving the pre-existing ik handle

- `second_joint`(*str*): The second joint in the three bone setup

- `third_joint`(*str*): The third joint in the three bone setup

- `host`(*str*): The node which all the attributes should be added to

#### Returns

- None

--------------------

### Create Spline Setup

Identifier : `Create Spline Setup`

--------------------

### Create Twist Setup

Identifier : `Create Twist Setup`

#### Overview

 This will create a twister setup - this provides two end points which can be accessed via twistSetup.root() and twistSetup.tip(). You can also access the root org of the twist setup using twistSetup.org() All controls can be accessed via twistSetup.all_controls()

#### Args

- `twist_count (int)`: The number of twists to create

- `description (str)`: The description of the twist - this will be used in all the node names

- `location`(*str*): The location tag for the nodes

- `config`: The aniseed.RigConfiguration instance

#### Returns

- The TwistSetup instance

--------------------

### Create Two Bone IKFK

Identifier : `Create Two Bone IKFK`

# Selection

--------------------

### Get By Location

Identifier : `Get By Location`

#### Overview

 This will return the opposite controls for the given controls

#### Args

- `controls`: List of controls to get the opposites for. If none are given then the selection will be used.

#### Returns



--------------------

### Get Opposites

Identifier : `Get Opposites`

#### Overview

 This will return the opposite controls for the given controls

#### Args

- `controls`: List of controls to get the opposites for. If none are given then the selection will be used.

#### Returns



--------------------

### Select Alternate Controls

Identifier : `Select Alternate Controls`

#### Overview

 This will zero out all the animatable channels for the given node

#### Args

- `node`(*str*): The node to zero out (reset)

#### Returns

- None

--------------------

### Select Controls

Identifier : `Select Controls`

#### Overview

 This will select all the controls for the given rig (if there is a selection or all the controls in all rigs if there is not a selection).

#### Args

#### Returns



--------------------

### Select Controls By Location

Identifier : `Select Controls By Location`

#### Overview

 This will zero out all the animatable channels for the given node

#### Args

- `node`(*str*): The node to zero out (reset)

#### Returns

- None

--------------------

### Select Filtered Controls

Identifier : `Select Filtered Controls`

#### Overview

 This will zero out all the animatable channels for the given node

#### Args

- `node`(*str*): The node to zero out (reset)

#### Returns

- None

--------------------

### Select Opposite

Identifier : `Select Opposite`

#### Overview

 This will select controls of the opposing location (side)

#### Args

#### Returns



--------------------

### Zero Rig

Identifier : `Zero Rig`

#### Overview

 This will zero out all the animatable channels for the selected controls.

#### Args

- `key_on_reset (bool, optional)`: If True, the objects will be keyed after being reset

#### Returns

- None

--------------------

### Zero Selection

Identifier : `Zero Selection`

#### Overview

 This will zero out all the animatable channels for the selected controls.

#### Args

- `key_on_reset (bool, optional)`: If True, the objects will be keyed after being reset

#### Returns

- None

# Shapes

--------------------

### Apply Shape

Identifier : `Apply Shape`

#### Overview

 Applies the given shape data to the given node.

#### Args

- `node`(*str*): Node to apply the shape data to

- `data`(*str*): Either a dictionary of shape data, or the absolute path to a shape file, or the name of a shape in the shapes directory

- `clear`(*bool*): If true, any pre-existing shapes will be removed before this applies the shape.

- `color`: Optional list [r, g, b] which will be used to colour the shape on creation

- `scale_by`(*int*): Optional multiplier for scaling the shape at the time of it being applied.

#### Returns

- List of shape nodes created

--------------------

### Apply Shape Color

Identifier : `Apply Shape Color`

#### Overview

 This will apply the given rgb values to the shapes of the selected nodes and ensure that their colour overrides are set.

#### Args

- `node`(*str*): The node to apply the colour to

- `r`(*int*): The red channel value (between zero and one)

- `g`(*int*): The green channel value (between zero and one)

- `b`(*int*): The blue channel value (between zero and one)

#### Returns

- None

--------------------

### Apply Shape Color Prompt

Identifier : `Apply Shape Color Prompt`

#### Overview

 This will prompt the user with a colour dialog and apply the given colour to the shapes of the selected nodes.

#### Args

#### Returns



--------------------

### Combine Shapes

Identifier : `Combine Shapes`

#### Overview

 Parents all the shapes under all the given nodes under the first given node

#### Args

- `nodes`: List of nodes to combine, with the first one being the node where all the resulting shapes will be applied

#### Returns

- None

--------------------

### Copy Shape

Identifier : `Copy Shape`

#### Overview

 This will return a list of shape files which are present in the aniseed toolkit shapes directory

#### Args

#### Returns

- List of absolute paths to the json shape files

--------------------

### Get Shape List

Identifier : `Get Shape List`

#### Overview

 This will return a list of shape files which are present in the aniseed toolkit shapes directory

#### Args

#### Returns

- List of absolute paths to the json shape files

--------------------

### Get Up Axis Shape Rotation Vector

Identifier : `Get Up Axis Shape Rotation Vector`

#### Overview

 Shapes are authored in a Y up environment. If you want to get a rotation vector to rotate the shape around based on another axis being up, you can use this function to get that vector

#### Args

- `up_axis`(*str*): The axis to be considered up

#### Returns

- List[float] of the rotation to apply to a shape

--------------------

### Load Rig Control Shapes From File

Identifier : `Load Rig Control Shapes From File`

--------------------

### Mirror Across

Identifier : `Mirror Across`

#### Overview

 This will attempt to mirror (globally) the shape from the from_node to the to_node across the specified axis.

#### Args

- `from_node`: What node should be the mirror from

- `to_node`: What node should be the mirror to

- `axis`(*str*): What axis should be mirrored (x, y, z)

#### Returns

- None

--------------------

### Mirror All Shapes Across

Identifier : `Mirror All Shapes Across`

--------------------

### Mirror Shape

Identifier : `Mirror Shape`

#### Overview

 This will mirror the shapes for a given node across a specific axis (x, y, z)

#### Args

- `nodes`: List of nodes to perform the mirror on

- `axis`(*str*): What axis should be mirrored (x, y, z)

#### Returns



--------------------

### Offset Shapes

Identifier : `Offset Shapes`

#### Overview

 This will do an in-place scaling of the shapes for a given node

#### Args

- `node`(*str*): The node whose shapes should be offset

- `offset_by`(*int*): The amount to offset the shapes by

- `x`(*float*): A multiplier for the offset amount specifically on the x axis

- `y`(*float*): A multiplier for the offset amount specifically on the y axis

- `z`(*float*): A multiplier for the offset amount specifically on the z axis

#### Returns

- None

--------------------

### Paste Shape

Identifier : `Paste Shape`

#### Overview

 This will return a list of shape files which are present in the aniseed toolkit shapes directory

#### Args

#### Returns

- List of absolute paths to the json shape files

--------------------

### Read Shape From File

Identifier : `Read Shape From File`

#### Overview

 This will attempt to get the shape dictionary data from a shape file. The shape file can either be the local name of a shape in the shapes directory or an absolute path to a shape file.

#### Args

- `shape_file`(*str*): The shape file to read (either absolute path or the name of a shape in the shapes directory)

#### Returns

- dict

--------------------

### Read Shape From Node

Identifier : `Read Shape From Node`

#### Overview

 Looks at all the NurbsCurve shape nodes under  the given node and attempts to read them into a dictionary format.

#### Args

- `node`(*str*): The node to seralise the shape data for

#### Returns

- dictionary

--------------------

### Rotate Shape From Up Axis

Identifier : `Rotate Shape From Up Axis`

#### Overview

 Shapes are authored in a Y up environment. If you want to get a rotation vector to rotate the shape around based on another axis being up, you can use this function to get that vector

#### Args

- `node`(*str*): The node to rotate the shape for

- `up_axis`(*str*): What axis should be considered up

#### Returns



--------------------

### Rotate Shapes

Identifier : `Rotate Shapes`

#### Overview

 Spins the shape around by the given x, y, z (local values)

#### Args

- `node`(*str*): The node whose shapes should be spun

- `x`(*float*): Amount to spin on the shapes local X axis in degrees

- `y`(*float*): Amount to spin on the shapes local Y axis in degrees

- `z`(*float*): Amount to spin on the shapes local Z axis in degrees

- `pivot`: Optional alternate pivot to rotate around. This can either be a vector (list[float]) or an actual object (str)

#### Returns

- None

--------------------

### Save All Rig Control Shapes

Identifier : `Save All Rig Control Shapes`

--------------------

### Save Shape

Identifier : `Save Shape`

#### Overview

 Writes the curve data of the given node to the given filepath

#### Args

- `node`(*str*): Node to read from

- `filepath`(*str*): Path to write the data into

#### Returns

- Dict of the data stored in the filepath

--------------------

### Scale Shapes

Identifier : `Scale Shapes`

#### Overview

 This will do an in-place scaling of the shapes for a given node

#### Args

- `node`(*str*): The node whose shapes should be offset

- `scale_by`(*int*): The amount to offset the shapes by

- `x`(*float*): A multiplier for the offset amount specifically on the x axis

- `y`(*float*): A multiplier for the offset amount specifically on the y axis

- `z`(*float*): A multiplier for the offset amount specifically on the z axis

#### Returns

- None

--------------------

### Select Shapes

Identifier : `Select Shapes`

#### Overview

 This will return a list of shape files which are present in the aniseed toolkit shapes directory

#### Args

#### Returns

- List of absolute paths to the json shape files

--------------------

### Snap Shape To Node Transform

Identifier : `Snap Shape To Node Transform`

# Skinning

--------------------

### Copy Skin To Unskinned Meshes

Identifier : `Copy Skin To Unskinned Meshes`

#### Overview

 This will copy the skin weights from the skinned_mesh object to all the unskinned_meshes.

#### Args

- `skinned_mesh`(*str*): the name of the skinned mesh

- `unskinned_meshes`: A list of meshes you want to copy the skinweights to.

#### Returns

- None

--------------------

### Disconnect All Skins

Identifier : `Disconnect All Skins`

#### Overview

 This will disconnect all the skinCluster nodes in the scene. It does not remove them, and does not disconnect them.

#### Args

#### Returns



--------------------

### Interp : Apply Interpolation

Identifier : `Interp : Apply Interpolation`

--------------------

### Interp : Set Target A Weights

Identifier : `Interp : Set Target A Weights`

--------------------

### Interp : Set Target B Weights

Identifier : `Interp : Set Target B Weights`

--------------------

### Load Skin File

Identifier : `Load Skin File`

#### Overview

 This will load the given skin weights file onto the given mesh. If a skin is already applied, it will be removed.

#### Args

- `mesh`(*str*): The node to apply the skin weights to

- `filepath`(*str*): The location to load the skinweights from

#### Returns

- The skinCluster node

--------------------

### Reconnect All Skins

Identifier : `Reconnect All Skins`

#### Overview

 This will reconnect all skin clusters in the scene which have previously been disconnected.

#### Args

#### Returns



--------------------

### Save Skin File

Identifier : `Save Skin File`

#### Overview

 This will save the skin weights of the given mesh to the given filepath.

#### Args

- `mesh`(*str*): The node to save the skin weights for

- `filepath`(*str*): The location to save the skinweights

#### Returns

- None

# Transforms

--------------------

### 

Identifier : ``

#### Overview

 This will attempt to return a Direction instance which represents the upvector direction of the chain between the start and end joint. The Direction instance is a class which provides easy access to directional data in different formats such as: axis: x, y, z full_string: Positive X, Negative X axis_vector: [1, 0, 0] direction_vector: [-1, 0, 0] cross_axis: x, y, z (the axis that crosses this one)

#### Args

- `start`(*str*): The first bone in the chain

- `end`(*str*): The last bone in the chain

- `epsilon`(*float*): How much variance in axis change we will tolerate

#### Returns

- Direction instance

--------------------

### Align Bones For Ik

Identifier : `Align Bones For Ik`

#### Overview

 This will align the bones down the chain based on a specific facing axis and a specific up axis. All joints including the end joint will be aligned (the end joint taking its vector from the projection of the joint before it).

#### Args

- `root`(*str*): The joint to start aligning from

- `tip`(*str*): The end joint - only joints between these two will be affected

- `primary_axis`(*str*): The axis to align to ('Positive X', 'Negative Y', etc)

- `polevector_axis`(*str*): The axis to align to (same format as primary_axis)

- `retain_child_transforms`: Whether to keep (in worldspace) the same transform for any children that are not part of the chain

#### Returns

- None

--------------------

### Apply Relative Matrix

Identifier : `Apply Relative Matrix`

#### Overview

 This will apply the matrix to the node as if the node were a child of the relative_to node

#### Args

- `node`(*type*): The node to adjust

- `matrix`(*type*): The matrix to apply (maya.cmds)

- `relative_to`(*str*): The node to use as a parent for spatial transforms

#### Returns

- None

--------------------

### Calculate Upvector Position

Identifier : `Calculate Upvector Position`

#### Overview

 Based on three points, this will calculate the position for an up-vector for the plane.

#### Args

- `point_a`(*str*): Start point (which can be a float list or a node name)

- `point_b`(*str*): End point (which can be a float list or a node name)

- `point_c`(*str*): Start point (which can be a float list or a node name)

- `length`(*float*): By default the vector will be multipled by the chain length but you can use this value to multiply that to make it further or shorter

- `create`(*bool*): If true, a transform node will be created at the specified location

#### Returns

- MVector of the position in worldspace

--------------------

### Clear Constraints

Identifier : `Clear Constraints`

--------------------

### Create Locator At Center

Identifier : `Create Locator At Center`

#### Overview

 Creates a locator at the center of the current selected components

#### Args

#### Returns

- The name of the created locator

--------------------

### Get Chain Facing Direction

Identifier : `Get Chain Facing Direction`

#### Overview

 This will return a Direction class which represents the facing direction of a chain. The facing direction is the direction ALL bones are using down-the-bone. The Direction instance is a class which provides easy access to directional data in different formats such as: axis: x, y, z full_string: Positive X, Negative X axis_vector: [1, 0, 0] direction_vector: [-1, 0, 0] cross_axis: x, y, z (the axis that crosses this one)

#### Args

- `start`(*str*): The first bone in the chain

- `end`(*str*): The last bone in the chain

- `epsilon`(*float*): How much variance in axis change we will tolerate

#### Returns

- Direction instance

--------------------

### Get Direction Class

Identifier : `Get Direction Class`

#### Overview

 This will return a Direction instance for the given direction. The Direction instance is a class which provides easy access to directional data in different formats such as: axis: x, y, z full_string: Positive X, Negative X axis_vector: [1, 0, 0] direction_vector: [-1, 0, 0] cross_axis: x, y, z (the axis that crosses this one)

#### Args

- `direction`(*str*): The direction string (x, y, z) to instance a direction class with Return Direction class

#### Returns



--------------------

### Get Relative Matrix

Identifier : `Get Relative Matrix`

#### Overview

 This will get a matrix which is the relative matrix between the relative_to and the node item

#### Args

- `node`(*str*): The node to consider as the child

- `relative_to`(*str*): The node to consider as the parent

#### Returns

- relative matrix as a list (maya.cmds)

--------------------

### Global Mirror

Identifier : `Global Mirror`

#### Overview

 This function is taken from github with a minor modification. The author and credit goes to Andreas Ranman. Github Url: https://gist.github.com/rondreas/1c6d4e5fc6535649780d5b65fc5a9283 Mirrors transform across hyperplane.

#### Args

- `transforms`: list of Transform or string.

- `across`(*str*): plane which to mirror across (XY, YX or XZ).

- `behaviour`(*bool*): If true, it should mirror the rotational behaviour too

- `name_replacement`: a tuple of length two, where the first part should be replaced with the second part

#### Returns



--------------------

### Invert Translation

Identifier : `Invert Translation`

#### Overview

 This will invert the translation channels of a node

#### Args

- `transforms`: List of transforms to invert the translation of

#### Returns

- None

--------------------

### Position Between

Identifier : `Position Between`

#### Overview

 This will set the translation of the given node to be at a position between from_this and to_this based on the factor value. A factor of zero will mean a position on top of from_this, whilst a factor of 1 will mean a position on bottom of to_this.

#### Args

- `node`(*str*): The node to adjust the position for

- `from_this`(*str*): The first node to consider

- `to_this`(*str*): The second node to consider

- `factor`(*float*): The factor value to use

#### Returns

- None

# Visibility

--------------------

### Create Aim Hierarchy

Identifier : `Create Aim Hierarchy`

--------------------

### Create Blend Chain

Identifier : `Create Blend Chain`

--------------------

### Find All Children With Tag

Identifier : `Find All Children With Tag`

--------------------

### Find All With Tag

Identifier : `Find All With Tag`

--------------------

### Find First Child With Tag

Identifier : `Find First Child With Tag`

--------------------

### Get Tag Data

Identifier : `Get Tag Data`

--------------------

### Has Tag

Identifier : `Has Tag`

--------------------

### Hide Nodes

Identifier : `Hide Nodes`

#### Overview

 This will hide all the given nodes. However, it will first do a node type test, and if it is a joint it will hide it using the joint style attribute rather than the visibility attribute.

#### Args

- `items`: List of nodes to hide

#### Returns

- None

--------------------

### Show Nodes

Identifier : `Show Nodes`

#### Overview

 This will show all the given nodes. However, it will first do a node type test, and if it is a joint it will show it using the joint style attribute rather than the visibility attribute.

#### Args

- `items`: List of nodes to hide

#### Returns

- None

--------------------

### Tag Node

Identifier : `Tag Node`

#### Overview



#### Args

- `node`(*str*): Node to tag

- `tag`(*str*): Tag to apply

#### Returns

- None

