'''
Rigging: a skeleton of joints for the glTF that a game engine animates.

    hips = joint("hips", (0, 0, 92))
    spine = joint("spine", (0, 0, 128), parent="hips")
    shoulder = joint("shoulder.R", shoulder_point, parent="spine")           # a point works: its numbers at the time of the export
    elbow = joint("elbow.R", (31, 0, 113), parent="shoulder.R")
    bones = mirror_joints([hips, spine, shoulder, elbow])                    # every ".R" joint gets a ".L" one on the other side of x = 0
    export_mesh(figure, "hero.glb", skeleton=bones)

The joints are in the order they are given, every joint after its parent, and there is ONE root.  The export writes them as the nodes of the glTF, with the
skin (the inverse bind matrices) and, for every vertex, the four joints that move it and how much (JOINTS_0 and WEIGHTS_0): the weights come from the
distance of the vertex to the bones.  The bone of a joint is the segments from it to its children (and the joint itself): the geometry between the elbow and
the hand follows the elbow, as it does when the elbow is turned.  A vertex follows the nearest bone alone, and shares itself with the others that are about as near
-- within `skin_falloff` -- so that a joint bends smoothly.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from fieldes.stdlib import curves as C

__all__ = ['joint', 'mirror_joints', 'Joint']


class Joint:
    ''' A joint of a skeleton: see `joint` '''

    def __init__(self, name, position, parent, tip=None):
        self.name = name
        self.position = position
        self.parent = parent
        self.tip = tip

    def __repr__(self):
        return 'joint(%r, (%.4g, %.4g, %.4g), parent=%r)' % ((self.name,) + tuple(self.position) + (self.parent,))


def joint(name, position, parent=None, tip=None):
    ''' A joint of a skeleton for `export_mesh(..., skeleton=[...])`.

        name      what the file calls it (a text: "elbow.R"; each joint of a skeleton has its own)
        position  where it is in the model: a point (the numbers it has when the file is written) or (x, y, z)
        parent    the name of the joint it hangs from, a joint that was made before it; None for the root, which there is one of
        tip       where the bone of a joint with no children ends -- the hand, the head, the toe: a point or (x, y, z).  Not given: the bone goes on in the
                  direction of the one before it for half its length (the hand goes on past the wrist), so that the end of the body has a bone of its own '''
    name = str(name or '').strip()
    if not name:
        raise ValueError('joint: a name is needed')
    if parent is not None:
        parent = str(parent).strip()
        if parent == name:
            raise ValueError('joint %s: it cannot hang from itself' % name)
    try:
        place = tuple(float(v) for v in C.Control(position).pos)
        end = tuple(float(v) for v in C.Control(tip).pos) if tip is not None else None
    except TypeError:
        raise TypeError('joint %s: the position (and the tip) is a point or (x, y, z), not %r' % (name, position))
    return Joint(name, place, parent, end)


def mirror_joints(joints, axis='x', plane=0.0, suffixes=('.R', '.L')):
    ''' The joints and the mirror images of those whose name ends with `suffixes[0]`: across the plane `axis` = `plane` ("x", "y" or "z"), named with `suffixes[1]`
        instead, hanging from the mirror image of their parent when it has one and from their parent otherwise.  The skeleton of a half of a body is the skeleton of all of it '''
    index = 'xyz'.index(str(axis).lower())
    joints = list(joints)
    right, left = suffixes
    out = list(joints)
    for j in joints:
        if j.name.endswith(right):
            def across(p):
                p = list(p)
                p[index] = 2.0 * plane - p[index]
                return tuple(p)
            parent = j.parent
            if parent is not None and parent.endswith(right):
                parent = parent[:-len(right)] + left
            out.append(Joint(j.name[:-len(right)] + left, across(j.position), parent, across(j.tip) if j.tip is not None else None))
    return out
