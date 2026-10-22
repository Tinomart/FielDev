'''
Rigging: a skeleton of joints, and the weights of a skin, for the glTF that is animated.

    hips = joint("hips", (0, 0, 92))
    spine = joint("spine", (0, 0, 128), parent="hips")
    shoulder = joint("shoulder.R", shoulder_point, parent="spine")           # a point works: its numbers at the time of the export
    elbow = joint("elbow.R", (31, 0, 113), parent="shoulder.R")
    jaw = joint("jaw", (0, 6, 150), parent="head", influence=box((-8, 0, 140), (8, 14, 150)))     # the jaw owns the box: the skin there follows it alone
    bones = mirror_joints([hips, spine, shoulder, elbow])                    # every ".R" joint gets a ".L" one on the other side of x = 0
    export_mesh(figure, "hero.glb", skeleton=bones, max_influences=4)

The joints are in the order they are given, every joint after its parent, and there is ONE root.  The export writes them as the nodes of the glTF, with the
skin (the inverse bind matrices) and, for every vertex, the joints that move it and how much (JOINTS_0 and WEIGHTS_0, and _1 for more than four): the weights are
FUNCTIONS OF THE PLACE of the vertex, not of the triangles it is in -- so they are as smooth as the model is, and the same at a seam.  Two rules make them:

  the bones   The bone of a joint is the segments from it to its children (and the joint itself): the geometry between the elbow and the hand follows the elbow, as it does
              when the elbow is turned.  A vertex follows the nearest bone alone, and shares itself with the joints beside it at the two ends of that bone -- the parent at the
              start, the child at the end: half at the very joint, less and less over `skin_falloff` mm along the bone, none beyond -- so that a joint bends smoothly and a bone that
              is merely near (the other leg) never moves a vertex.
  the fields  A joint with an `influence` (a body or a field) owns the places where it is negative: there the skin follows the joint alone, and it fades to the weights of the bones over
              `skin_falloff` mm outside.  The joints are layers, as materials are: the later one is on top.  A jaw, a finger, a tail tip, a cape -- anything the bones do not shape.

Then the weights are cut to the `max_influences` strongest (4 is what the engines run; up to 8) and made to add up to 1.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math
from array import array

from fieldev.shape import Shape
from fieldev.stdlib import curves as C

__all__ = ['joint', 'mirror_joints', 'Joint']


class Joint:
    ''' A joint of a skeleton: see `joint` '''

    def __init__(self, name, position, parent, tip=None, influence=None):
        self.name = name
        self.position = position
        self.parent = parent
        self.tip = tip
        self.influence = influence

    def __repr__(self):
        return 'joint(%r, (%.4g, %.4g, %.4g), parent=%r%s)' % ((self.name,) + tuple(self.position) + (self.parent, ', influence=...' if self.influence is not None else ''))


def joint(name, position, parent=None, tip=None, influence=None):
    ''' A joint of a skeleton for `export_mesh(..., skeleton=[...])`.

        name       what the file calls it (a text: "elbow.R"; each joint of a skeleton has its own)
        position   where it is in the model: a point (the numbers it has when the file is written) or (x, y, z)
        parent     the name of the joint it hangs from, a joint that was made before it; None for the root, which there is one of
        tip        where the bone of a joint with no children ends -- the hand, the head, the toe: a point or (x, y, z).  Not given: the bone goes on in the
                   direction of the one before it for half its length (the hand goes on past the wrist), so that the end of the body has a bone of its own
        influence  a body or a field: the places where it is negative belong to this joint (the skin there follows it alone), fading to the weights of the bones over the
                   `skin_falloff` of the export.  None: the joint has only its bones '''
    name = str(name or '').strip()
    if not name:
        raise ValueError('joint: a name is needed')
    if parent is not None:
        parent = str(parent).strip()
        if parent == name:
            raise ValueError('joint %s: it cannot hang from itself' % name)
    if influence is not None and not isinstance(influence, Shape):
        raise TypeError('joint %s: influence is a body or a field, not %r' % (name, type(influence).__name__))
    try:
        place = tuple(float(v) for v in C.Control(position).pos)
        end = tuple(float(v) for v in C.Control(tip).pos) if tip is not None else None
    except TypeError:
        raise TypeError('joint %s: the position (and the tip) is a point or (x, y, z), not %r' % (name, position))
    return Joint(name, place, parent, end, influence)


def mirror_joints(joints, axis='x', plane=0.0, suffixes=('.R', '.L')):
    ''' The joints and the mirror images of those whose name ends with `suffixes[0]`: across the plane `axis` = `plane` ("x", "y" or "z"), named with `suffixes[1]`
        instead, hanging from the mirror image of their parent when it has one and from their parent otherwise, with the mirror image of their influence.  The skeleton of a half
        of a body is the skeleton of all of it '''
    from fieldev.stdlib import transforms as T
    index = 'xyz'.index(str(axis).lower())
    reflect = (T.reflect_x, T.reflect_y, T.reflect_z)[index]
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
            influence = reflect(j.influence, plane) if j.influence is not None else None
            out.append(Joint(j.name[:-len(right)] + left, across(j.position), parent, across(j.tip) if j.tip is not None else None, influence))
    return out


def skin_weights(xyz, joints, falloff, max_influences, eval_at):
    ''' For every vertex the joints that move it and how much: (the joint numbers, a B array of `max_influences` for each vertex; the weights, an f array of the same, adding up to 1).
        See the top of this file for the two rules.  `falloff` is in mm (None: 4 % of the largest side of the model); `eval_at(field, xyz, count)` evaluates a field at the vertices '''
    nv = len(xyz) // 3
    if falloff is None:
        falloff = 0.04 * (max(max(xyz[c::3]) - min(xyz[c::3]) for c in range(3)) or 1.0)
    falloff = float(falloff)
    if not falloff > 0:
        raise ValueError('export_mesh: skin_falloff is above 0 mm, not {!r}'.format(falloff))
    number = {j.name: k for k, j in enumerate(joints)}
    children = {}
    for k, j in enumerate(joints):
        if j.parent is not None:
            children.setdefault(j.parent, []).append(k)
    bones = []                      # (the joint it is of, its start, the vector to its end, the square of its length, the joint at its end (None: a tip))
    for k, j in enumerate(joints):
        a = j.position
        if children.get(j.name):
            ends = [(joints[c].position, c) for c in children[j.name]]
        elif j.tip is not None:
            ends = [(j.tip, None)]
        elif j.parent is not None:
            before = joints[number[j.parent]].position
            ends = [(tuple(a[c] + 0.5 * (a[c] - before[c]) for c in range(3)), None)]
        else:
            ends = [(a, None)]
        for b, c in ends:
            v = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            bones.append((k, a, v, v[0] * v[0] + v[1] * v[1] + v[2] * v[2], c))
    shares = []                     # per vertex: {joint number: weight}
    for i in range(nv):
        px, py, pz = xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]
        nearest = None
        for k, a, v, l2, c in bones:
            dx, dy, dz = px - a[0], py - a[1], pz - a[2]
            t = (dx * v[0] + dy * v[1] + dz * v[2]) / l2 if l2 > 0 else 0.0
            t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            ex, ey, ez = dx - t * v[0], dy - t * v[1], dz - t * v[2]
            d2 = ex * ex + ey * ey + ez * ez
            if nearest is None or d2 < nearest[0]:
                nearest = (d2, k, t, l2, c)
        d2, k, t, l2, c = nearest
        length = math.sqrt(l2)
        at_start = 0.5 * max(0.0, 1.0 - t * length / falloff) if joints[k].parent is not None else 0.0
        at_end = 0.5 * max(0.0, 1.0 - (1.0 - t) * length / falloff) if c is not None else 0.0
        mine = {k: 1.0 - at_start - at_end}
        if at_start > 0.0:
            mine[number[joints[k].parent]] = mine.get(number[joints[k].parent], 0.0) + at_start
        if at_end > 0.0:
            mine[c] = mine.get(c, 0.0) + at_end
        shares.append(mine)
    for k, j in enumerate(joints):                      # (the joints that own a place: layers, the later on top)
        if j.influence is None:
            continue
        inside = eval_at(j.influence, xyz, nv)
        for i in range(nv):
            a = min(1.0, max(0.0, 1.0 - inside[i] / falloff))           # (all of it where the field is negative, fading over `falloff` outside)
            if a > 0.0:
                mine = shares[i]
                for key in mine:
                    mine[key] *= 1.0 - a
                mine[k] = mine.get(k, 0.0) + a
    ids = array('B', [0]) * (max_influences * nv)
    weights = array('f', [0.0]) * (max_influences * nv)
    for i in range(nv):
        strongest = sorted(shares[i].items(), key=lambda s: -s[1])[:max_influences]
        strongest = [(k, w) for k, w in strongest if w >= 0.002] or strongest[:1]
        total = sum(w for _, w in strongest)
        for slot, (k, w) in enumerate(strongest):
            ids[max_influences * i + slot] = k
            weights[max_influences * i + slot] = w / total
    return ids, weights
