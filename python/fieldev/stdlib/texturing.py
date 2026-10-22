'''
Texturing: the textures of a model, baked from its fields.

    export_mesh(hero, "hero.glb", uvs="unwrap", materials=[skin, metal], textures=bake(size=1024))

A texture is a picture the surface is painted with.  A modelling program that works on meshes paints it by hand; here the surface IS a field, and so the picture is
asked of the field: every texel of the picture is a place on the surface (found through the UVs of the export), and what that place is made of is read from the
model there.  `bake` says which pictures are wanted and how fine; `export_mesh` makes them and writes them beside the mesh (`hero_color.png`, `hero_normal.png`,
`hero_orm.png`, `hero_emissive.png`), and the glTF file refers to them (a .glb has them inside as well).

    color      the base colour: the material of the place (`where` is read at the texel, so the edge between two materials is as sharp as the texture is), times the vertex
               colours (`colors=`); a material's colour, roughness and so on can be FIELDS (a pattern, noise) and so can the colours.  sRGB, like every colour map
    normal     the normal map: the exact normal of the field at the place, in the tangent space of the mesh (red right, green up, blue out).  A coarse mesh (`max_triangles`) shaded
               with it looks like the fine surface -- the detail of the field is in the picture, not in the triangles
    orm        occlusion (red), roughness (green), metalness (blue), one linear picture: what glTF and the game engines read for the metallic-roughness model
    mr         roughness and metalness only (occlusion is 1)
    occlusion  the occlusion alone, a grey picture (for an engine that wants it apart)
    emissive   the glow of the materials, sRGB

The occlusion is the ambient occlusion of the field: from every place rays go out over the hemisphere, and a ray is blocked where the field gets near zero again
(cone tracing along the ray, which is exact for a field that is a distance and a good guess for one that is nearly).  The normal map and the occlusion come from the
field and not from the mesh, so they have no triangles in them.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math
import os
import time
from array import array

from fieldev.shape import Shape
from fieldev.stdlib import pngfile

__all__ = ['bake', 'Bake']

_MAPS = ('color', 'normal', 'orm', 'mr', 'occlusion', 'emissive')
_ALIASES = {'albedo': 'color', 'basecolor': 'color', 'base_color': 'color', 'diffuse': 'color', 'normals': 'normal', 'ao': 'occlusion', 'roughness': 'mr',
            'metallic': 'mr', 'metalness': 'mr', 'glow': 'emissive'}


class Bake:
    ''' What textures an export makes: see `bake` '''

    def __init__(self, size, maps, padding, samples, distance, strength, uv_set):
        self.size = size
        self.maps = maps
        self.padding = padding
        self.samples = samples
        self.distance = distance
        self.strength = strength
        self.uv_set = uv_set
        self.report = None

    def __repr__(self):
        return 'bake(size=%d, maps=%r)' % (self.size, self.maps)


def bake(size=1024, maps=None, padding=4, occlusion_samples=8, occlusion_distance=None, occlusion_strength=1.0, uv_set=0):
    ''' The textures that `export_mesh(..., uvs=..., textures=bake(...))` bakes out of the fields of the model.

        size        the texels across (the pictures are square): 16 to 8192; 1024 by default
        maps        which pictures: "color", "normal", "orm" (occlusion, roughness, metalness in one), "mr" (roughness and metalness only), "occlusion" (alone), "emissive".
                    None: color, normal and orm, and emissive when a material glows
        padding     texels the islands of the picture are grown by, so that a filter or a mip map does not take in the empty ground beside them: 4
        occlusion_samples   rays from every texel for the occlusion: 4 to 64; 8
        occlusion_distance  how far, in mm, a ray looks for something in the way: None for a fifth of the largest side of the model
        occlusion_strength  1: the occlusion as it is; 0: none; 2: twice as dark
        uv_set      the UV map the pictures are made for: 0 (the first) or 1 (the second of a list of two)

        The pictures are written beside the mesh file, `<name>_<map>.png`.  Needs `uvs=` in the export (a UV map where the islands do not overlap: "unwrap") '''
    if not isinstance(size, int) or isinstance(size, bool) or not 16 <= size <= 8192:
        raise ValueError('bake: size is the texels across, from 16 to 8192, not %r' % (size,))
    wanted = None
    if maps is not None:
        wanted = []
        for m in ([maps] if isinstance(maps, str) else list(maps)):
            key = _ALIASES.get(str(m).strip().lower(), str(m).strip().lower())
            if key not in _MAPS:
                raise ValueError('bake: the maps are %s, not %r' % (', '.join(_MAPS), m))
            if key not in wanted:
                wanted.append(key)
        if not wanted:
            raise ValueError('bake: maps names at least one picture')
        if 'orm' in wanted and ('mr' in wanted or 'occlusion' in wanted):
            raise ValueError('bake: "orm" already has the occlusion, the roughness and the metalness in it')
    if not isinstance(padding, int) or isinstance(padding, bool) or not 0 <= padding <= 64:
        raise ValueError('bake: padding is a number of texels from 0 to 64, not %r' % (padding,))
    if not isinstance(occlusion_samples, int) or isinstance(occlusion_samples, bool) or not 4 <= occlusion_samples <= 64:
        raise ValueError('bake: occlusion_samples is from 4 to 64, not %r' % (occlusion_samples,))
    if occlusion_distance is not None and not (isinstance(occlusion_distance, (int, float)) and occlusion_distance > 0):
        raise ValueError('bake: occlusion_distance is a number of mm above 0, not %r' % (occlusion_distance,))
    if not isinstance(occlusion_strength, (int, float)) or isinstance(occlusion_strength, bool) or not 0.0 <= occlusion_strength <= 8.0:
        raise ValueError('bake: occlusion_strength is from 0 to 8, not %r' % (occlusion_strength,))
    if uv_set not in (0, 1):
        raise ValueError('bake: uv_set is 0 or 1, not %r' % (uv_set,))
    return Bake(int(size), wanted, int(padding), int(occlusion_samples), None if occlusion_distance is None else float(occlusion_distance),
                float(occlusion_strength), int(uv_set))


# ---------------------------------------------------------------------------
# Rasterising the triangles in the picture

def rasterize(uv, tri, size):
    ''' The texels whose centre is inside a triangle of the UV map: (the texel, y * size + x, the triangle, and the barycentric weights of its second and third corner).  The
        picture has v up, so the row of a texel counts from the top: y = (1 - v) * size '''
    texel, owner, w1, w2 = array('I'), array('I'), array('f'), array('f')
    floor, ceil = math.floor, math.ceil
    for t in range(len(tri) // 3):
        i0, i1, i2 = tri[3 * t], tri[3 * t + 1], tri[3 * t + 2]
        x0, y0 = uv[2 * i0] * size, (1.0 - uv[2 * i0 + 1]) * size
        x1, y1 = uv[2 * i1] * size, (1.0 - uv[2 * i1 + 1]) * size
        x2, y2 = uv[2 * i2] * size, (1.0 - uv[2 * i2 + 1]) * size
        d = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(d) < 1e-12:
            continue
        inv = 1.0 / d
        first = max(0, int(ceil(min(y0, y1, y2) - 0.5)))
        last = min(size - 1, int(floor(max(y0, y1, y2) - 0.5)))
        a1, a2 = (y2 - y0) * inv, -(y1 - y0) * inv                  # (the weights as a1 * x + b1 along a row)
        for y in range(first, last + 1):
            yc = y + 0.5
            b1 = (-x0 * (y2 - y0) - (x2 - x0) * (yc - y0)) * inv
            b2 = (-(-x0) * (y1 - y0) + (x1 - x0) * (yc - y0)) * inv
            low, high = -1e30, 1e30
            for a, b in ((a1, b1), (a2, b2), (-a1 - a2, 1.0 - b1 - b2)):
                if abs(a) < 1e-12:
                    if b < 0.0:
                        low, high = 1.0, 0.0
                        break
                elif a > 0.0:
                    low = max(low, -b / a)
                else:
                    high = min(high, -b / a)
            if low > high:
                continue
            xa = max(0, int(ceil(low - 0.5)))
            xb = min(size - 1, int(floor(high - 0.5)))
            for x in range(xa, xb + 1):
                xc = x + 0.5
                texel.append(y * size + x)
                owner.append(t)
                w1.append(a1 * xc + b1)
                w2.append(a2 * xc + b2)
    return texel, owner, w1, w2


def vertex_tangents(xyz, tri, uv, normals):
    ''' The tangent of every vertex: where u grows on the surface, made square to the normal, and the sign (w) of the bitangent -- where v (up the picture) grows is
        cross(normal, tangent) * w.  Flat array, x, y, z, w for each vertex '''
    nv = len(xyz) // 3
    acc_t, acc_b = [0.0] * (3 * nv), [0.0] * (3 * nv)
    for t in range(len(tri) // 3):
        i = (tri[3 * t], tri[3 * t + 1], tri[3 * t + 2])
        e1 = [xyz[3 * i[1] + c] - xyz[3 * i[0] + c] for c in range(3)]
        e2 = [xyz[3 * i[2] + c] - xyz[3 * i[0] + c] for c in range(3)]
        du1, dv1 = uv[2 * i[1]] - uv[2 * i[0]], uv[2 * i[1] + 1] - uv[2 * i[0] + 1]
        du2, dv2 = uv[2 * i[2]] - uv[2 * i[0]], uv[2 * i[2] + 1] - uv[2 * i[0] + 1]
        det = du1 * dv2 - du2 * dv1
        if abs(det) < 1e-18:
            continue
        r = 1.0 / det
        cross = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        area = 0.5 * math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)
        for c in range(3):
            tc = (e1[c] * dv2 - e2[c] * dv1) * r * area
            bc = (e2[c] * du1 - e1[c] * du2) * r * area
            for k in i:
                acc_t[3 * k + c] += tc
                acc_b[3 * k + c] += bc
    out = array('f', [0.0]) * (4 * nv)
    for k in range(nv):
        n = (normals[3 * k], normals[3 * k + 1], normals[3 * k + 2])
        t = (acc_t[3 * k], acc_t[3 * k + 1], acc_t[3 * k + 2])
        d = n[0] * t[0] + n[1] * t[1] + n[2] * t[2]
        t = (t[0] - d * n[0], t[1] - d * n[1], t[2] - d * n[2])
        length = math.sqrt(t[0] ** 2 + t[1] ** 2 + t[2] ** 2)
        if length < 1e-20:                                          # (a vertex of no triangle with a usable map: any tangent square to the normal)
            ref = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
            t = (n[1] * ref[2] - n[2] * ref[1], n[2] * ref[0] - n[0] * ref[2], n[0] * ref[1] - n[1] * ref[0])
            length = math.sqrt(t[0] ** 2 + t[1] ** 2 + t[2] ** 2) or 1.0
        t = (t[0] / length, t[1] / length, t[2] / length)
        nxt = (n[1] * t[2] - n[2] * t[1], n[2] * t[0] - n[0] * t[2], n[0] * t[1] - n[1] * t[0])
        w = 1.0 if (nxt[0] * acc_b[3 * k] + nxt[1] * acc_b[3 * k + 1] + nxt[2] * acc_b[3 * k + 2]) >= 0.0 else -1.0
        out[4 * k], out[4 * k + 1], out[4 * k + 2], out[4 * k + 3] = t[0], t[1], t[2], w
    return out


# ---------------------------------------------------------------------------
# Baking

_SRGB = [0] * 4096
for _i in range(4096):
    _c = _i / 4095.0
    _SRGB[_i] = int(round(255.0 * (12.92 * _c if _c <= 0.0031308 else 1.055 * _c ** (1.0 / 2.4) - 0.055)))


def _srgb(c):
    c = 0.0 if c < 0.0 else (1.0 if c > 1.0 else c)
    return _SRGB[int(c * 4095.0 + 0.5)]


def _byte(c):
    c = 0.0 if c < 0.0 else (1.0 if c > 1.0 else c)
    return int(c * 255.0 + 0.5)


def _evaluate(eval_at, shape, pts):
    ''' A field at the points (an f array of x, y, z): a list of values '''
    return eval_at(shape, pts, len(pts) // 3)


def _shifted(pts, axis, amount):
    out = array('f', pts)
    out[axis::3] = array('f', [v + amount for v in pts[axis::3]])
    return out


def surface_gradient(values_at, pts, h):
    ''' The gradient of a field at the points by central differences over `h` mm: (gx, gy, gz) lists.  `values_at(pts)` gives the field there '''
    out = []
    for axis in range(3):
        hi = values_at(_shifted(pts, axis, h))
        lo = values_at(_shifted(pts, axis, -h))
        out.append([(a - b) / (2.0 * h) for a, b in zip(hi, lo)])
    return out


def _hemisphere(samples):
    ''' Directions over the hemisphere, more of them near the pole (weighted by the cosine): (x, y, z) in a frame whose z is the normal '''
    out = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for k in range(samples):
        r2 = (k + 0.5) / samples
        radius = math.sqrt(r2)
        phi = k * golden
        out.append((radius * math.cos(phi), radius * math.sin(phi), math.sqrt(max(0.0, 1.0 - r2))))
    return out


def bake_textures(values_at, xyz, tri, uv, normals, tangents, materials, colors, spec, folder, stem, eval_at, scale):
    ''' Makes the pictures `spec` asks for and writes them in `folder`.  `values_at(pts)` is the body (the union of the bodies) at the points; `xyz`, `tri` and `uv` the mesh as it is
        written (before it is turned into another unit) with the UVs of the set the pictures are for; `normals` and `tangents` the vertex normals and tangents; `materials` the list
        of materials (may be empty), `colors` the vertex colour channels or None; `scale` the largest side of the model in mm.  Returns (the pictures {map: path}, a report) '''
    started = time.time()
    size = spec.size
    texel, owner, w1, w2 = rasterize(uv, tri, size)
    count = len(texel)
    if not count:
        raise RuntimeError('textures: the UV map has no triangle with an area inside the picture')
    maps = list(spec.maps) if spec.maps else ['color', 'normal', 'orm']
    if spec.maps is None and any(m.emissive for m in materials):
        maps.append('emissive')
    if not materials:
        from fieldev.stdlib.materials import material
        base = [material('baked')]
    else:
        base = list(materials)
    see_through = any(isinstance(m.opacity, Shape) or m.opacity < 1.0 for m in base)
    h = max(scale * 0.002, 1e-6)
    distance = spec.distance if spec.distance is not None else 0.2 * scale
    directions = _hemisphere(spec.samples)
    steps = (0.04, 0.12, 0.28, 0.55, 1.0)
    want = {m: (m in maps) for m in _MAPS}
    channels = 4 if see_through else 3
    img = {
        'color': bytearray(b'\x80\x80\x80\xff' if see_through else b'\x80\x80\x80') * (size * size),
        'normal': bytearray(b'\x80\x80\xff') * (size * size),
        'orm': bytearray(b'\xff\x80\x00') * (size * size),
        'mr': bytearray(b'\xff\x80\x00') * (size * size),
        'occlusion': bytearray(b'\xff') * (size * size),
        'emissive': bytearray(3 * size * size),
    }
    chunk = 16384
    covered_rgb = [0.0, 0.0, 0.0]
    for start in range(0, count, chunk):
        stop = min(count, start + chunk)
        n = stop - start
        # the places on the flat triangles, and the frame of the mesh there
        P = array('f', [0.0]) * (3 * n)
        Nm = [[0.0] * n for _ in range(3)]
        Tm = [[0.0] * n for _ in range(3)]
        Wm = [1.0] * n
        for j in range(n):
            t = owner[start + j]
            c0, c1, c2 = tri[3 * t], tri[3 * t + 1], tri[3 * t + 2]
            b1, b2 = w1[start + j], w2[start + j]
            b0 = 1.0 - b1 - b2
            for c in range(3):
                P[3 * j + c] = b0 * xyz[3 * c0 + c] + b1 * xyz[3 * c1 + c] + b2 * xyz[3 * c2 + c]
                Nm[c][j] = b0 * normals[3 * c0 + c] + b1 * normals[3 * c1 + c] + b2 * normals[3 * c2 + c]
                Tm[c][j] = b0 * tangents[4 * c0 + c] + b1 * tangents[4 * c1 + c] + b2 * tangents[4 * c2 + c]
            Wm[j] = tangents[4 * c0 + 3]
        for j in range(n):
            ln = math.sqrt(Nm[0][j] ** 2 + Nm[1][j] ** 2 + Nm[2][j] ** 2) or 1.0
            Nm[0][j], Nm[1][j], Nm[2][j] = Nm[0][j] / ln, Nm[1][j] / ln, Nm[2][j] / ln
            d = Tm[0][j] * Nm[0][j] + Tm[1][j] * Nm[1][j] + Tm[2][j] * Nm[2][j]
            tx, ty, tz = Tm[0][j] - d * Nm[0][j], Tm[1][j] - d * Nm[1][j], Tm[2][j] - d * Nm[2][j]
            lt = math.sqrt(tx * tx + ty * ty + tz * tz) or 1.0
            Tm[0][j], Tm[1][j], Tm[2][j] = tx / lt, ty / lt, tz / lt
        # onto the real surface: one Newton step along the gradient, and the exact normal there
        Q = P
        if want['normal'] or want['orm'] or want['occlusion'] or True:
            f0 = values_at(P)
            g = surface_gradient(values_at, P, h)
            Q = array('f', P)
            limit = 0.05 * scale
            for j in range(n):
                g2 = g[0][j] ** 2 + g[1][j] ** 2 + g[2][j] ** 2
                if g2 > 1e-18:
                    s = f0[j] / g2
                    if abs(s) * math.sqrt(g2) <= limit:
                        Q[3 * j] -= s * g[0][j]
                        Q[3 * j + 1] -= s * g[1][j]
                        Q[3 * j + 2] -= s * g[2][j]
        g = surface_gradient(values_at, Q, h)
        Nt = [[0.0] * n for _ in range(3)]
        glen = [1.0] * n                    # (how fast the field grows across the surface here: 1 for a distance; the occlusion reads the field as a distance by it)
        for j in range(n):
            ln = math.sqrt(g[0][j] ** 2 + g[1][j] ** 2 + g[2][j] ** 2)
            if ln > 1e-12:
                Nt[0][j], Nt[1][j], Nt[2][j] = g[0][j] / ln, g[1][j] / ln, g[2][j] / ln
                glen[j] = max(0.25, ln)
            else:
                Nt[0][j], Nt[1][j], Nt[2][j] = Nm[0][j], Nm[1][j], Nm[2][j]
        # the materials: the last one whose `where` is negative at the place; the colour, the roughness ... of that one
        chosen = [-1] * n
        for k, m in enumerate(base):
            if m.where is None:
                chosen = [k] * n
            else:
                inside = _evaluate(eval_at, m.where, Q)
                chosen = [k if v < 0 else c for v, c in zip(inside, chosen)]
        rgb = [[0.8] * n for _ in range(3)]
        rough, metal, alpha = [0.5] * n, [0.0] * n, [1.0] * n
        glow = [[0.0] * n for _ in range(3)]
        for k, m in enumerate(base):
            spots = [j for j in range(n) if chosen[j] == k]
            if not spots:
                continue
            points = array('f')
            for j in spots:
                points.extend((Q[3 * j], Q[3 * j + 1], Q[3 * j + 2]))

            def value(v):
                if isinstance(v, Shape):
                    return _evaluate(eval_at, v, points)
                return [v] * len(spots)
            cols = [value(c) for c in m.color]
            for c in range(3):
                for s, j in enumerate(spots):
                    rgb[c][j] = cols[c][s]
            for s, j in enumerate(spots):
                pass
            r_vals, m_vals, a_vals = value(m.roughness), value(m.metallic), value(m.opacity)
            for s, j in enumerate(spots):
                rough[j], metal[j], alpha[j] = r_vals[s], m_vals[s], a_vals[s]
            if m.emissive:
                e = [value(c) for c in m.emissive]
                for c in range(3):
                    for s, j in enumerate(spots):
                        glow[c][j] = e[c][s]
        if colors is not None:
            for c in range(3):
                vals = _evaluate(eval_at, colors[c], Q) if isinstance(colors[c], Shape) else [float(colors[c])] * n
                rgb[c] = [a * min(1.0, max(0.0, b)) for a, b in zip(rgb[c], vals)]
        # the occlusion: rays over the hemisphere about the exact normal, and how far each gets before the field says something is in the way
        occlusion = [1.0] * n
        if (want['orm'] or want['occlusion']) and spec.strength > 0.0:
            frame_a = [[0.0] * n for _ in range(3)]
            frame_b = [[0.0] * n for _ in range(3)]
            for j in range(n):
                nx, ny, nz = Nt[0][j], Nt[1][j], Nt[2][j]
                ref = (1.0, 0.0, 0.0) if abs(nx) < 0.9 else (0.0, 1.0, 0.0)
                ax, ay, az = ny * ref[2] - nz * ref[1], nz * ref[0] - nx * ref[2], nx * ref[1] - ny * ref[0]
                la = math.sqrt(ax * ax + ay * ay + az * az) or 1.0
                ax, ay, az = ax / la, ay / la, az / la
                frame_a[0][j], frame_a[1][j], frame_a[2][j] = ax, ay, az
                frame_b[0][j], frame_b[1][j], frame_b[2][j] = ny * az - nz * ay, nz * ax - nx * az, nx * ay - ny * ax
            lift = 0.0015 * scale
            blocked = [0.0] * n
            for dx, dy, dz in directions:
                ray = [[dx * frame_a[c][j] + dy * frame_b[c][j] + dz * Nt[c][j] for j in range(n)] for c in range(3)]
                see = [1.0] * n
                for step in steps:
                    t = distance * step + lift
                    pts = array('f', [0.0]) * (3 * n)
                    for c in range(3):
                        pts[c::3] = array('f', [Q[3 * j + c] + t * ray[c][j] for j in range(n)])
                    field = values_at(pts)
                    # (a soft shadow: the ray is free when the field grows at a quarter of the rate it would along open space, blocked where it is 0, and between them it is the penumbra --
                    # the field need not be a distance, and a ray that only passes a bump of it is not a shadow)
                    cone = [max(0.0, min(1.0, 4.0 * f / (t * dz * gl))) if dz > 1e-3 else 1.0 for f, gl in zip(field, glen)]
                    see = [a if a < b else b for a, b in zip(see, cone)]
                weight = dz
                blocked = [b + weight * (1.0 - s) for b, s in zip(blocked, see)]
            total = sum(d[2] for d in directions)
            occlusion = [max(0.0, 1.0 - spec.strength * b / total) for b in blocked]
        # into the pictures
        for j in range(n):
            at = texel[start + j]
            if want['color']:
                if see_through:
                    img['color'][4 * at:4 * at + 4] = bytes((_srgb(rgb[0][j]), _srgb(rgb[1][j]), _srgb(rgb[2][j]), _byte(alpha[j])))
                else:
                    img['color'][3 * at:3 * at + 3] = bytes((_srgb(rgb[0][j]), _srgb(rgb[1][j]), _srgb(rgb[2][j])))
            if want['normal']:
                bx, by, bz = Nm[1][j] * Tm[2][j] - Nm[2][j] * Tm[1][j], Nm[2][j] * Tm[0][j] - Nm[0][j] * Tm[2][j], Nm[0][j] * Tm[1][j] - Nm[1][j] * Tm[0][j]
                w = Wm[j]
                nx = Nt[0][j] * Tm[0][j] + Nt[1][j] * Tm[1][j] + Nt[2][j] * Tm[2][j]
                ny = w * (Nt[0][j] * bx + Nt[1][j] * by + Nt[2][j] * bz)
                nz = Nt[0][j] * Nm[0][j] + Nt[1][j] * Nm[1][j] + Nt[2][j] * Nm[2][j]
                ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                img['normal'][3 * at:3 * at + 3] = bytes((_byte(0.5 + 0.5 * nx / ln), _byte(0.5 + 0.5 * ny / ln), _byte(0.5 + 0.5 * nz / ln)))
            if want['orm']:
                img['orm'][3 * at:3 * at + 3] = bytes((_byte(occlusion[j]), _byte(rough[j]), _byte(metal[j])))
            if want['mr']:
                img['mr'][3 * at:3 * at + 3] = bytes((255, _byte(rough[j]), _byte(metal[j])))
            if want['occlusion']:
                img['occlusion'][at] = _byte(occlusion[j])
            if want['emissive']:
                img['emissive'][3 * at:3 * at + 3] = bytes((_srgb(glow[0][j]), _srgb(glow[1][j]), _srgb(glow[2][j])))
    # the padding: the texels beside an island take what the island has at its edge
    if spec.padding:
        bytes_per = {'color': channels, 'normal': 3, 'orm': 3, 'mr': 3, 'occlusion': 1, 'emissive': 3}
        _dilate(img, [m for m in maps], bytes_per, texel, size, spec.padding)
    written = {}
    for m in maps:
        name = '%s_%s.png' % (stem, m)
        pixels = bytes(img[m])
        if m == 'occlusion':
            pngfile.write_png(os.path.join(folder, name), size, size, pixels, 1)
        else:
            pngfile.write_png(os.path.join(folder, name), size, size, pixels, channels if m == 'color' else 3)
        written[m] = name
    report = {'size': size, 'texels': count, 'coverage': count / float(size * size), 'maps': maps, 'seconds': time.time() - started, 'see_through': see_through}
    return written, report


def _dilate(img, maps, bytes_per, texel, size, rounds):
    ''' Grows what is painted by `rounds` texels in every direction: an empty texel beside a painted one takes the value of it '''
    mask = bytearray(size * size)
    for at in texel:
        mask[at] = 1
    frontier = []
    for at in texel:
        x, y = at % size, at // size
        if (x > 0 and not mask[at - 1]) or (x < size - 1 and not mask[at + 1]) or (y > 0 and not mask[at - size]) or (y < size - 1 and not mask[at + size]):
            frontier.append(at)
    for _ in range(rounds):
        grown = {}
        for at in frontier:
            x, y = at % size, at // size
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < size and 0 <= ny < size:
                    to = ny * size + nx
                    if not mask[to] and to not in grown:
                        grown[to] = at
        for to, source in grown.items():
            for m in maps:
                k = bytes_per[m]
                img[m][k * to:k * to + k] = img[m][k * source:k * source + k]
        for to in grown:
            mask[to] = 1
        frontier = list(grown)


# ---------------------------------------------------------------------------
# The layout of a UV map, as a picture

def write_uv_layout(path, uv, tri, size=1024):
    ''' A picture of a UV map: the islands in grey on a dark ground and the edges of the triangles in white, v up.  Returns the path '''
    texel, _, _, _ = rasterize(uv, tri, size)
    pixels = bytearray(b'\x18\x18\x18') * (size * size)
    for at in texel:
        pixels[3 * at:3 * at + 3] = b'\x50\x58\x60'

    def line(x0, y0, x1, y1):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for s in range(steps + 1):
            f = s / float(steps)
            x, y = int(x0 + (x1 - x0) * f), int(y0 + (y1 - y0) * f)
            if 0 <= x < size and 0 <= y < size:
                pixels[3 * (y * size + x):3 * (y * size + x) + 3] = b'\xe8\xe8\xe8'
    for t in range(len(tri) // 3):
        pts = [(uv[2 * tri[3 * t + k]] * size, (1.0 - uv[2 * tri[3 * t + k] + 1]) * size) for k in range(3)]
        for k in range(3):
            line(pts[k][0], pts[k][1], pts[(k + 1) % 3][0], pts[(k + 1) % 3][1])
    return pngfile.write_png(path, size, size, bytes(pixels), 3)
