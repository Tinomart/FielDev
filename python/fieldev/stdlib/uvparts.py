'''
UV maps by part: the surface laid on the texture from the armature it was made of, not from the mesh alone.

    export_mesh(hero, "hero.glb", uvs="armature")                       the same as uvs=uv_armature()
    export_mesh(hero, "hero.glb", uvs=uv_armature(margin=8, size=2048))

`uv_armature` (see uvmaps.py) asks the parts of the exported model what they are.  A character made with `character([spine, arm, nose, ...])` knows its parts: the armatures
(`armature(...)`) and the feature models (`feature_model(...)`).  The unwrap then goes in three steps.

  1. WHICH PART EACH TRIANGLE BELONGS TO.  The field of every part is asked at the vertices of the mesh, and a vertex belongs to the part whose surface is the nearest to it
     (the lowest value: a part's own field is 0 on its own surface and grows away from it).  A triangle goes to the part most of its vertices belong to.  A model made with
     `character(..., symmetric="x")` has its other half evaluated across the plane, and the two halves of a part get an island each (the other one mirrored back, so that a
     texture painted on one is not mirrored on the other).
  2. EACH PART LAID FLAT FROM WHAT IT IS.  An ARMATURE is a tube along its path: u goes round the path (the angle times the distance from the path, so that it is millimetres), v along
     it (the length of the path).  The seam is a straight line along the back of the armature (the side the path's first stretch faces away from -y), and the angle is measured from a
     frame that is carried along the path without twisting.  The end caps are unrolled as a disc beyond the end (the rim at the end of the path, the middle one radius further), so
     that a flat cap is not a line in the texture.  FEATURE MODELS are laid flat as they were drawn: in the picture of the view it was stitched in (u to the right, v up, in millimetres), so
     that a texture painted over the reference picture of a face lands where it was drawn.  The triangles that face away from the viewer -- the back of a shell, a closed back --
     are an island of their own, seen from behind.
  3. THE ISLANDS PACKED.  Every island is in millimetres, so a texel is the same size everywhere; they are packed in the square with `margin` texels between them, and are not
     turned (an armature's u is round the part and v along it, the feature models' the way they were drawn, so that a texture is painted the way the part runs).

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
    ''' The armatures and feature models that make up what is exported (a character knows its parts; an armature or feature models on their own are one) '''
    out = []
    for p in (shapes if isinstance(shapes, (list, tuple)) else [shapes]):
        found = getattr(p, '_parts', None)
        if found:
            out.extend(found)
        elif getattr(p, '_armature', None) is not None or getattr(p, '_feature_model', None) is not None:
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


# -- a tube along a path ---------------------------------------------------------------------------------------------------------------

def _spine(nodes, per=8):
    ''' The path of an armature as a list of places: the Catmull-Rom curve through its nodes (the ends doubled, as the armature is made), `per` places to a stretch '''
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
        ''' (angle, distance from the path, length along it, end, stretch, how far along that stretch) of a place: the nearest stretch of the path, the length carried on past the two
            ends.  `end`: -1 on the start cap (at the start of the path or before it), 1 on the end cap, else 0 '''
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
        # (a place on the end cap -- at the end of the path or beyond it, flat or rounded -- is laid out apart, see _unroll_caps)
        tol = 1e-3 * self.arc[-1] + 1e-9
        end = -1 if (j == 0 and along < tol) else (1 if (j == len(self.tangent) - 1 and along > self.length[j] - tol) else 0)
        return theta, rho, s, end, j, c


def _unroll_caps(tube, got):
    ''' The end caps laid out as a disc unrolled beyond the end: the rim (the widest place of the cap) at the end of the path and the middle one radius further.  A flat cap is all at
        one length along the path, and would be a line in the texture; a rounded one is only seen from the pole.  `got` is {vertex: where(...)}; it is changed.  Returns {end: rim} '''
    last = tube.arc[-1]
    rims = {}
    for end in (-1, 1):
        zone = [i for i, g in got.items() if g[3] == end]
        if not zone:
            continue
        rim = max(got[i][1] for i in zone) or 1e-9
        rims[end] = rim
        for i in zone:
            theta, rho, _s, _e, j, c = got[i]
            got[i] = (theta, rho, (last + (rim - rho)) if end > 0 else -(rim - rho), end, j, c)
    return rims


def _tube_params(points, nodes):
    ''' {vertex: (angle, distance from the path, length along it)} for an armature with these nodes.  An armature of one node is a ball: longitude and latitude '''
    if len(nodes) == 1:
        c = tuple(nodes[0])
        out = {}
        for i, p in points.items():
            d = _sub(p, c)
            r = _length(d)
            out[i] = (math.atan2(d[1], d[0]), r, math.asin(max(-1.0, min(1.0, d[2] / r))) * r if r > 1e-12 else 0.0)
        return out
    tube = _Tube(_spine(nodes))
    got = {i: tube.where(p) for i, p in points.items()}
    _unroll_caps(tube, got)
    return {i: g[:3] for i, g in got.items()}


# -- feature models: flat, as they were drawn ---------------------------------------------------------------------------------------------------------

def _planar_params(points, info, back):
    ''' {vertex: (u, v)} in millimetres: where each place is on feature models, laid flat as it is seen in the view they were stitched in -- u to the right, v up -- or, for the
        triangles that face away from the viewer (`back`: the back of a shell, a closed back), as it is seen from behind '''
    u, v, _ = info.surface.view
    sign = -1.0 if back else 1.0
    return {i: (sign * _dot(p, u), _dot(p, v)) for i, p in points.items()}


# -- the unwrap -------------------------------------------------------------------------------------------------------------------------

def _describe(part):
    ''' (name, nodes or the feature models, kind, its places) of a part: an armature has nodes, feature models are what they know of themselves.  The places are what decides whether the part is on the plane
        of symmetry (all of them are) or off it; feature models that have places on both sides of the plane have their other half in themselves, and counts as being on it '''
    info = getattr(part, '_armature', None)
    if info is not None:
        nodes = [tuple(c.pos) for c in info.ctrls]
        return info.name, nodes, 'armature', nodes
    info = getattr(part, '_feature_model', None)
    if info is not None:
        return info.name, info, 'feature_model', info.surface.vertices
    raise TypeError('uv_armature: the parts are armature(...)s and feature_model(...)s, not %r' % (type(part).__name__,))


def unwrap_parts(xyz, tri, parts, margin, size, axis=None):
    ''' The UV map of the mesh by the parts it was made of: a flat f array, (u, v) three times for each triangle, and the report.  `axis`: the number of the axis the model was made
        symmetric about (its other half is the first one mirrored), or None '''
    from fieldev.stdlib.exporting import _eval_at
    if not parts:
        raise ValueError('uv_armature: the model has no parts to unwrap by -- make it with character([armature(...), feature_model(...), ...]), or give the parts: uv_armature([arm, nose, ...])')
    nv, nt = len(xyz) // 3, len(tri) // 3
    described = [_describe(p) for p in parts]
    folded = array('f', xyz)
    if axis is not None:
        for i in range(nv):
            folded[3 * i + axis] = abs(folded[3 * i + axis])
    # (a part that lies on the plane of symmetry is its own mirror image and is asked at the places themselves; the others are asked across the plane, for the other half)
    mirrored = [axis is not None and any(abs(p[axis]) > 1e-6 for p in d[3])
                and not (d[2] == 'feature_model' and any(p[axis] > 1e-6 for p in d[3]) and any(p[axis] < -1e-6 for p in d[3])) for d in described]
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
        back = 0
        if described[k][2] == 'feature_model':
            # feature models are laid flat as they are seen in their view: the triangles that face away from the viewer are an island of their own, seen from behind.  (Across the plane of
            # symmetry the triangle is turned inside out by the mirror, and so is the way it faces)
            q = [(xyz[3 * c], xyz[3 * c + 1], xyz[3 * c + 2]) for c in corners]
            if mirrored[k] and side == 1:
                q = [tuple(-x if a == axis else x for a, x in enumerate(p)) for p in q]
            n = _cross(_sub(q[1], q[0]), _sub(q[2], q[0]))
            facing = _dot(n, described[k][1].surface.view[2]) * (-1.0 if mirrored[k] and side == 1 else 1.0)
            back = 0 if facing >= 0.0 else 1
        groups.setdefault((k, side, back), []).append(t)
    islands, names = [], []
    for (k, side, back), members in sorted(groups.items()):
        name, data, kind, _ = described[k]
        used = sorted({tri[3 * t + c] for t in members for c in range(3)})
        pts = {}
        for i in used:
            q = (xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2])
            if mirrored[k] and side == 1:
                q = tuple(-q[a] if a == axis else q[a] for a in range(3))
            pts[i] = q
        uv = []
        if kind == 'armature':
            par = _tube_params(pts, data)
            for t in members:
                corners = [tri[3 * t + c] for c in range(3)]
                angles = [par[c][0] for c in corners]
                if max(angles) - min(angles) > math.pi:                  # (a triangle across the seam: the corners on the small side go round to the other)
                    angles = [a + 2.0 * math.pi if a < 0.0 else a for a in angles]
                for c, a in zip(corners, angles):
                    uv.append((a * par[c][1], par[c][2]))
        else:
            par = _planar_params(pts, data, back)
            for t in members:
                for c in range(3):
                    uv.append(par[tri[3 * t + c]])
        if mirrored[k] and side == 1:
            uv = [(-u, v) for u, v in uv]                                # (the mirrored half is laid the way round that gives its triangles the winding of the first half)
        lu, lv = min(u for u, v in uv), min(v for u, v in uv)
        uv = [(u - lu, v - lv) for u, v in uv]
        width, height = max(u for u, v in uv), max(v for u, v in uv)
        islands.append((members, uv, width, height))
        names.append(name + (' (back)' if back else '') + (' (mirrored)' if side else ''))
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
    per_island = [[] for _ in islands]
    island_of = {t: number for number, island in enumerate(islands) for t in island[0]}
    for t in range(nt):
        p = [(xyz[3 * tri[3 * t + c]], xyz[3 * tri[3 * t + c] + 1], xyz[3 * tri[3 * t + c] + 2]) for c in range(3)]
        area3 = 0.5 * _length(_cross(_sub(p[1], p[0]), _sub(p[2], p[0])))
        area2 = abs(U._area2((out[6 * t], out[6 * t + 1]), (out[6 * t + 2], out[6 * t + 3]), (out[6 * t + 4], out[6 * t + 5])))
        covered += area2
        if area3 > 1e-12:
            ratios.append(area2 / area3)
            per_island[island_of[t]].append(area2 / area3)
    ratios.sort()
    median = ratios[len(ratios) // 2] if ratios else 1.0
    # (for each island: its name, its triangles, those with less than a twentieth of the median area in the texture, and its own median against the whole model's)
    detail = [(names[k], len(islands[k][0]), sum(1 for r in per_island[k] if r < 0.05 * median), (sorted(per_island[k])[len(per_island[k]) // 2] / median) if per_island[k] and median > 0 else 0.0)
              for k in range(len(islands))]
    report = {'islands': len(islands), 'parts': names, 'detail': detail, 'coverage': covered, 'size': size,
              'mm_per_texel': (1.0 / (math.sqrt(median) * size)) if median > 0 else None,
              'stretch': (ratios[len(ratios) // 100] / median, ratios[-1 - len(ratios) // 100] / median) if ratios else None}
    return out, report
