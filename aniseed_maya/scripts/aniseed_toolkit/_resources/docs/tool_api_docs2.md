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

