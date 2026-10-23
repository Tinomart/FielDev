'''
Features: stitched loops, for the delicate parts of a character -- a face, an ear, a hand.

    nose = feature([bridge, middle, tip, nostrils], name="nose")        # four loops of points, stitched together
    face = feature([brow, eyes, cheeks, mouth, chin], detail=3, name="face")

A FEATURE is a surface that is stitched through LOOPS: each loop is a ring of points (`point(x, y, z)`, dragged with their gizmos, or tuples of numbers) round one place of the
part -- the brow, the eyes, the mouth -- and the feature is the skin that joins one loop to the next, closed at the two ends.  It is what a limb cannot be: a limb has the same round
cross-section all along, and a loop has the shape of the place it is at, so the loops of a face are an oval at the brow, a wide shape at the eyes, a slit at the mouth.  Every loop has
the same number of points, in the same order round (the first point of one loop is stitched to the first point of the next), and each loop should be a ring that can be seen from its
middle: the middle of the loop must be inside it.  Every number of the feature is an expression of the points, so that a point dragged in the viewport moves the feature at once.

    feature(loops, detail=3, name=None)

        loops   two or more loops, each a list of three or more points, all with the same number of points
        detail  how many rings make the stretch between two loops: 1 is the loops themselves, joined with straight skin; more rings are laid on a smooth curve through the loops
                (a Catmull-Rom curve, as the nodes of a limb are), so that the skin bends smoothly across a loop and the feature is not faceted
        name    what the UV map and the model tree call the feature

`ring(center, radius, count, facing)` makes the points of a round loop, to start a feature from.  The feature joins a character with the rest of the parts, as a limb does:

    hero = character([spine, arm, face], blend=2)

The UV map of the character (`uvs="armature"`, see uvmaps.py) unwraps a feature along its loops: round a loop is one direction of the texture, and from loop to loop is the other.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math

from fieldev.kinds import takes as _declare
from fieldev.stdlib import curves as C
from fieldev.stdlib import fields as F
from fieldev.stdlib.armature import _catmull

__all__ = ['feature', 'ring', 'Feature']

_MOST_PIECES = 6000             # (the tetrahedra a feature is made of: more would be too slow to draw)


class Feature:
    ''' What a feature knows of itself, for the UV map: its name and its rings (the numbers they have now, one list of (x, y, z) for each ring, the loops among them) '''

    def __init__(self, name, rings, loops, detail):
        self.name = name
        self.rings = rings
        self.loops = loops
        self.detail = detail

    def __repr__(self):
        return 'feature(%r, %d loops of %d points)' % (self.name, self.loops, len(self.rings[0]))


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def ring(center, radius, count=8, facing=(0, 1, 0), start=None):
    ''' The points of a round loop, as tuples of numbers: `count` of them on a circle of `radius` (a number, or (wide, high) for an oval) round `center`, in the plane that `facing` is
        the normal of, the first at the direction `start` (default: up, +z; along x when the loop faces up or down).  The points follow each other counter-clockwise seen from where the
        loop faces '''
    if not isinstance(count, int) or isinstance(count, bool) or count < 3:
        raise ValueError('ring: count is the number of points, 3 or more, not %r' % (count,))
    wide, high = (radius if isinstance(radius, (tuple, list)) and len(radius) == 2 else (radius, radius))
    n = math.sqrt(sum(float(c) ** 2 for c in facing))
    if n < 1e-12:
        raise ValueError('ring: facing is a direction, not (0, 0, 0)')
    f = tuple(float(c) / n for c in facing)
    up = tuple(float(c) for c in start) if start is not None else ((1.0, 0.0, 0.0) if abs(f[2]) > 0.9 else (0.0, 0.0, 1.0))
    along = _dot(up, f)
    u = _sub(up, tuple(c * along for c in f))                  # (the start direction, made to lie in the plane)
    lu = math.sqrt(_dot(u, u))
    if lu < 1e-12:
        raise ValueError('ring: start must not be along the way the loop faces')
    u = tuple(c / lu for c in u)
    v = _cross(f, u)
    out = []
    for k in range(count):
        t = 2.0 * math.pi * k / count
        a, b = math.cos(t) * high, math.sin(t) * wide
        out.append(tuple(float(center[i]) + u[i] * a + v[i] * b for i in range(3)))
    return out


def _tet(corners, numbers):
    ''' The tetrahedron of four corners (expressions; `numbers` are the places they have now) as a field: the greatest of the distances to the planes of its four faces, each plane
        taken so that the corner it does not hold is on the inside.  None for a flat one (it has no volume) '''
    q = (F.X(), F.Y(), F.Z())
    sides = []
    for i, j, k, o in ((0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 3, 1), (1, 2, 3, 0)):
        n = _cross(_sub(numbers[j], numbers[i]), _sub(numbers[k], numbers[i]))
        length = math.sqrt(_dot(n, n))
        inside = _dot(_sub(numbers[o], numbers[i]), n)
        if length < 1e-9 or abs(inside) < 1e-9 * length:
            return None
        sign = -1.0 if inside > 0 else 1.0
        m = _cross(_sub(corners[j], corners[i]), _sub(corners[k], corners[i]))
        norm = (m[0].square() + m[1].square() + m[2].square() + 1e-12).sqrt()
        sides.append(_dot(_sub(q, corners[i]), m) * (sign / norm))
    out = sides[0]
    for s in sides[1:]:
        out = out.max(s)
    return out


def feature(loops, detail=3, name=None):
    ''' A surface stitched through loops of points: the skin from one loop to the next, closed at the first and the last.

            nose = feature([bridge, middle, tip], detail=3, name="nose")

        loops   two or more loops; each is a list of three or more points (`point(x, y, z)`, or tuples of numbers), all with the same number of points, in the same order round
        detail  the rings of a stretch from one loop to the next: 1 joins the loops with straight skin, more lay the rings on a smooth curve through the loops (3 by default)
        name    what the UV map calls it ("nose") '''
    if not isinstance(loops, (list, tuple)) or len(loops) < 2:
        raise TypeError('feature(loops): a list of two or more loops, each a list of points')
    sets = []
    for k, one in enumerate(loops):
        if not isinstance(one, (list, tuple)) or len(one) < 3:
            raise TypeError('feature: loop %d is a list of three or more points (point(x, y, z) or tuples of numbers)' % k)
        sets.append(C.controls(list(one)))
    count = len(sets[0])
    for k, ctrls in enumerate(sets):
        if len(ctrls) != count:
            raise ValueError('feature: loop %d has %d points but the first has %d -- every loop has the same number, in the same order round' % (k, len(ctrls), count))
    if not isinstance(detail, int) or isinstance(detail, bool) or not 1 <= detail <= 16:
        raise ValueError('feature: detail is the rings between two loops, from 1 to 16, not %r' % (detail,))
    label = str(name) if name else 'feature'
    # the rings: the loops, and between them the rings of a Catmull-Rom curve through each point's places (the ends doubled) -- the expressions, for the field, and the numbers, for the
    # UV map and for deciding which side of a face is the inside
    expr = [[c.expr for c in ctrls] for ctrls in sets]
    nums = [[tuple(c.pos) for c in ctrls] for ctrls in sets]
    way_e = [expr[0]] + expr + [expr[-1]]
    way_n = [nums[0]] + nums + [nums[-1]]
    rings_e, rings_n = [], []
    for k in range(len(sets) - 1):
        for s in range(detail):
            t = s / float(detail)
            rings_e.append([_catmull(way_e[k][i], way_e[k + 1][i], way_e[k + 2][i], way_e[k + 3][i], t) for i in range(count)])
            rings_n.append([_catmull(way_n[k][i], way_n[k + 1][i], way_n[k + 2][i], way_n[k + 3][i], t) for i in range(count)])
    rings_e.append(expr[-1])
    rings_n.append(nums[-1])
    pieces = 3 * count * (len(rings_e) - 1)
    if pieces > _MOST_PIECES:
        raise ValueError('feature: %d loops of %d points with detail=%d make %d pieces, more than %d -- fewer points, or a lower detail' % (len(sets), count, detail, pieces, _MOST_PIECES))

    def middle(points, numbers):
        e = [points[0][c] for c in range(3)]
        for p in points[1:]:
            e = [e[c] + p[c] for c in range(3)]
        return tuple(x * (1.0 / count) for x in e), tuple(sum(p[c] for p in numbers) / count for c in range(3))

    mids = [middle(rings_e[k], rings_n[k]) for k in range(len(rings_e))]
    tets = []
    for k in range(len(rings_e) - 1):
        a, b = rings_e[k], rings_e[k + 1]
        an, bn = rings_n[k], rings_n[k + 1]
        (ca, can), (cb, cbn) = mids[k], mids[k + 1]
        for i in range(count):
            j = (i + 1) % count
            # the wedge between the triangle (middle of ring k, point i, point j) and the same of ring k+1, in three tetrahedra whose shared faces are cut the same way in the wedges
            # on both sides of them (the diagonals run from the middle of ring k to point i of ring k+1, and from point i of ring k to point j of ring k+1)
            for corners, numbers in (((ca, a[i], a[j], b[j]), (can, an[i], an[j], bn[j])),
                                     ((ca, a[i], b[i], b[j]), (can, an[i], bn[i], bn[j])),
                                     ((ca, b[i], cb, b[j]), (can, bn[i], cbn, bn[j]))):
                t = _tet(corners, numbers)
                if t is not None:
                    tets.append(t)
    if not tets:
        raise ValueError('feature: the loops are flat or on top of each other -- they enclose no volume')
    out = F.union_all(tets, 0)
    if all(isinstance(p, (tuple, list)) and all(isinstance(c, (int, float)) for c in p) for one in loops for p in one):             # (tuples of numbers: the box is known)
        from fieldev.stdlib.shapes import _bounded
        flat = [p for r in rings_n for p in r]
        _bounded(out, [min(p[c] for p in flat) for c in range(3)], [max(p[c] for p in flat) for c in range(3)])
    out._feature = Feature(label, rings_n, len(sets), detail)
    return out


# What the menus offer it for (see fieldev.kinds.takes): a feature is made of points
feature._takes = _declare({'point'}, [{'point'}])
