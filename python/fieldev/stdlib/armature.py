'''
Armatures: a character made of parts, each a path of nodes with a thickness, and the skeleton that goes with them.

    shoulder = point(18, 0, 138)                            # a node: a point, with the size of its gizmo as its thickness
    elbow = point(31, 0, 113)
    hand = point(37, 8, 92)
    arm = limb([shoulder, elbow, hand], radii=[6, 4.5, 3.5], name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"])
    spine = limb([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5], name="spine", joints=["hips", "spine", "chest", "neck"])
    hero = character([spine, arm, ...], blend=4, symmetric="x")          # the body: the parts joined with a blend, and the left half as the mirror image
    export_mesh(hero, "hero.glb", symmetric="x", skeleton=skeleton_of([spine, arm, ...], mirror="x"))

A LIMB is a path extruded: the cross-section is swept along a smooth curve through its nodes, thicker or thinner at each node.  By default the cross-section is round and the sweep is
made of round cones along the curve (the curve is a Catmull-Rom spline through the nodes, so the limb bends smoothly, and every number in it is an expression of the nodes, so that a node
dragged in the viewport moves the limb with it at once).  With `profile=` -- any 2D shape, a square, a polygon, a profile of your own -- the limb is `path_extrude(profile, spline(nodes))`,
which keeps the shape of the profile along the curve (and takes longer to draw).

The nodes of a limb are the joints of the skeleton: `skeleton_of` makes a joint for each, named by `joints=` (or `<name>_0`, `<name>_1` ...), each hanging from the one before it.  A limb
that begins on a node of another limb -- its first node is within a few millimetres of one -- is a branch of it, and hangs from that joint; `parent="chest"` says where a limb is joined
when its first node is not on the other.  There is one root: the first node of the first limb.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math

from fieldev.kinds import takes as _declare
from fieldev.shape import Shape
from fieldev.stdlib import curves as C
from fieldev.stdlib import fields as F
from fieldev.stdlib.characters import round_cone, _radius
from fieldev.stdlib.rigging import Joint, mirror_joints

__all__ = ['limb', 'character', 'skeleton_of', 'Limb']


class Limb:
    ''' What a limb knows of itself, for the skeleton: its name, the nodes (as controls), the names of its joints, and where it is joined '''

    def __init__(self, name, ctrls, joints, parent, sizes):
        self.name = name
        self.ctrls = ctrls
        self.joints = joints
        self.parent = parent
        self.sizes = sizes

    def __repr__(self):
        return 'limb(%r, %d nodes)' % (self.name, len(self.ctrls))


def _width(sizes, i, t):
    ''' The thickness a fraction t of the way from node i to the next: a Catmull-Rom curve through the nodes' thicknesses (the ends doubled), as the path itself is, so that the thickness changes
        smoothly across a node and no ring of the body shows where two round cones meet.  Numbers are kept above a hair's width; a thickness that is a field is left as it is '''
    # (the ends of a limb have no neighbour: the thickness is level there -- the end is round, and a slope would swell the last cone beyond the thickness of its node)
    n = len(sizes)
    a = sizes[i - 1] if i > 0 else sizes[i + 1]
    b, c = sizes[i], sizes[i + 1]
    d = sizes[i + 2] if i + 2 < n else sizes[i]
    w = 0.5 * (2.0 * b + (c - a) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * (t * t) + (3.0 * b - a - 3.0 * c + d) * (t * t * t))
    if isinstance(w, (int, float)) and isinstance(b, (int, float)) and isinstance(c, (int, float)):
        w = max(w, 0.05 * min(b, c))
    return w


def _catmull(p0, p1, p2, p3, t):
    ''' A place on the Catmull-Rom spline between p1 and p2 (t from 0 to 1), as three expressions: the nodes are tuples of expressions '''
    out = []
    for c in range(3):
        out.append(0.5 * (2.0 * p1[c] + (p2[c] - p0[c]) * t + (2.0 * p0[c] - 5.0 * p1[c] + 4.0 * p2[c] - p3[c]) * (t * t) + (3.0 * p1[c] - p0[c] - 3.0 * p2[c] + p3[c]) * (t * t * t)))
    return tuple(out)


def limb(points, radii=None, profile=None, name=None, joints=None, parent=None, detail=12, twist=0):
    ''' A part of a character: a cross-section swept along a smooth path through the nodes (a path extrude), thick or thin at each node.

            arm = limb([shoulder, elbow, hand], radii=[6, 4.5, 3.5], name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"])

        points   the nodes, in order: points (`point(x, y, z)`, dragged with their gizmos) or tuples of numbers
        radii    the thickness at each node: a number for all, or one for each (numbers or fields).  It is that number TIMES the size of the node -- the scale of its gizmo, the gold ring
                 (1 for a tuple) -- so with no radii the size of a node is its radius
        profile  None: a round cross-section (made of round cones along the path); or a 2D shape (`rectangle`, `polygon(...)`, a profile): the limb is `path_extrude(profile, spline(points))`,
                 and then the thickness at a node is the size of the node alone
        name     what the skeleton calls the limb ("arm.R"); joints: the names of the joints, one for each node (default `name_0`, `name_1` ...)
        parent   the name of the joint this limb hangs from, when its first node is not on a node of another limb
        detail   how many round cones make a stretch between two nodes: 12 (fewer is faster to draw and shows rings of the cones; more is smoother)
        twist    degrees, for a profile: the whole cross-section turned about the path '''
    if not isinstance(points, (list, tuple)) or not points:
        raise TypeError('limb(points): a list of nodes (points or tuples of numbers), one or more')
    ctrls = C.controls(list(points))
    n = len(ctrls)
    if radii is None:
        radii = [1.0] * n
    elif isinstance(radii, (list, tuple)):
        if len(radii) != n:
            raise ValueError('limb: %d nodes but %d radii -- one for each node, or one number for all' % (n, len(radii)))
    else:
        radii = [radii] * n
    sizes = []
    for k, (ctl, r) in enumerate(zip(ctrls, radii)):
        r = _radius(r, 'limb: radii[%d]' % k)
        sizes.append(r * ctl.scale_expr if ctl.scale_expr is not None else r)
    label = str(name) if name else 'limb'
    if joints is None:
        joints = ['%s_%d' % (label, k) for k in range(n)]
    elif not isinstance(joints, (list, tuple)) or len(joints) != n or len(set(joints)) != n:
        raise ValueError('limb: joints is %d different names, one for each node' % n)
    if not isinstance(detail, int) or isinstance(detail, bool) or not 1 <= detail <= 32:
        raise ValueError('limb: detail is the round cones between two nodes, from 1 to 32, not %r' % (detail,))
    if profile is not None:
        from fieldev.stdlib.profile import path_extrude
        from fieldev.stdlib import transforms
        way = C.spline(list(points))
        out = path_extrude(profile, way, twist)
        # (path_extrude starts the sweep where the 2D shape is -- the origin for a shape in the plane z = 0 -- and draws the path and its points there.  A limb is at its NODES: the sweep is
        # carried by what it was moved, with the nodes' own numbers, so that a node dragged moves the limb, and the nodes are drawn where they are)
        shift = getattr(way, '_weld_shift', None)
        if shift is not None:
            out = transforms.move(out, C.sub((0.0, 0.0, 0.0), tuple(shift)))
            for item in [way] + list(getattr(way, 'points', [])):
                try:
                    item._weld_shift = None
                except AttributeError:
                    pass
    elif n == 1:
        out = round_cone(ctrls[0].expr, ctrls[0].expr, sizes[0], sizes[0])
    else:
        # the curve: the nodes' own places and the places between them, from the Catmull-Rom spline (the ends are doubled)
        nodes = [c.expr for c in ctrls]
        way = [nodes[0]] + nodes + [nodes[-1]]
        places, widths = [], []
        for i in range(n - 1):
            for s in range(detail):
                t = s / float(detail)
                places.append(_catmull(way[i], way[i + 1], way[i + 2], way[i + 3], t))
                widths.append(_width(sizes, i, t))
        places.append(nodes[-1])
        widths.append(sizes[-1])
        out = F.union_all([round_cone(places[k], places[k + 1], widths[k], widths[k + 1]) for k in range(len(places) - 1)], 0)
    out._limb = Limb(label, ctrls, list(joints), None if parent is None else str(parent), sizes)
    return out


def character(limbs, blend=3, symmetric=None):
    ''' The body made of limbs: joined as one with a smooth blend of `blend` mm where they meet (0: none), and, with `symmetric` "x", "y" or "z", the other half as the mirror image
        (the limbs are modelled on one side of the plane; the parts that lie across it, a spine and a head, are in both) '''
    if not isinstance(limbs, (list, tuple)) or not limbs:
        raise TypeError('character(limbs): a list of limbs, one or more')
    body = F.union_all(list(limbs), blend)
    if symmetric is None:
        return body
    from fieldev.stdlib import transforms
    mirror = {'x': 'symmetric_x', 'y': 'symmetric_y', 'z': 'symmetric_z'}.get(str(symmetric).lower())
    if mirror is None:
        raise ValueError('character: symmetric is "x", "y" or "z", not %r' % (symmetric,))
    return getattr(transforms, mirror)(body)


def skeleton_of(limbs, mirror=None, plane=0.0, join=None):
    ''' The joints of the limbs, for `export_mesh(..., skeleton=...)`: a joint at each node, named by the limb's `joints`, each hanging from the one before it.  A limb whose first node is
        within `join` mm of a joint already made (default: half a millimetre: the same point, or the same place typed again) is a branch of it: that joint is its first, and its other nodes hang from it.
        A limb that is not on any joint hangs from the joint it names with `parent=`.  `mirror` ("x", "y" or "z"): the joints whose name ends with ".R" get a ".L" one across that plane '''
    out = []
    by_name = {}
    for k, one in enumerate(limbs):
        info = getattr(one, '_limb', None)
        if info is None:
            raise TypeError('skeleton_of: limb(...)s, not %r' % (type(one).__name__,))
        anchor = None
        first = info.ctrls[0].pos
        reach = join if join is not None else 0.5
        near = None
        for j in out:
            d = math.dist(j.position, first)
            if d <= reach and (near is None or d < near[0]):
                near = (d, j)
        start = 0
        if near is not None:
            anchor = near[1].name
            start = 1                                        # (its first node is that joint)
        elif info.parent is not None:
            if info.parent not in by_name:
                raise ValueError('skeleton_of: the limb %r hangs from %r, which is not a joint of an earlier limb' % (info.name, info.parent))
            anchor = info.parent
        elif out:
            raise ValueError('skeleton_of: the limb %r begins at %s, which is not on a joint of an earlier limb: say where it is joined with parent="a joint name"' % (
                info.name, tuple(round(c, 2) for c in first)))
        previous = anchor
        for index in range(start, len(info.ctrls)):
            name = info.joints[index]
            if name in by_name:
                raise ValueError('skeleton_of: two joints are called %r' % name)
            tip = None
            joint = Joint(name, tuple(float(c) for c in info.ctrls[index].pos), previous, tip, None)
            out.append(joint)
            by_name[name] = joint
            previous = name
    if mirror is not None:
        out = mirror_joints(out, axis=mirror, plane=plane)
    return out


# What the menus offer them for (see fieldev.kinds.takes): a limb is made of points, a character and a skeleton of limbs (bodies)
limb._takes = _declare({"point"}, [{"point"}])
character._takes = _declare({"solid"}, [{"solid"}])
skeleton_of._takes = _declare({"solid"}, [{"solid"}])
