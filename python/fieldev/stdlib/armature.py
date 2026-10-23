'''
Armatures: a character made of parts, each a path of nodes with a cross-section, and the skeleton that goes with them.

    shoulder = point(18, 0, 138)                            # a node: a point, with the size of its gizmo (the gold ring) as how thick the armature is there
    elbow = point(31, 0, 113)
    hand = point(37, 8, 92)
    arm = armature([shoulder, elbow, hand], name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"])
    spine = armature([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5], name="spine", joints=["hips", "spine", "chest", "neck"])
    face = cut_face(arm)                                    # the cross-section of the arm, shown at its first node: its points are the profile's
    hero = character([spine, arm, ...], blend=4, symmetric="x")          # the body: the parts joined with a blend, and the left half as the mirror image
    export_mesh(hero, "hero.glb", symmetric="x", skeleton=skeleton_of([spine, arm, ...], mirror="x"))

An ARMATURE is a path extruded: a cross-section swept along a smooth curve through its nodes (the curve is a Catmull-Rom spline through the nodes, so the armature bends smoothly), thicker or
thinner at each node, and every number in it is an expression of the nodes, so that a node dragged in the viewport moves the armature with it at once.  The cross-section is a PROFILE:
by default one that is made for the armature -- a square whose four corners are spline points, so that it is nearly round, with a radius of `radii` (1 by default) -- or any 2D shape of your
own, `armature([...], profile=my_profile)`: a profile you made from points, a polygon, a rectangle.  The profile is the same for the whole armature, and a node's size (the gold ring of its gizmo)
makes it bigger or smaller there (keep it near 1: a node's size is also how strongly the path leaves it, and a node many times the size of the profile swings the path out and back on
itself -- make the profile that size instead); the profile is a model of its own, so a different one is swapped in by dropping it on the profile the armature uses in the model tree.  Where the profile
is does not matter: the armature is swept from the first node.  `cut_face(armature)` shows the profile there, as a linked clone (`instance`) turned the way the armature leaves the node, with a dot
for each of the profile's points: pull a dot, and the profile -- and so the whole armature -- changes with it.

The nodes of an armature are the joints of the skeleton: `skeleton_of` makes a joint for each, named by `joints=` (or `<name>_0`, `<name>_1` ...), each hanging from the one before it.  An armature
that begins on a node of another armature -- its first node is within a few millimetres of one -- is a branch of it, and hangs from that joint; `parent="chest"` says where an armature is joined
when its first node is not on the other.  There is one root: the first node of the first armature.

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

__all__ = ['armature', 'cut_face', 'character', 'skeleton_of', 'Armature']

# the corner of the square of an automatic cross-section, as a share of its radius: four spline points here make a curve whose distance from the middle is 1 on average
_CORNER = 0.75


class Armature:
    ''' What an armature knows of itself, for the skeleton, the UV map and the cross-section it shows: its name, the nodes (as controls), the names of its joints, where it is joined, the
        sizes of its nodes, the profile it is swept from (None for a ball) and the direction it leaves its first node in '''

    def __init__(self, name, ctrls, joints, parent, sizes, profile=None, start=None):
        self.name = name
        self.ctrls = ctrls
        self.joints = joints
        self.parent = parent
        self.sizes = sizes
        self.profile = profile
        self.start = start

    def __repr__(self):
        return 'armature(%r, %d nodes)' % (self.name, len(self.ctrls))


def _catmull(p0, p1, p2, p3, t):
    ''' A place on the Catmull-Rom spline between p1 and p2 (t from 0 to 1), as three expressions: the nodes are tuples of expressions '''
    out = []
    for c in range(3):
        out.append(0.5 * (2.0 * p1[c] + (p2[c] - p0[c]) * t + (2.0 * p0[c] - 5.0 * p1[c] + 4.0 * p2[c] - p3[c]) * (t * t) + (3.0 * p1[c] - p0[c] - 3.0 * p2[c] + p3[c]) * (t * t * t)))
    return tuple(out)


def _base_profile(radius):
    ''' The cross-section an armature is given when it has none of its own: a square with spline points at its corners, which is a rounded square that is nearly a circle, `radius` across '''
    from fieldev.stdlib.profile import profile as make
    a = _CORNER * radius
    return make([(a, a), (-a, a), (-a, -a), (a, -a)], smooth=True)


def _profile_radius(shape):
    ''' How big a cross-section is: the mean distance of its outline from the middle of it (1.0 when it cannot be told) '''
    try:
        pts = getattr(shape, 'vertices', None)
        if pts:
            mid = tuple(0.5 * (min(p[c] for p in pts) + max(p[c] for p in pts)) for c in range(3))
            return sum(math.dist(p, mid) for p in pts) / len(pts)
        (x0, y0, _z0), (x1, y1, _z1) = shape._bounds
        return 0.25 * ((x1 - x0) + (y1 - y0))
    except Exception:
        return 1.0


def _sized(place, size):
    ''' A node given as a tuple of numbers, made a point with that size (the scale of its gizmo is how thick the armature is there) '''
    from fieldev.stdlib.handles import gizmo
    from fieldev.stdlib.points import point
    xyz = tuple(place) + (0.0,) * (3 - len(place))
    return gizmo(point(*xyz), scale=(size, size, size))


def _placed_natively(placed, sweep, move):
    ''' `placed` is `sweep` moved by `move` (a new shape: its field).  A sweep that is drawn natively from the numbers of its points (path_extrude: `_sweep_*`) is placed natively as well, the way
        handles.gizmo places one: the viewport carries it by the numbers of the move, in a moment, and does not mesh the field of a sweep (thousands of terms: seconds at every node put down) '''
    if getattr(sweep, '_sweep_ppos', None) is None:
        return
    from fieldev.stdlib.handles import _carry
    _carry(placed, sweep)
    for name in ('_sweep_ppos', '_sweep_prot', '_sweep_pflag', '_sweep_pscale', '_sweep_pradius', '_sweep_pdefault', '_sweep_qpos', '_sweep_qrot', '_sweep_qflag', '_sweep_qscale',
                 '_sweep_qdefault', '_sweep_qclosed', '_sweep_twist'):
        setattr(placed, name, getattr(sweep, name))
    placed._sweep_free = getattr(sweep, '_sweep_free', False)
    placed._sweep_guard = list(getattr(sweep, '_sweep_guard', []))
    placed._sweep_place = ((0.0, 0.0, 0.0), tuple(Shape.wrap(x) for x in move), (Shape.wrap(0.0),) * 3, (Shape.wrap(1.0),) * 3)


def armature(points, radii=None, profile=None, name=None, joints=None, parent=None, twist=0):
    ''' A part of a character: a cross-section swept along a smooth path through the nodes (a path extrude), thick or thin at each node.

            arm = armature([shoulder, elbow, hand], name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"])

        points   the nodes, in order: points (`point(x, y, z)`, dragged with their gizmos) or tuples of numbers.  The scale of a node's gizmo -- the gold ring, 1 for a tuple -- is
                 how big the cross-section is there: the ring is drawn as a circle of the armature's real radius round the node
        radii    the size of the cross-section the armature is given when it has no profile of its own (a number: the radius of the rounded square, 1 by default); or, for nodes that are
                 tuples of numbers, a list with one number for each node (a point has its own size, in its gizmo)
        profile  the cross-section: any 2D shape (a profile made of points, a polygon, a rectangle).  None: a square with spline points, made for the armature.  It is swept from the first
                 node whatever place it is at; a different profile is dropped on this one in the model tree to swap it
        name     what the skeleton calls the armature ("arm.R"); joints: the names of the joints, one for each node (default `name_0`, `name_1` ...)
        parent   the name of the joint this armature hangs from, when its first node is not on a node of another armature
        twist    degrees: the whole cross-section turned about the path '''
    if not isinstance(points, (list, tuple)) or not points:
        raise TypeError('armature(points): a list of nodes (points or tuples of numbers), one or more')
    if profile is not None and radii is not None:
        raise ValueError('armature: radii is the size of the cross-section the armature makes for itself -- a profile of your own has its own size: change its points, or the size of the nodes '
                         '(the gold ring of their gizmos)')
    n = len(points)
    number = 1.0
    if isinstance(radii, (list, tuple)):
        if len(radii) != n:
            raise ValueError('armature: %d nodes but %d radii -- one for each node, or one number for all' % (n, len(radii)))
        given = []
        for k, (p, r) in enumerate(zip(points, radii)):
            r = _radius(r, 'armature: radii[%d]' % k)
            if not isinstance(p, (tuple, list)) or not isinstance(r, (int, float)) or isinstance(r, bool) or not r > 0:
                raise ValueError('armature: radii[%d] -- a list of radii is for nodes that are tuples of numbers (plain numbers above 0); a node that is a point has its size in its own '
                                 'gizmo (the gold ring): give radii as one number' % k)
            given.append(float(r))
        # The size of a node is also how strongly the path leaves it (a node ten times as big as the profile swings the path out and back on itself), so the profile gets the mean size
        # of the radii (the geometric mean) and each node the share of it that is its own: the thickness at a node is still exactly its radius
        number = math.exp(sum(math.log(r) for r in given) / n)
        points = [_sized(p, r / number) for p, r in zip(points, given)]
    elif radii is not None:
        number = _radius(radii, 'armature: radii')
        if not isinstance(number, (int, float)) or isinstance(number, bool) or not number > 0:
            raise ValueError('armature: radii is a number above 0 (the size of the cross-section), or a list of them for nodes that are tuples, not %r' % (radii,))
    ctrls = C.controls(list(points))
    sizes = [number * ctl.scale_expr if ctl.scale_expr is not None else number for ctl in ctrls]
    label = str(name) if name else 'armature'
    if joints is None:
        joints = ['%s_%d' % (label, k) for k in range(n)]
    elif not isinstance(joints, (list, tuple)) or len(joints) != n or len(set(joints)) != n:
        raise ValueError('armature: joints is %d different names, one for each node' % n)
    if n == 1 and profile is not None and radii is None:
        # (a ball with a cross-section of its own is as big as that cross-section is, so that the cross-section can be shown at it and a second node swept from it grows from the same size)
        number = _profile_radius(profile)
        sizes = [number * ctl.scale_expr if ctl.scale_expr is not None else number for ctl in ctrls]
    base, start = None, None
    if n == 1:
        base = profile
        out = round_cone(ctrls[0].expr, ctrls[0].expr, sizes[0], sizes[0])
        for ctl in ctrls:
            if isinstance(ctl.item, Shape):
                try:
                    ctl.item._armature_factor = float(number)
                except AttributeError:
                    pass
    else:
        from fieldev.stdlib import transforms
        from fieldev.stdlib.profile import path_extrude
        base = profile if profile is not None else _base_profile(number)
        way = C.spline(list(points))
        out = path_extrude(base, way, twist)
        # (path_extrude starts the sweep where the 2D shape is -- the origin for a shape in the plane z = 0 -- and draws the path and its points there.  An armature is at its NODES: the sweep is
        # carried by what it was moved, with the nodes' own numbers, so that a node dragged moves the armature, and the nodes are drawn where they are)
        shift = getattr(way, '_weld_shift', None)
        if shift is not None:
            sweep, back = out, C.sub((0.0, 0.0, 0.0), tuple(shift))
            out = transforms.move(out, back)
            _placed_natively(out, sweep, back)
            for item in [way] + list(getattr(way, 'points', [])):
                try:
                    item._weld_shift = None
                except AttributeError:
                    pass
        if len(way.vertices) > 1:
            start = C.unit(C.sub(way.vertices[1], way.vertices[0]))
        # (the viewport draws the ring of a selected node as a circle of the armature's real radius there: the node's scale times the size of the cross-section)
        factor = _profile_radius(base)
        for ctl in ctrls:
            if isinstance(ctl.item, Shape):
                try:
                    ctl.item._armature_factor = float(factor)
                except AttributeError:
                    pass
    # the box the armature fills, for the render region and the export: its nodes, the thickness of the cross-section there (the corners of the square reach a little beyond its radius)
    # and the bend of the curve between them.  A box that holds the armature, not its exact extent
    ref = _profile_radius(base) if base is not None else number
    reach = 1.3 * ref * max([1.0] + [ctl.scale for ctl in ctrls])
    lo = [min(ctl.pos[c] for ctl in ctrls) for c in range(3)]
    hi = [max(ctl.pos[c] for ctl in ctrls) for c in range(3)]
    bend = 0.15 * max(hi[c] - lo[c] for c in range(3))
    out._bounds = (tuple(lo[c] - reach - bend for c in range(3)), tuple(hi[c] + reach + bend for c in range(3)))
    out._bounds_loose = True
    if n > 1 and getattr(out, '_sweep_ppos', None) is None:
        # (a sweep that is not drawn natively from its points -- a profile that is not made of points -- is meshed from its field, which is slow to clear empty space of: over the whole region
        # of the scene it takes seconds at every node put down, so it is meshed over a cube of its own)
        from fieldev.stdlib.custom_resolution import render_hint_for
        hint = render_hint_for(out._bounds[0], out._bounds[1], 2.0 * ref * max(min(ctl.scale for ctl in ctrls), 1e-3))
        if hint is not None:
            out._render_hint = hint
    out._group_pos = [ctl.expr for ctl in ctrls]        # (the points it is made of: the viewport shares their gizmos when the armature is selected as a whole, as it does for a profile's)
    out._armature = Armature(label, ctrls, list(joints), None if parent is None else str(parent), sizes, base, start)
    out._no_gizmo = True                    # (no gizmo() line with numbers of its own: its nodes have them, and the viewport shares them -- View::groupGizmo -- to move, turn and scale the armature)
    out._outline_gizmo = True               # (the model tree's gizmo button gives it a line without numbers, `x = gizmo(x, mode=...)`: when that shared gizmo is shown, off until said; the armature itself is returned)
    return out


def _euler(R):
    ''' The angles (degrees; x, then y, then z: R = Rz * Ry * Rx) of a turn '''
    sy = -R[2][0]
    sy = max(-1.0, min(1.0, sy))
    beta = math.asin(sy)
    if abs(sy) < 1.0 - 1e-9:
        alpha = math.atan2(R[2][1], R[2][2])
        gamma = math.atan2(R[1][0], R[0][0])
    else:
        alpha = 0.0
        gamma = math.atan2(-R[0][1], R[1][1])
    return tuple(math.degrees(a) for a in (alpha, beta, gamma))


def cut_face(one, node=0):
    ''' The cross-section of an armature, shown at its first node: the profile the armature is swept from, as a linked clone of it (`instance`) put where the armature has it -- turned the way the
        armature leaves the node, in the middle of the node -- and drawn with a dot for each of the profile's points.  Pull a dot, double click it, or press the outline to put a point on
        it, and it is the profile that changes, and with it the armature.

            arm_face = cut_face(arm)
            arm_face

        The profile must be made of points (`profile([...])`) for it to have dots; the cross-section an armature makes for itself has none.  Only the first node has one (node=0) '''
    info = getattr(one, '_armature', None)
    if info is None:
        raise TypeError('cut_face(armature): an armature(...), not %r' % (type(one).__name__,))
    if info.profile is None:
        raise ValueError('cut_face: an armature without a profile of its own has no cross-section to show: give it profile=...')
    if node != 0:
        raise ValueError('cut_face: the cross-section is shown at the first node of the armature (node=0), not at node %r' % (node,))
    base = info.profile
    items = getattr(base, 'points', None)
    if not items or not callable(getattr(base, '_remake', None)):
        raise TypeError('cut_face: the profile of the armature is made of points (profile([...])), so that it has a clone to show')
    from fieldev.stdlib.handles import gizmo
    from fieldev.stdlib.instances import instance
    plane = getattr(base, 'plane', None)
    bu, bv = (tuple(plane[1]), tuple(plane[2])) if plane is not None else ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    normal = C.unit(C.cross(bu, bv))
    t0 = info.start if info.start is not None else normal
    # the frame the sweep starts in -- see path_extrude: the profile as it is when the path leaves across it, else turned across the path
    if abs(C.dot(normal, t0)) >= 0.1:
        u0, w0 = bu, bv
    else:
        first = None
        for across in (bu, bv):
            candidate = C.sub(across, C.mul(t0, C.dot(across, t0)))
            if C.dot(candidate, candidate) > 1e-12:
                first = C.unit(candidate)
                break
        if first is None:
            first = bu
        u0, w0 = first, C.cross(t0, first)
    n0 = C.cross(u0, w0)
    R = [[u0[i] * bu[j] + w0[i] * bv[j] + n0[i] * normal[j] for j in range(3)] for i in range(3)]
    places = []
    for p in items:
        xyz = getattr(p, 'xyz', None)
        if xyz is None:
            xyz = tuple(p) + (0.0,) * (3 - len(p))
        places.append(tuple(C.value_of(v) for v in xyz))
    middle = tuple(0.5 * (min(q[i] for q in places) + max(q[i] for q in places)) for i in range(3))
    node0 = tuple(info.ctrls[0].pos)
    move = tuple(node0[i] - middle[i] for i in range(3))
    return gizmo(instance(base), move=move, rotate=_euler(R))


def character(armatures, blend=3, symmetric=None):
    ''' The body made of armatures and feature models: joined as one with a smooth blend of `blend` mm where they meet (0: none), and, with `symmetric` "x", "y" or "z", the other half as the mirror
        image (the parts are modelled on one side of the plane; the parts that lie across it, a spine and a head, are in both) '''
    if not isinstance(armatures, (list, tuple)) or not armatures:
        raise TypeError('character(armatures): a list of armatures (and feature models), one or more')
    body = F.union_all(list(armatures), blend)
    body._parts = list(armatures)               # (the parts the UV map by armature unwraps the body by: armatures and feature models)
    boxes = [getattr(p, '_bounds', None) for p in armatures]
    if all(boxes):
        body._bounds = (tuple(min(b[0][c] for b in boxes) for c in range(3)), tuple(max(b[1][c] for b in boxes) for c in range(3)))
        body._bounds_loose = True
    if symmetric is None:
        return body
    from fieldev.stdlib import transforms
    mirror = {'x': 'symmetric_x', 'y': 'symmetric_y', 'z': 'symmetric_z'}.get(str(symmetric).lower())
    if mirror is None:
        raise ValueError('character: symmetric is "x", "y" or "z", not %r' % (symmetric,))
    out = getattr(transforms, mirror)(body)
    box = getattr(body, '_bounds', None)
    if box:
        # (the half on the positive side and its mirror image: the box is as far on the negative side as the half is on the positive)
        a = 'xyz'.index(str(symmetric).lower())
        m = max(box[1][a], 0.0)
        lo, hi = list(box[0]), list(box[1])
        lo[a], hi[a] = -m, m
        out._bounds = (tuple(lo), tuple(hi))
        out._bounds_loose = True
    out._parts = list(armatures)
    out._symmetric_axis = str(symmetric).lower()
    return out


def skeleton_of(armatures, mirror=None, plane=0.0, join=None):
    ''' The joints of the armatures, for `export_mesh(..., skeleton=...)`: a joint at each node, named by the armature's `joints`, each hanging from the one before it.  An armature whose first node is
        within `join` mm of a joint already made (default: half a millimetre: the same point, or the same place typed again) is a branch of it: that joint is its first, and its other nodes hang from it.
        An armature that is not on any joint hangs from the joint it names with `parent=`.  `mirror` ("x", "y" or "z"): the joints whose name ends with ".R" get a ".L" one across that plane '''
    out = []
    by_name = {}
    for k, one in enumerate(armatures):
        info = getattr(one, '_armature', None)
        if info is None and getattr(one, '_feature_model', None) is not None:
            continue                            # (feature models are skin, not bone: they are skinned to the nearest joints)
        if info is None:
            raise TypeError('skeleton_of: armature(...)s, not %r' % (type(one).__name__,))
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
                raise ValueError('skeleton_of: the armature %r hangs from %r, which is not a joint of an earlier armature' % (info.name, info.parent))
            anchor = info.parent
        elif out:
            raise ValueError('skeleton_of: the armature %r begins at %s, which is not on a joint of an earlier armature: say where it is joined with parent="a joint name"' % (
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


# What the menus offer them for (see fieldev.kinds.takes): an armature is made of points and a profile, a character and a skeleton of armatures (bodies)
armature._takes = _declare({"point", "profile"}, [{"point"}])
armature._makes_no_gizmo = True
armature._makes_outline_gizmo = True
character._takes = _declare({"solid"}, [{"solid"}])
skeleton_of._takes = _declare({"solid"}, [{"solid"}])
