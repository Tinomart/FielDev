'''
Armatures: a character made of parts, each a path of nodes with a cross-section, and the skeleton that goes with them.

    shoulder = point(18, 0, 138)                            # a node: a point (the scale of its gizmo is how strongly the curve leaves it)
    elbow = point(31, 0, 113)
    hand = point(37, 8, 92)
    arm = armature([shoulder, elbow, hand], sizes=[1, 0.75, 0.58], name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"])
    spine = armature([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5], name="spine", joints=["hips", "spine", "chest", "neck"])
    face = cut_face(arm)                                    # the cross-section of the arm, shown at its first node: its points are the profile's
    hero = character([spine, arm, ...], blend=4, symmetric="x")          # the body: the parts joined with a blend, and the left half as the mirror image
    export_mesh(hero, "hero.glb", symmetric="x", skeleton=skeleton_of([spine, arm, ...], mirror="x"))

An ARMATURE is a path extruded: a cross-section swept along a smooth curve through its nodes (the curve is a Catmull-Rom spline through the nodes, so the armature bends smoothly), thicker or
thinner at each node, and every number in it is an expression of the nodes, so that a node dragged in the viewport moves the armature with it at once.  The cross-section is a PROFILE:
by default one that is made for the armature -- a square whose four corners are spline points, so that it is nearly round, with a radius of `radii` (1 by default) -- or any 2D shape of your
own, `armature([...], profile=my_profile)`: a profile you made from points, a polygon, a rectangle.  The profile is the same for the whole armature, and the size of a node (`sizes`: the circle round the node, the real radius there)
makes it bigger or smaller there (the scale of a node's gizmo, which shows when the point itself is selected, is not the thickness: it is how strongly the path leaves the node, and a node with a scale many times 1 swings the path out and back on
itself); the profile is a model of its own, so a different one is swapped in by dropping it on the profile the armature uses in the model tree.  Where the profile
is does not matter: the armature is swept from the first node.  `cut_face(armature)` shows the profile there, as a linked clone (`instance`) turned the way the armature leaves the node, with a dot
for each of the profile's points: pull a dot, and the profile -- and so the whole armature -- changes with it.

The ENDS of an armature are round where the node there is a spline point -- every node is one unless it says `point(..., smooth=False)` -- a dome as thick as the armature is at that node; a node
that is a corner ends the armature flat, with the face of the cross-section.  The size of a node is how thick the armature is there, exactly: a node of size 2 is twice as thick as one of size 1.
A character joins its armatures with a blend as wide as each one is thick (`blend="auto"`, the default), so that a branch grows out of its parent the way a limb grows out of a body, whatever
the size of the character; `blend=3` is 3 mm everywhere.

A BRANCH is a list among the nodes: `armature([hip, knee, ankle, [toe_a, toe_b], heel_end])` -- it hangs from the node before it (the ankle), is swept from there with the same cross-section and the same
sizes and joints lists.  It is part of the armature -- one profile, one cross-section, one skeleton, and ONE field: the field of the whole armature blends the branch into the piece it hangs from,
over a width as thick as the branch is (a branch is not a second tube united with the first afterwards).

The nodes of an armature are the joints of the skeleton: `skeleton_of` makes a joint for each, named by `joints=` (or `<name>_0`, `<name>_1` ...), each hanging from the one before it (the first
node of a branch: from the node it branches from).  An armature
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
    ''' What an armature knows of itself, for the skeleton, the UV map and the cross-section it shows: its name, the nodes (as controls, in the order the script lists them, the nodes of a branch
        where the branch is written), the names of its joints, where it is joined, the sizes of its nodes, the profile it is swept from (None for a ball) and the direction it leaves its first
        node in.  `parents` says which node each hangs from (-1: the first), `chains` the nodes of every piece that is swept in one go: the chain from the first node, then each branch, a branch
        beginning with the node it hangs from '''

    def __init__(self, name, ctrls, joints, parent, sizes, profile=None, start=None, multipliers=None, parents=None, chains=None, pieces=None, widths=None):
        self.name = name
        self.ctrls = ctrls
        self.joints = joints
        self.parent = parent
        self.sizes = sizes
        self.multipliers = multipliers if multipliers is not None else [1.0] * len(ctrls)         # (how big the cross-section is at each node: see `sizes` of armature)
        self.profile = profile
        self.start = start
        self.parents = parents if parents is not None else list(range(-1, len(ctrls) - 1))
        self.chains = chains if chains is not None else [list(range(len(ctrls)))]
        self.pieces = pieces            # (the shape of each chain, where there are branches: `character` joins them with a blend as wide as each branch is thick -- `widths`)
        self.widths = widths

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


_NATIVE = ('_sweep_ppos', '_sweep_prot', '_sweep_pflag', '_sweep_pscale', '_sweep_pradius', '_sweep_pdefault', '_sweep_qpos', '_sweep_qrot', '_sweep_qflag', '_sweep_qscale',
           '_sweep_qdefault', '_sweep_qclosed', '_sweep_twist', '_sweep_qsize')


def _carry_native(target, sweep):
    ''' What makes `sweep` a sweep that the viewport draws natively from the numbers of its points (path_extrude: `_sweep_*`), on to `target`, a shape made of it.  False when it is not one '''
    if getattr(sweep, '_sweep_ppos', None) is None:
        return False
    from fieldev.stdlib.handles import _carry
    _carry(target, sweep)
    for name in _NATIVE:
        setattr(target, name, getattr(sweep, name))
    target._sweep_free = getattr(sweep, '_sweep_free', False)
    for name in ('_sweep_round', '_sweep_offset', '_sweep_across', '_sweep_inner', '_sweep_place'):
        if getattr(sweep, name, None) is not None:
            setattr(target, name, getattr(sweep, name))
    target._sweep_guard = list(getattr(sweep, '_sweep_guard', []))
    return True


def _placed_natively(placed, sweep, move):
    ''' `placed` is `sweep` moved by `move` (a new shape: its field).  A sweep that is drawn natively from the numbers of its points (path_extrude: `_sweep_*`) is placed natively as well, the way
        handles.gizmo places one: the viewport carries it by the numbers of the move, in a moment, and does not mesh the field of a sweep (thousands of terms: seconds at every node put down) '''
    if _carry_native(placed, sweep):
        placed._sweep_place = ((0.0, 0.0, 0.0), tuple(Shape.wrap(x) for x in move), (Shape.wrap(0.0),) * 3, (Shape.wrap(1.0),) * 3)


# how wide the blend of a character is, as a share of the thickness of the armature that is joined: about a third of it is added at the inside of the joint, which is what makes it grow out
_BLEND = 1.2



def _thickness(one):
    ''' How thick an armature is, as a number: the size of its cross-section times the mean size of its nodes (a ball: its radius); None for what is not an armature (a feature model) '''
    info = getattr(one, '_armature', None)
    if info is None:
        return None
    if info.profile is None:
        return C.value_of(Shape.wrap(info.sizes[0]))
    mean = sum(max(C.value_of(Shape.wrap(m)), 1e-3) for m in info.multipliers) / len(info.multipliers)
    return _profile_radius(info.profile) * mean


def _whole(one, width=None):
    ''' An armature with branches as one shape: its pieces joined with a blend as wide as each branch is thick -- or `width`, when one is given (0: none).  Anything else is itself '''
    info = getattr(one, '_armature', None)
    pieces = getattr(info, 'pieces', None)
    if not pieces or len(pieces) < 2:
        return one
    out = pieces[0]
    for piece, own in zip(pieces[1:], info.widths[1:]):
        out = F.smooth_union(out, piece, own if width is None else width)
    return out


def _joined(parts):
    ''' The parts as one body, each joined to the ones before it with a blend as wide as it is thick (a part that is not an armature: as wide as the armatures are thick, on average).  The branches
        of an armature are joined to it the same way '''
    sizes = [_thickness(p) for p in parts]
    known = [s for s in sizes if s]
    fallback = sum(known) / len(known) if known else 3.0
    out = _whole(parts[0])
    for one, size in zip(parts[1:], sizes[1:]):
        out = F.smooth_union(out, _whole(one), (size or fallback) * _BLEND)
    return out


def _node_tree(points):
    ''' The nodes of an armature as the script lists them -- a list among them is a BRANCH, which hangs from the node before it -- and how they hang together: (nodes, parents, chains).
        `nodes` are all of them in the order they are written, a branch's where it is written; `parents[i]` is the node i hangs from (-1: the first); `chains` are the pieces that are swept in
        one go: the nodes of the main chain, then each branch, a branch beginning with the node it hangs from, so that it is swept from there '''
    nodes, parents, chains = [], [], []

    def walk(items, start):
        chain = [] if start is None else [start]
        chains.append(chain)
        previous = start
        for item in items:
            if isinstance(item, list):
                if previous is None:
                    raise TypeError('armature: a list among the nodes is a branch and hangs from the node before it, so the first of the nodes cannot be one')
                if not item:
                    raise TypeError('armature: a branch is a list of nodes, one or more')
                if all(isinstance(e, (int, float)) and not isinstance(e, bool) for e in item):
                    raise TypeError('armature: a node is a point(x, y, z) or a tuple (x, y, z), not a list of numbers: a list among the nodes is a branch, a list of nodes that hangs from the node before it')
                walk(item, previous)
            else:
                nodes.append(item)
                parents.append(-1 if previous is None else previous)
                previous = len(nodes) - 1
                chain.append(previous)

    walk(list(points), None)
    return nodes, parents, chains


def armature(points, radii=None, profile=None, name=None, joints=None, parent=None, twist=0, sizes=None):
    ''' A part of a character: a cross-section swept along a smooth path through the nodes (a path extrude), thick or thin at each node.

            arm = armature([shoulder, elbow, hand], sizes=[1, 0.75, 0.58], name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"])
            foot = armature([knee, ankle, [toe_a, toe_b], heel], name="foot")           # the toes branch from the ankle

        points   the nodes, in order: points (`point(x, y, z)`, dragged with their gizmos) or tuples of numbers.  A LIST among them is a branch: it hangs from the node before it and is swept from
                 there with the same cross-section, as a part of this armature (a branch can have branches).  The scale of a point's gizmo is how strongly the curve leaves it (its influence,
                 1 by default: it shows when that point is selected); how thick the armature is at a node is `sizes`, not the point's scale
        radii    the size of the cross-section the armature is given when it has no profile of its own (a number: the radius of the rounded square, 1 by default); or a list with one
                 number for each node, the radius at that node.  `radii`, `sizes` and `joints` list every node in the order it is written -- the nodes of a branch where the branch is written
        sizes    how big the cross-section is at each node, as a number of its own -- a list, one number (or var()) for each node, 1 the cross-section as it is -- on top of `radii`.  The circle round a
                 node, drawn with the armature's real radius there, is what changes it (drag it, or Shift + wheel over the node)
        profile  the cross-section: any 2D shape (a profile made of points, a polygon, a rectangle).  None: a square with spline points, made for the armature.  It is swept from the first
                 node whatever place it is at; a different profile is dropped on this one in the model tree to swap it
        name     what the skeleton calls the armature ("arm.R"); joints: the names of the joints, one for each node (default `name_0`, `name_1` ...)
        parent   the name of the joint this armature hangs from, when its first node is not on a node of another armature
        twist    degrees: the whole cross-section turned about the path
        The cross-section says how the size of a node sizes it: `sizing=` of the 2D shape -- `profile(..., sizing="offset")`, `ring(..., sizing="offset")`, `with_sizing` --, "scale" where it says
        nothing and for the cross-section the armature makes for itself (see `with_sizing`)

        The ends are round at a node that is a spline point (every node is, unless it says `point(..., smooth=False)`; the nodes put down in the viewport are corners except the first and the
        last) and flat at a corner.  The cross-section at the first node is turned across the path, so that both ends are square to it.  A branch begins round, inside the node it hangs from.  A branch is blended into the piece it hangs from, over a width as thick as the branch is -- what is exported.  While a node is dragged every chain is drawn from the nodes at once, ring by ring, each as a tube of its own (a quick picture to follow the hand by); the mesh that stays once it is let go is the mesh of the
        field, which has the blend '''
    if not isinstance(points, (list, tuple)) or not points:
        raise TypeError('armature(points): a list of nodes (points or tuples of numbers), one or more; a list among them is a branch')
    nodes, parents, chains = _node_tree(points)
    n = len(nodes)
    number = 1.0
    shares = [1.0] * n              # (each node's share of the size of the cross-section, where a radius is given for each)
    if isinstance(radii, (list, tuple)):
        if len(radii) != n:
            raise ValueError('armature: %d nodes but %d radii -- one for each node, or one number for all' % (n, len(radii)))
        given = []
        for k, r in enumerate(radii):
            r = _radius(r, 'armature: radii[%d]' % k)
            if not isinstance(r, (int, float)) or isinstance(r, bool) or not r > 0:
                raise ValueError('armature: radii[%d] is a plain number above 0 (the radius at that node), not %r' % (k, r))
            given.append(float(r))
        # The cross-section gets the mean size of the radii (the geometric mean) and each node the share of it that is its own: the thickness at a node is exactly its radius
        number = math.exp(sum(math.log(r) for r in given) / n)
        shares = [r / number for r in given]
    elif radii is not None:
        number = _radius(radii, 'armature: radii')
        if not isinstance(number, (int, float)) or isinstance(number, bool) or not number > 0:
            raise ValueError('armature: radii is a number above 0 (the size of the cross-section), or a list of them, one for each node, not %r' % (radii,))
    if profile is not None and radii is not None:
        raise ValueError('armature: radii is the size of the cross-section the armature makes for itself -- a profile of your own has its own size: change its points, or `sizes`')
    # How thick the armature is at each node: its radius (`radii`) times its size (`sizes`, a number of its own -- not the scale of the point, which is the influence of the point on the curve)
    from fieldev.stdlib.profile import _section_sizes
    node_sizes = _section_sizes(sizes, n, 'armature')[0]
    multipliers = [sh * sz for sh, sz in zip(shares, node_sizes)]
    ctrls = C.controls(nodes)
    thickness = [number * m for m in multipliers]
    label = str(name) if name else 'armature'
    if joints is None:
        joints = ['%s_%d' % (label, k) for k in range(n)]
    elif not isinstance(joints, (list, tuple)) or len(joints) != n or len(set(joints)) != n:
        raise ValueError('armature: joints is %d different names, one for each node' % n)
    if n == 1 and profile is not None and radii is None:
        # (a ball with a cross-section of its own is as big as that cross-section is, so that the cross-section can be shown at it and a second node swept from it grows from the same size)
        number = _profile_radius(profile)
        thickness = [number * m for m in multipliers]
    base, start = None, None
    pieces, piece_widths = None, None
    if n == 1:
        base = profile
        out = round_cone(ctrls[0].expr, ctrls[0].expr, thickness[0], thickness[0])
        for k, ctl in enumerate(ctrls):
            if isinstance(ctl.item, Shape):
                try:
                    ctl.item._armature_factor = float(number * shares[k])
                    ctl.item._armature_size = node_sizes[k]         # (the number the circle round the node is bound to: the viewport drags it)
                    ctl.item._armature_size_value = float(C.value_of(node_sizes[k]))
                except AttributeError:
                    pass
        # A ball with the cross-section of a profile of points carries what the viewport needs to draw the sweep that the NEXT node makes of it at the click, before the script has run: the profile, the
        # node as a path of one, how it is placed (Shape::previewSweepNode).  It is not drawn from them: a path of one node is no sweep
        if base is not None and getattr(base, '_ctrl_pos', None) and getattr(base, 'plane', None) is not None:
            from fieldev.stdlib.handles import _carry
            seed = C.spline([nodes[0]])
            if getattr(seed, '_ctrl_pos', None):
                out._sweep_ppos, out._sweep_prot = base._ctrl_pos, base._ctrl_rot
                out._sweep_pflag, out._sweep_pscale, out._sweep_pdefault = base._ctrl_flag, base._ctrl_scale, base._ctrl_default
                out._sweep_pradius = base._ctrl_radius
                out._sweep_qpos, out._sweep_qrot = seed._ctrl_pos, seed._ctrl_rot
                out._sweep_qflag, out._sweep_qscale, out._sweep_qdefault = seed._ctrl_flag, seed._ctrl_scale, seed._ctrl_default
                out._sweep_qsize = [Shape.wrap(m) for m in multipliers]
                out._sweep_qclosed = False
                out._sweep_twist = Shape.wrap(twist)
                out._sweep_round = (ctrls[0].flag != 0, True)
                out._sweep_offset = (getattr(base, '_sizing', None) or 'scale') == 'offset'
                out._sweep_across = True
                po, pu, pv = base.plane
                cx, cy = getattr(base, '_centre2d', (0.0, 0.0))
                middle = tuple(po[k] + cx * pu[k] + cy * pv[k] for k in range(3))
                out._sweep_place = ((0.0, 0.0, 0.0), tuple(Shape.wrap(ctrls[0].expr[k] - middle[k]) for k in range(3)), (Shape.wrap(0.0),) * 3, (Shape.wrap(1.0),) * 3)
                out._sweep_guard = []
                out._sweep_seed = True
    else:
        from fieldev.stdlib import transforms
        from fieldev.stdlib.profile import path_extrude
        base = profile if profile is not None else _base_profile(number)
        # (every chain of nodes that has two or more is swept from its first node: the main chain, and each branch from the node it hangs from.  The cross-section is the same for all of them)
        swept = [chain for chain in chains if len(chain) > 1]
        sweeps, placed, ways = [], [], []
        across_ref = _profile_radius(base)
        for chain in swept:
            way = C.spline([nodes[i] for i in chain])
            # (the ends: a dome at a node that is a spline point, the flat face of the cross-section at a corner.  path_extrude makes the dome -- the cross-section itself shrinking along a quarter of a
            # circle -- in the field and for the viewport by the same law.  A branch begins round: its start is inside the node it hangs from)
            rounds = (ctrls[0].flag != 0 if chain is chains[0] else True, ctrls[chain[-1]].flag != 0)
            # (the field of a sweep of an armature with branches is the small one -- see `cheap` of path_extrude --, for what is made of it; every chain is drawn natively from its nodes, branches too)
            sweep = path_extrude(base, way, twist, ends=rounds, across=True, sizes=[multipliers[i] for i in chain], cheap=len(swept) > 1)
            moved = sweep
            # (path_extrude starts the sweep where the 2D shape is -- the origin for a shape in the plane z = 0 -- and draws the path and its points there.  An armature is at its NODES: the sweep is
            # carried by what it was moved, with the nodes' own numbers, so that a node dragged moves the armature, and the nodes are drawn where they are)
            shift = getattr(way, '_weld_shift', None)
            if shift is not None:
                # (carried back from the profile to where the first node of the chain IS -- by the node's own numbers, not by numbers worked out when the script ran: the viewport moves the sweep to the
                # profile by where that node is now, and a node dragged, or the armature moved as a whole, would leave the tube behind)
                first = ctrls[chain[0]]
                middle = tuple(float(shift[k]) + first.pos[k] for k in range(3))
                back = tuple(first.expr[k] - middle[k] for k in range(3))
                moved = transforms.move(sweep, back)
                _placed_natively(moved, sweep, back)
                for item in [way] + list(getattr(way, 'points', [])):
                    try:
                        item._weld_shift = None
                    except AttributeError:
                        pass
            sweeps.append(sweep)
            placed.append(moved)
            ways.append(way)
        core = sweeps[0]
        out = placed[0]
        if len(placed) > 1:
            # (the armature is the union of its pieces, as the viewport draws it -- ring by ring, each piece as it is swept; `character` joins the pieces with a blend as wide as each branch is thick, so that a
            # branch grows out of the body the way a limb does)
            across_ref = _profile_radius(base)
            piece_widths = [0.0]
            for chain in swept[1:]:
                own = chain[1:]
                mean = sum(max(C.value_of(Shape.wrap(multipliers[i])), 1e-3) for i in own) / len(own)
                piece_widths.append(across_ref * mean * _BLEND)
            # (one field: each branch is blended into what it hangs from, over a width as thick as the branch is -- what is exported.  While a node is dragged the viewport draws every chain from its nodes at once, each as a tube of its own;
            # the mesh it shows after is the mesh of this field (`_sweep_blend`, the width of the blend as a multiple of the thickness of the branch, tells the viewport that the sweep has blended branches))
            pieces = placed
            out = placed[0]
            for piece, own in zip(placed[1:], piece_widths[1:]):
                out = F.smooth_union(out, piece, own)
            if _carry_native(out, placed[0]):
                out._sweep_branches = list(sweeps[1:])
                out._sweep_blend = _BLEND
        if len(ways[0].vertices) > 1:
            start = C.unit(C.sub(ways[0].vertices[1], ways[0].vertices[0]))
        # (the viewport draws the ring of every node of a selected armature as a circle of the armature's real radius there: the node's size times the size of the cross-section)
        factor = _profile_radius(base)
        inner = getattr(core, '_sweep_inner', 0.0)
        if getattr(core, '_sweep_offset', False) and inner > 1e-9:
            factor = inner                  # (an offset armature is as thick as the widest circle of its cross-section: that is the ring)
        for k, ctl in enumerate(ctrls):
            if isinstance(ctl.item, Shape):
                try:
                    ctl.item._armature_factor = float(factor * shares[k])
                    ctl.item._armature_size = node_sizes[k]
                    ctl.item._armature_size_value = float(C.value_of(node_sizes[k]))
                except AttributeError:
                    pass
    # the box the armature fills, for the render region and the export: its nodes, the thickness of the cross-section there (the corners of the square reach a little beyond its radius)
    # and the bend of the curve between them.  A box that holds the armature, not its exact extent
    ref = _profile_radius(base) if base is not None else number
    reach = 1.3 * ref * max([1.0] + [C.value_of(Shape.wrap(m)) for m in multipliers] + [ctl.scale for ctl in ctrls])
    lo = [min(ctl.pos[c] for ctl in ctrls) for c in range(3)]
    hi = [max(ctl.pos[c] for ctl in ctrls) for c in range(3)]
    bend = 0.15 * max(hi[c] - lo[c] for c in range(3))
    out._bounds = (tuple(lo[c] - reach - bend for c in range(3)), tuple(hi[c] + reach + bend for c in range(3)))
    out._bounds_loose = True
    if n > 1 and getattr(out, '_sweep_ppos', None) is None:
        # (a sweep that is not drawn natively from its points -- a profile that is not made of points -- is meshed from its field, which is slow to clear empty space of: over the whole region
        # of the scene it takes seconds at every node put down, so it is meshed over a cube of its own)
        from fieldev.stdlib.custom_resolution import render_hint_for
        hint = render_hint_for(out._bounds[0], out._bounds[1], 2.0 * ref * max(min(C.value_of(Shape.wrap(m)) for m in multipliers), 1e-3))
        if hint is not None:
            out._render_hint = hint
    out._group_pos = [ctl.expr for ctl in ctrls]        # (the points it is made of: the viewport shares their gizmos when the armature is selected as a whole, as it does for a profile's)
    out._armature = Armature(label, ctrls, list(joints), None if parent is None else str(parent), thickness, base, start, multipliers, parents, chains, pieces, piece_widths)
    out._kind = 'solid'                     # (an armature is a body: said here, so that nothing probes the field of a sweep -- thousands of terms -- to find it out)
    out._no_gizmo = True                    # (no gizmo() line with numbers of its own: its nodes have them, and the viewport shares them -- View::groupGizmo -- to move, turn and scale the armature)
    out._outline_gizmo = True               # (the model tree's gizmo button gives it a line without numbers, `x = gizmo(x, mode=...)`: when that shared gizmo is shown, off until said; the armature itself is returned)
    return out


def _euler(R):
    ''' The angles (degrees; x, then y, then z) a gizmo turns by to make the turn R: the inverse of the gizmo's own matrices -- Rz * Ry * Rx, with Rx and Rz the right-hand turns and the library's Ry
        the opposite one about y -- the same as the viewport's gizmoEuler, so that what the viewport draws and what the library evaluates are the one turn '''
    sy = max(-1.0, min(1.0, R[2][0]))
    beta = math.asin(sy)
    if abs(sy) < 1.0 - 1e-9:
        alpha = math.atan2(R[2][1], R[2][2])
        gamma = math.atan2(R[1][0], R[0][0])
    else:
        alpha = 0.0
        gamma = math.atan2(-R[0][1] * sy, R[1][1])
    return tuple(math.degrees(a) for a in (alpha, beta, gamma))


def _live_placement(info, axes, middle, move, rotate):
    ''' Where the cross-section shown at the first node is (`cut_face`), as EXPRESSIONS of the numbers of the nodes, so that it follows them while one of them is dragged: the script is not run again
        until the drag is over, and numbers worked out when it ran would stay where they were.  The place is the first node, and the turn is the direction the armature leaves it in -- the chord to
        the first point the kernel puts on the curve (`trace`), worked out here the way the kernel does it -- with the profile turned the least that puts it across that direction (`_across_frame`).
        (move, rotate) as expressions; None where that cannot be done in the same way as the numbers are (a node that has a rotation, a profile that lies along the direction ...): the numbers of the
        last run are used then.  The expressions are checked against the numbers (`move`, `rotate`) and used only where they are the same '''
    from fieldev.stdlib.curves import PIECES
    bu, bv, normal = axes
    chain = next((c for c in info.chains if len(c) > 1), None)
    if chain is None:
        return None
    ctl = [info.ctrls[i] for i in chain[:3]]
    if any(c.turned for c in ctl[:2]):
        return None
    P = [c.expr for c in ctl]

    def add(a, b):
        return tuple(a[i] + b[i] for i in range(3))

    def sub(a, b):
        return tuple(a[i] - b[i] for i in range(3))

    def mul(a, k):
        return tuple(a[i] * k for i in range(3))

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

    smooth0, smooth1 = ctl[0].smooth(True), ctl[1].smooth(True)
    chord = sub(P[1], P[0])
    if not smooth0 and not smooth1:
        d = chord                                   # (a straight piece: the next vertex is the next node)
    else:
        s0 = ctl[0].scale_expr if ctl[0].scale_expr is not None else ctl[0].scale
        s1 = ctl[1].scale_expr if ctl[1].scale_expr is not None else ctl[1].scale
        a_vec = mul(chord, s0) if smooth0 else chord                                      # (the tangent at the first node, or the chord)
        if smooth1:
            b_vec = mul(sub(P[2], P[0]), 0.5 * s1) if len(ctl) >= 3 else mul(chord, s1)
        else:
            b_vec = chord
        step = 1.0 / PIECES
        m = 1.0 - step
        d = add(add(mul(a_vec, m * m * step), mul(sub(chord, mul(b_vec, 1.0 / 3.0)), 3.0 * m * step * step)), mul(chord, step ** 3))
    length = dot(d, d).sqrt()
    t0 = tuple(d[i] / length for i in range(3))
    dd = dot(normal, t0)
    value = C.value_of(dd)
    if abs(value) < 0.1:
        return None
    sign = 1.0 if value > 0 else -1.0
    target = mul(t0, sign)
    c = dd * sign
    a = cross(normal, target)

    def turn(v):
        return add(add(mul(v, c), cross(a, v)), mul(a, dot(a, v) / (c + 1.0)))
    u0, w0 = turn(bu), turn(bv)
    n0 = cross(u0, w0)
    R = [[u0[i] * bu[j] + w0[i] * bv[j] + n0[i] * normal[j] for j in range(3)] for i in range(3)]
    sy = R[2][0]
    if abs(C.value_of(sy)) >= 1.0 - 1e-9:
        return None
    deg = 180.0 / math.pi
    angles = (R[2][1].atan2(R[2][2]) * deg, sy.asin() * deg, R[1][0].atan2(R[0][0]) * deg)
    shift = tuple(P[0][i] - middle[i] for i in range(3))
    if max(abs(C.value_of(shift[i]) - move[i]) for i in range(3)) > 1e-6 * (1.0 + max(abs(v) for v in move)):
        return None
    if max(abs(C.value_of(angles[i]) - rotate[i]) for i in range(3)) > 1e-4:
        return None
    # (the turn as the gizmo makes it from the angles: what the images of the points of the cross-section are placed by, and what the viewport places its dots by)
    from fieldev.stdlib.symmetries import _turn_matrix
    turn = _turn_matrix(angles)
    return shift, angles, tuple(Shape.wrap(turn[i][j]) for i in range(3) for j in range(3))


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
    # the frame the sweep starts in -- see path_extrude: the profile turned the least that puts it across the path, and when its plane holds the path, turned across it
    from fieldev.stdlib.profile import _across_frame
    turned_first = _across_frame(bu, bv, t0)
    if turned_first is not None:
        u0, w0 = turned_first
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
    # (the angles of a gizmo are the ones the viewport itself writes for a turn -- Shape::gizmoRotation and gizmoEuler of the app: x, then y, then z, the x and z turns right-handed and the y turn the other way.  The
    # first version of this negated all three, which is right for a turn about y alone and wrong for an armature that leans in two directions: its face was tilted against the path, as a probe of such an armature showed)
    rotate = _euler(R)
    # (the place as expressions of the nodes' numbers, so that the cross-section follows a node that is dragged -- the script runs again when the drag is over -- where that can be done exactly)
    live = _live_placement(info, (bu, bv, normal), middle, move, rotate)
    matrix = None
    if live is not None:
        move, rotate, matrix = live
    clone = gizmo(instance(base), move=move, rotate=rotate)
    if matrix is not None:
        # (the outline of the clone follows the nodes through the expressions; its dots are drawn through a map, which is numbers of the last run unless it is given as expressions too: the viewport
        # works the map out from them while a node is dragged -- Shape::gizmoMap)
        shift = tuple(Shape.wrap(v) for v in move)
        for dot in getattr(clone, '_image_dots', None) or []:
            dot._symmetry_live = (matrix, shift)
    return clone


def _own_region(body):
    ''' A body of armatures is meshed over a cube of its own, at the resolution the scene has, and not over the whole region of the scene: the field of a sweep is slow to clear empty space of, and
        the memory it takes grows with the region (four characters of a few mm each, side by side, took more than 14 GB over a region of 70 mm).  The hint is (box, resolution, side, scene resolution):
        a scene resolution above 0 says that the resolution follows the scene's '''
    box = getattr(body, '_bounds', None)
    if box is None:
        return
    ext = max(box[1][i] - box[0][i] for i in range(3))
    if not ext > 0:
        return
    grow = 0.1 * ext
    body._render_hint = (tuple(v - grow for v in box[0]), tuple(v + grow for v in box[1]), 1.0, ext + 2.0 * grow, 1.0)


def _join_widths(parts):
    """ How wide each part of a character is blended into the ones before it (the first: 0): as thick as the part is -- or, for a part that is not an armature, as thick as the armatures are on
        average -- times `_BLEND`, the way `_joined` does.  The viewport meshes a character natively from these numbers (`_group_*`) """
    sizes = [_thickness(p) for p in parts]
    known = [s for s in sizes if s]
    fallback = sum(known) / len(known) if known else 3.0
    return [0.0] + [float((size or fallback) * _BLEND) for size in sizes[1:]]


def _describe_group(target, parts, blend, symmetric):
    """ What the viewport meshes a character from, natively and in a moment, at every render: its parts, how wide each is blended into the ones before it, the width the branches of its armatures are
        blended with when one is given (-1: as thick as each branch is), and the plane the other half is the mirror image in.  A character whose blend is not a plain number is left to its field """
    try:
        if isinstance(blend, str):
            joins, given = _join_widths(parts), -1.0
        else:
            given = float(blend)
            joins = [0.0] + [given] * (len(parts) - 1)
    except (TypeError, ValueError):
        return
    target._group_parts = list(parts)
    target._group_joins = joins
    target._group_blend = given
    target._group_mirror = str(symmetric).lower() if symmetric else ''


def character(armatures, blend="auto", symmetric=None):
    ''' The body made of armatures and feature models: joined as one with a smooth blend where they meet, and, with `symmetric` "x", "y" or "z", the other half as the mirror
        image (the parts are modelled on one side of the plane; the parts that lie across it, a spine and a head, are in both)

        blend  "auto" (the default): each armature is joined with a blend as wide as it is thick, so that a branch grows out of its parent the way a limb grows out of a body, whatever the
               size of the character; or a number: a blend of that many mm everywhere (0: none) '''
    if not isinstance(armatures, (list, tuple)) or not armatures:
        raise TypeError('character(armatures): a list of armatures (and feature models), one or more')
    if isinstance(blend, str):
        if blend != "auto":
            raise ValueError('character: blend is "auto" or a number of mm, not %r' % (blend,))
        body = _joined(list(armatures))
    else:
        body = F.union_all([_whole(p, blend) for p in armatures], blend)
    body._parts = list(armatures)               # (the parts the UV map by armature unwraps the body by: armatures and feature models)
    _describe_group(body, armatures, blend, None)
    boxes = [getattr(p, '_bounds', None) for p in armatures]
    if all(boxes):
        body._bounds = (tuple(min(b[0][c] for b in boxes) for c in range(3)), tuple(max(b[1][c] for b in boxes) for c in range(3)))
        body._bounds_loose = True
        _own_region(body)
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
        _own_region(out)
    out._parts = list(armatures)
    out._symmetric_axis = str(symmetric).lower()
    _describe_group(out, armatures, blend, symmetric)
    return out


def skeleton_of(armatures, mirror=None, plane=0.0, join=None):
    ''' The joints of the armatures, for `export_mesh(..., skeleton=...)`: a joint at each node, named by the armature's `joints`, each hanging from the one before it -- the first node of a branch
        from the node it branches from.  An armature whose first node is within `join` mm of a joint already made (default: half a millimetre: the same point, or the same place typed again) is
        a branch of it: that joint is its first, and its other nodes hang from it.  An armature that is not on any joint hangs from the joint it names with `parent=`.  `mirror` ("x", "y" or "z"):
        the joints whose name ends with ".R" get a ".L" one across that plane '''
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
        names = {}
        if start == 1:
            names[0] = anchor
        for index in range(start, len(info.ctrls)):
            name = info.joints[index]
            if name in by_name:
                raise ValueError('skeleton_of: two joints are called %r' % name)
            up = info.parents[index]
            tip = None
            joint = Joint(name, tuple(float(c) for c in info.ctrls[index].pos), anchor if up < 0 else names[up], tip, None)
            out.append(joint)
            by_name[name] = joint
            names[index] = name
    if mirror is not None:
        out = mirror_joints(out, axis=mirror, plane=plane)
    return out


# What the menus offer them for (see fieldev.kinds.takes): an armature is made of points and a profile, a character and a skeleton of armatures (bodies)
armature._takes = _declare({"point", "profile"}, [{"point"}])
armature._makes_no_gizmo = True
armature._makes_outline_gizmo = True
character._takes = _declare({"solid"}, [{"solid"}])
skeleton_of._takes = _declare({"solid"}, [{"solid"}])
