'''
UV maps by part: the surface laid on the texture from the armature it was made of, not from the mesh alone.

    export_mesh(hero, "hero.glb", uvs="armature")                       the same as uvs=uv_armature()
    export_mesh(hero, "hero.glb", uvs=uv_armature(margin=8, size=2048))

`uv_armature` (see uvmaps.py) asks the parts of the exported model what they are.  A character made with `character([spine, arm, face, ...])` knows its parts: the limbs
(`limb(...)`) and the features (`feature(...)`).  The unwrap then goes in three steps.

  1. WHICH PART EACH TRIANGLE BELONGS TO.  The field of every part is asked at the vertices of the mesh, and a vertex belongs to the part whose surface is the nearest to it
     (the lowest value: a part's own field is 0 on its own surface and grows away from it).  A triangle goes to the part most of its vertices belong to.  A model made with
     `character(..., symmetric="x")` has its other half evaluated across the plane, and the two halves of a part get an island each (the other one mirrored back, so that a
     texture painted on one is not mirrored on the other).
  2. EACH PART LAID FLAT FROM WHAT IT IS.  A LIMB is a tube along its path: u goes round the path (the angle times the distance from the path, so that it is millimetres), v along
     it (the length of the path, carried on past the two ends over the rounded caps).  The seam is a straight line along the back of the limb (the side the path's first stretch faces
     away from -y), and the angle is measured from a frame that is carried along the path without twisting.  A FEATURE is a skin stitched through loops: u goes round the loops
     (the mean length of each stretch of a loop), v from loop to loop (the distance between the middles of the loops), and the two end caps are laid as petals beyond the first and
     the last loop.  Where a vertex is on the skin is found by its nearest triangle of the skin, so a feature is unwrapped by the loops it was stitched through.
  3. THE ISLANDS PACKED.  Every island is in millimetres, so a texel is the same size everywhere; they are packed in the square with `margin` texels between them, and are not
     turned (u is round the part and v along it, so that a texture is painted the way the part runs).

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math
from array import array

from fieldev.stdlib import uvmaps as U
from fieldev.stdlib.armature import _catmull

__all__ = ['unwrap_parts', 'parts_of', 'symmetry_axis_of']


# -- the parts of a model -----------------------------------------------------------------------------------------------------------------

def parts_of(shapes):
    ''' The limbs and features that make up what is exported (a character knows its parts; a limb or a feature on its own is one) '''
    out = []
    for p in (shapes if isinstance(shapes, (list, tuple)) else [shapes]):
        found = getattr(p, '_parts', None)
        if found:
            out.extend(found)
        elif getattr(p, '_limb', None) is not None or getattr(p, '_feature', None) is not None:
            out.append(p)
    return out


def symmetry_axis_of(shapes):
    ''' The number of the axis (0, 1, 2) that a character was made symmetric about, or None '''
    for p in (shapes if isinstance(shapes, (list, tuple)) else [shapes]):
        axis = getattr(p, '_symmetric_axis', None)
        if axis in ('x', 'y', 'z'):
            return 'xyz'.index(axis)
    return None


# -- small vector helpers -----------------------------------------------------------------------------------------------------------------

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _length(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _unit(a):
    n = _length(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-30 else (0.0, 0.0, 1.0)


def _middle(points):
    n = float(len(points))
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n, sum(p[2] for p in points) / n)


# -- a limb: a tube along its path ---------------------------------------------------------------------------------------------------------

def _spine(nodes, per=8):
    ''' The path of a limb as a list of places: the Catmull-Rom curve through its nodes (the ends doubled, as the limb is made), `per` places to a stretch '''
    way = [tuple(nodes[0])] + [tuple(n) for n in nodes] + [tuple(nodes[-1])]
    out = []
    for i in range(len(nodes) - 1):
        for s in range(per):
            out.append(_catmull(way[i], way[i + 1], way[i + 2], way[i + 3], s / float(per)))
    out.append(tuple(nodes[-1]))
    clean = [out[0]]
    for p in out[1:]:
        if _length(_sub(p, clean[-1])) > 1e-9:                      # (places that are the same make no stretch)
            clean.append(p)
    return clean


class _Tube:
    ''' A path with a frame carried along it without twisting: the length along the path, and for every stretch its direction and the two directions across it '''

    def __init__(self, path):
        self.path = path
        self.tangent, self.length = [], []
        for a, b in zip(path, path[1:]):
            d = _sub(b, a)
            l = _length(d)
            self.length.append(l)
            self.tangent.append(_scale(d, 1.0 / l))
        self.arc = [0.0]
        for l in self.length:
            self.arc.append(self.arc[-1] + l)
        t0 = self.tangent[0]
        # (the angle is 0 facing front, -y, and the seam is on the back: the first of these directions that is not along the path starts the frame)
        ref = (0.0, -1.0, 0.0)
        for candidate in ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)):
            if abs(_dot(candidate, t0)) < 0.8:
                ref = candidate
                break
        u = _unit(_sub(ref, _scale(t0, _dot(ref, t0))))
        self.u, self.v = [], []
        for j, t in enumerate(self.tangent):
            if j > 0:
                prev = self.tangent[j - 1]
                axis = _cross(prev, t)
                sin, cos = _length(axis), _dot(prev, t)
                if sin > 1e-9:
                    axis = _scale(axis, 1.0 / sin)
                    u = _add(_add(_scale(u, cos), _scale(_cross(axis, u), sin)), _scale(axis, _dot(axis, u) * (1.0 - cos)))        # (turned with the path: Rodrigues)
                u = _unit(_sub(u, _scale(t, _dot(u, t))))
            self.u.append(u)
            self.v.append(_cross(t, u))

    def where(self, p):
        ''' (angle, distance from the path, length along it) of a place: the nearest stretch of the path, the length carried on past the two ends '''
        best = None
        for j, a in enumerate(self.path[:-1]):
            d = _sub(p, a)
            along = _dot(d, self.tangent[j])
            c = min(max(along, 0.0), self.length[j])
            r = _sub(d, _scale(self.tangent[j], c))
            d2 = _dot(r, r)
            if best is None or d2 < best[0]:
                best = (d2, j, c, along, d)
        _, j, c, along, d = best
        s = self.arc[j] + c
        if j == 0 and along < 0.0:
            s = along
        elif j == len(self.tangent) - 1 and along > self.length[j]:
            s = self.arc[j] + along
        perp = _sub(d, _scale(self.tangent[j], along))
        rho = _length(perp)
        theta = math.atan2(_dot(perp, self.v[j]), _dot(perp, self.u[j])) if rho > 1e-9 else 0.0
        return theta, rho, s


def _tube_params(points, nodes):
    ''' {vertex: (angle, distance from the path, length along it)} for a limb with these nodes.  A limb of one node is a ball: longitude and latitude '''
    if len(nodes) == 1:
        c = tuple(nodes[0])
        out = {}
        for i, p in points.items():
            d = _sub(p, c)
            r = _length(d)
            out[i] = (math.atan2(d[1], d[0]), r, math.asin(max(-1.0, min(1.0, d[2] / r))) * r if r > 1e-12 else 0.0)
        return out
    tube = _Tube(_spine(nodes))
    return {i: tube.where(p) for i, p in points.items()}


# -- a feature: a skin stitched through loops ---------------------------------------------------------------------------------------------

def _skin(rings):
    ''' (the triangles of the skin of a feature with the (u, v) in millimetres of each corner, the length of a loop).  The cells between two rings are two triangles each (cut the
        way the feature is made); the two end caps are fans whose middle is laid beyond the first and the last ring '''
    count = len(rings[0])
    edge = [[_length(_sub(r[(i + 1) % count], r[i])) for i in range(count)] for r in rings]
    mean = [sum(edge[k][i] for k in range(len(rings))) / len(rings) for i in range(count)]
    along = [0.0]
    for m in mean:
        along.append(along[-1] + max(m, 1e-6))
    mids = [_middle(r) for r in rings]
    down = [0.0]
    for k in range(len(rings) - 1):
        down.append(down[-1] + max(_length(_sub(mids[k + 1], mids[k])), 1e-6))
    first = sum(_length(_sub(p, mids[0])) for p in rings[0]) / count
    last = sum(_length(_sub(p, mids[-1])) for p in rings[-1]) / count
    tris = []
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(count):
            j = (i + 1) % count
            tris.append((a[i], a[j], b[j], (along[i], down[k]), (along[i + 1], down[k]), (along[i + 1], down[k + 1])))
            tris.append((a[i], b[j], b[i], (along[i], down[k]), (along[i + 1], down[k + 1]), (along[i], down[k + 1])))
    for i in range(count):
        j = (i + 1) % count
        middle = 0.5 * (along[i] + along[i + 1])
        tris.append((mids[0], rings[0][i], rings[0][j], (middle, -first), (along[i], 0.0), (along[i + 1], 0.0)))
        tris.append((mids[-1], rings[-1][j], rings[-1][i], (middle, down[-1] + last), (along[i + 1], down[-1]), (along[i], down[-1])))
    return tris, along[-1]


def _closest(p, a, b, c):
    ''' The nearest place of the triangle abc to p, as its barycentric weights (wa, wb, wc) '''
    ab, ac, ap = _sub(b, a), _sub(c, a), _sub(p, a)
    d1, d2 = _dot(ab, ap), _dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return (1.0, 0.0, 0.0)
    bp = _sub(p, b)
    d3, d4 = _dot(ab, bp), _dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return (0.0, 1.0, 0.0)
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return (1.0 - v, v, 0.0)
    cp = _sub(p, c)
    d5, d6 = _dot(ab, cp), _dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return (0.0, 0.0, 1.0)
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return (1.0 - w, 0.0, w)
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return (0.0, 1.0 - w, w)
    total = va + vb + vc
    if abs(total) < 1e-30:
        return (1.0, 0.0, 0.0)
    v, w = vb / total, vc / total
    return (1.0 - v - w, v, w)


def _skin_params(points, rings):
    ''' ({vertex: (u, v)} in millimetres, the length of a loop): where each place is on the skin of a feature, by the nearest triangle of the skin '''
    tris, period = _skin(rings)
    boxes = []
    for t in tris:
        c = _middle(t[:3])
        boxes.append((c, max(_length(_sub(q, c)) for q in t[:3])))
    out = {}
    for i, p in points.items():
        best, found = None, None
        for n, t in enumerate(tris):
            c, r = boxes[n]
            if best is not None and _length(_sub(p, c)) - r > best:
                continue
            w = _closest(p, t[0], t[1], t[2])
            q = (w[0] * t[0][0] + w[1] * t[1][0] + w[2] * t[2][0], w[0] * t[0][1] + w[1] * t[1][1] + w[2] * t[2][1], w[0] * t[0][2] + w[1] * t[1][2] + w[2] * t[2][2])
            d = _length(_sub(p, q))
            if best is None or d < best:
                best = d
                found = (w[0] * t[3][0] + w[1] * t[4][0] + w[2] * t[5][0], w[0] * t[3][1] + w[1] * t[4][1] + w[2] * t[5][1])
        out[i] = found
    return out, period


# -- the unwrap -------------------------------------------------------------------------------------------------------------------------

def _describe(part):
    ''' (name, nodes or rings, kind, on the plane) of a part: a limb has nodes, a feature has rings.  `on the plane`: every place of it is on the plane of symmetry '''
    info = getattr(part, '_limb', None)
    if info is not None:
        nodes = [tuple(c.pos) for c in info.ctrls]
        return info.name, nodes, 'limb', nodes
    info = getattr(part, '_feature', None)
    if info is not None:
        return info.name, info.rings, 'feature', [p for r in info.rings for p in r]
    raise TypeError('uv_armature: the parts are limb(...)s and feature(...)s, not %r' % (type(part).__name__,))


def unwrap_parts(xyz, tri, parts, margin, size, axis=None):
    ''' The UV map of the mesh by the parts it was made of: a flat f array, (u, v) three times for each triangle, and the report.  `axis`: the number of the axis the model was made
        symmetric about (its other half is the first one mirrored), or None '''
    from fieldev.stdlib.exporting import _eval_at
    if not parts:
        raise ValueError('uv_armature: the model has no parts to unwrap by -- make it with character([limb(...), feature(...), ...]), or give the parts: uv_armature([arm, face, ...])')
    nv, nt = len(xyz) // 3, len(tri) // 3
    described = [_describe(p) for p in parts]
    folded = array('f', xyz)
    if axis is not None:
        for i in range(nv):
            folded[3 * i + axis] = abs(folded[3 * i + axis])
    # (a part that lies on the plane of symmetry is its own mirror image and is asked at the places themselves; the others are asked across the plane, for the other half)
    mirrored = [axis is not None and any(abs(p[axis]) > 1e-6 for p in d[3]) for d in described]
    values = [_eval_at(p, folded if m else xyz, nv) for p, m in zip(parts, mirrored)]
    owner = [min(range(len(parts)), key=lambda k: values[k][i]) for i in range(nv)]
    groups = {}
    for t in range(nt):
        corners = [tri[3 * t + k] for k in range(3)]
        votes = {}
        for c in corners:
            votes[owner[c]] = votes.get(owner[c], 0) + 1
        top = max(votes.values())
        k = min((k for k, v in votes.items() if v == top), key=lambda k: sum(values[k][c] for c in corners))
        side = 0
        if mirrored[k]:
            side = 0 if sum(xyz[3 * c + axis] for c in corners) >= 0.0 else 1
        groups.setdefault((k, side), []).append(t)
    islands, names = [], []
    for (k, side), members in sorted(groups.items()):
        name, data, kind, _ = described[k]
        used = sorted({tri[3 * t + c] for t in members for c in range(3)})
        pts = {}
        for i in used:
            q = (xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2])
            if mirrored[k] and side == 1:
                q = tuple(-q[a] if a == axis else q[a] for a in range(3))
            pts[i] = q
        uv = []
        if kind == 'limb':
            par = _tube_params(pts, data)
            for t in members:
                corners = [tri[3 * t + c] for c in range(3)]
                angles = [par[c][0] for c in corners]
                if max(angles) - min(angles) > math.pi:                  # (a triangle across the seam: the corners on the small side go round to the other)
                    angles = [a + 2.0 * math.pi if a < 0.0 else a for a in angles]
                for c, a in zip(corners, angles):
                    uv.append((a * par[c][1], par[c][2]))
        else:
            par, period = _skin_params(pts, data)
            for t in members:
                corners = [tri[3 * t + c] for c in range(3)]
                us = [par[c][0] for c in corners]
                if max(us) - min(us) > 0.5 * period:
                    us = [u + period if u < 0.5 * period else u for u in us]
                for c, u in zip(corners, us):
                    uv.append((u, par[c][1]))
        if mirrored[k] and side == 1:
            uv = [(-u, v) for u, v in uv]                                # (the mirrored half is laid the way round that gives its triangles the winding of the first half)
        lu, lv = min(u for u, v in uv), min(v for u, v in uv)
        uv = [(u - lu, v - lv) for u, v in uv]
        width, height = max(u for u, v in uv), max(v for u, v in uv)
        islands.append((members, uv, width, height))
        names.append(name + (' (mirrored)' if side else ''))
    margin_uv = float(margin) / float(size)
    scale, place = U._pack(islands, margin_uv, False)
    out = array('f', [0.0]) * (6 * nt)
    for number, (members, uv, width, height) in enumerate(islands):
        x0, y0, _ = place[number]
        for slot, t in enumerate(members):
            for c in range(3):
                u, v = uv[3 * slot + c]
                out[6 * t + 2 * c] = x0 + u * scale
                out[6 * t + 2 * c + 1] = y0 + v * scale
    ratios, covered = [], 0.0
    for t in range(nt):
        p = [(xyz[3 * tri[3 * t + c]], xyz[3 * tri[3 * t + c] + 1], xyz[3 * tri[3 * t + c] + 2]) for c in range(3)]
        area3 = 0.5 * _length(_cross(_sub(p[1], p[0]), _sub(p[2], p[0])))
        area2 = abs(U._area2((out[6 * t], out[6 * t + 1]), (out[6 * t + 2], out[6 * t + 3]), (out[6 * t + 4], out[6 * t + 5])))
        covered += area2
        if area3 > 1e-12:
            ratios.append(area2 / area3)
    ratios.sort()
    median = ratios[len(ratios) // 2] if ratios else 1.0
    report = {'islands': len(islands), 'parts': names, 'coverage': covered, 'size': size, 'mm_per_texel': (1.0 / (math.sqrt(median) * size)) if median > 0 else None,
              'stretch': (ratios[len(ratios) // 100] / median, ratios[-1 - len(ratios) // 100] / median) if ratios else None}
    return out, report
