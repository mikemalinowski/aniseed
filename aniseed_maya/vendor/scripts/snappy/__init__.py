"""
# Snappy

## Origins
```
Snappy is an extraction of part of a Crab ulitity from 2019. This version
has specifically been seperated from any rigging framework and converted to maya.cmds
and OpenMaya to ensure it works in Maya 2024, 2025 & 2026. You can see the original
code here:
https://github.com/mikemalinowski/crab/blob/master/crab/utils/snap.py
```
Snappy is an object snapping tool which allows a user/developer
to define a node to snap and a target. At the time the snap relationship
is defined it will also store the offset matrix between the two - ensuring
that when the snap is later used the offset will be retained.

The snapping is group centric - meaning that when you declare a snap
you also give it a group label. This means you can snap by label too which
will trigger the snapping of all items within that snap group. This is
great for things like IK/FK snapping where you need multiple objects
to snap simultaneously.

Snappy comes with a headless set of functions which can be used to define and
trigger snaps. It also comes with a gui application which can be used by
riggers or animators to setup snap groups or trigger snap groups.

## User Facing Tool

To launch the tool you can run this code:

```python
import snappy
snappy.launch()
```

With the tool open, select a node you want to snap and a node you want to
snap to - then right click in the tool and choose "New Snap Group". Give the
snap a group label and it will then show in the tool. From that point you can
right click that snap group and select "snap" to instigate the snap.

With a pre-existing snap group, you can select a node  you want to snap and a node
it should snap to and right click the snap group. You can then add this as a new
snap member of the pre-existing group.

## Using the snap tools headless

You can use all of the snappy functionality without the ui.

To create a new snap, whether its a new label or a pre-existing one you
can use the code below. This will use

```python
import snappy
snappy.new(node="object_a", target="object_b", group="example")
```

You can then instigate the snapping of that group using
```python
import snappy
snappy.snap_label("example")
```

## MIT License

Copyright (c) 2025 Michael Malinowski

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
from .core import new
from .core import snap
from .core import snap_group
from .core import snappable
from .core import groups
from .core import members

from . app import launch

__version__ = "1.0.1"
