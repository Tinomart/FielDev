'''
Characters: bodies made of points, in the spirit of a skeleton of round joints -- a few points, each with a size, and the flesh round them.

    shoulder = point(0, 0, 40)
    elbow = point(22, 0, 38)
    hand = point(40, 0, 30)
    arm = chain([shoulder, elbow, hand], radii=[7, 5, 4])      # an armature that tapers: a round cone from joint to joint
    leg = chain([point(0, 0, 0), point(0, 0, 25)], radii=[5, 7])
    body = smooth_union(arm, leg, 3)                           # armatures are joined with a blend, as everything else is

`round_cone(a, b, ra, rb)` is the segment: two balls and the taper between them.  `chain(points, radii, blend)` is an armature: a round cone between each two
points that follow each other.  The radius at a joint is the SIZE of its point -- the scale of its gizmo, the ring that is dragged to make the joint
thicker -- times `radii[i]` when radii are given, so an armature is shaped by dragging its points and the sizes of its points, in the viewport, as a spline is.

A joint is a ball, a segment is the surface between two balls with a radius that changes along it, and a chain is the union of its segments: a smooth
body wherever the radius changes gently, and balls at the joints however it changes.  The fields are plain math (no meshing step), so they are blended,
offset, shelled, textured and exported like every other model.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from fieldev.shape import Shape
from fieldev.kinds import takes as _declare
from fieldev.stdlib import curves as C
from fieldev.stdlib import fields as F
from fieldev.stdlib.fieldargs import is_field, number_or_field

__all__ = ['round_cone', 'chain']


def _place(p, what):
    ''' The three coordinates of a point (point(x, y, z): the expressions of its numbers, so that a dragged point moves what is made of it) or of a tuple, as fields '''
    try:
        return C.Control(p).expr
    except TypeError:
        raise TypeError('%s: a point (point(x, y, z)) or a tuple of three numbers, not %r' % (what, p))


def _radius(r, what):
    r = number_or_field(r, what)
    if not is_field(r) and r < 0:
        raise ValueError('%s: a radius is not negative (%r)' % (what, r))
    return r


def _plain(*values):
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)


def round_cone(a, b, ra, rb=None):
    ''' Two balls, one of radius `ra` at `a` and one of radius `rb` at `b` (the same as `ra` when it is not given), and the surface between them whose radius
        changes along the way from one to the other: an armature that tapers, a bone with its joints.  `a` and `b` are points, or tuples of numbers; the radii are
        numbers, or fields (a radius that is thick here and thin there).  The cone is cut across by the ends: each ends in a ball, so that armatures that
        meet at a joint are one smooth body there.  Where the radius changes fast over a short way the surface is steeper than the field is: a body, not a distance '''
    raw = (a, b)
    a, b = _place(a, 'round_cone(a, ...)'), _place(b, 'round_cone(a, b, ...)')
    ra = _radius(ra, 'round_cone: the radius at a')
    rb = ra if rb is None else _radius(rb, 'round_cone: the radius at b')
    ab = [b[i] - a[i] for i in range(3)]
    q = (F.X() - a[0], F.Y() - a[1], F.Z() - a[2])
    length2 = (ab[0].square() + ab[1].square() + ab[2].square()).max(1e-12)       # (two points that are the same make a ball)
    along = ((q[0] * ab[0] + q[1] * ab[1] + q[2] * ab[2]) / length2).max(0).min(1)
    distance = ((q[0] - along * ab[0]).square() + (q[1] - along * ab[1]).square() + (q[2] - along * ab[2]).square()).sqrt()
    out = distance - (ra + along * (rb - ra))
    if all(isinstance(p, (tuple, list)) and _plain(*p) for p in raw) and _plain(ra, rb):
        from fieldev.stdlib.shapes import _bounded
        r = max(ra, rb)
        pa, pb = tuple(raw[0]) + (0.0,) * (3 - len(raw[0])), tuple(raw[1]) + (0.0,) * (3 - len(raw[1]))
        _bounded(out, [min(pa[i], pb[i]) - r for i in range(3)], [max(pa[i], pb[i]) + r for i in range(3)])
    return out


def chain(points, radii=None, blend=0):
    ''' An armature through points: a round cone (see `round_cone`) between each two points that follow each other, joined as one body.

            arm = chain([shoulder, elbow, hand], radii=[7, 5, 4])

        points  the joints, in order: points (`point(x, y, z)`, dragged with their gizmos) or tuples of numbers.  One point is a ball
        radii   the radius at each joint: a number for all of them, or one for each (numbers or fields).  The radius at a joint is that number TIMES the size of
                its point -- the scale of its gizmo (1 for a point that has none) -- so with no radii the size of a point is its radius, and the ring of its gizmo is the
                thickness of the armature there
        blend   the radius of a smooth blend where the segments meet (0, the default: none; the joints are balls already, so a chain is smooth without it) '''
    if not isinstance(points, (list, tuple)) or not points:
        raise TypeError('chain(points): a list of points, one or more')
    ctrls = C.controls(list(points))
    n = len(ctrls)
    if radii is None:
        radii = [1.0] * n
    elif isinstance(radii, (list, tuple)):
        if len(radii) != n:
            raise ValueError('chain: %d points but %d radii -- one for each point, or one number for all' % (n, len(radii)))
    else:
        radii = [radii] * n
    sizes = []
    for k, (ctl, r) in enumerate(zip(ctrls, radii)):
        r = _radius(r, 'chain: radii[%d]' % k)
        sizes.append(r * ctl.scale_expr if ctl.scale_expr is not None else r)
    if n == 1:
        return round_cone(ctrls[0].expr, ctrls[0].expr, sizes[0], sizes[0])
    segments = [round_cone(ctrls[k - 1].expr, ctrls[k].expr, sizes[k - 1], sizes[k]) for k in range(1, n)]
    return F.union_all(segments, blend)


chain._takes = _declare({'point'}, [{'point'}])
