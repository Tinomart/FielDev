'''
UV maps: how a surface is laid out on a texture.

    export_mesh(hero, "hero.glb", uvs="unwrap")                      the surface cut into islands and packed into the 0 to 1 square (a texture atlas)
    export_mesh(hero, "hero.glb", uvs=uv_unwrap(angle=45, margin=8))    the same, with the angle an island may bend by and the gap between islands
    export_mesh(crate, "crate.obj", uvs=uv_box(500))                 a texture that repeats every 500 mm, going on from one face to the next
    export_mesh(pole, "pole.obj", uvs=uv_cylinder("z"))              wrapped once round the z axis
    export_mesh(ball, "ball.obj", uvs=[uv_sphere(), uv_unwrap(margin=8)])   two sets: the second one (TEXCOORD_1) is for a lightmap
    export_mesh(hero, "hero.glb", uvs="armature")                       a character laid out part by part: each armature as a tube along its path, each set of stitching loops flat as it was drawn

A UV map gives every corner of every triangle a place (u, v) on the texture, v up.  The vertices that are in triangles with different places are made again for each
(a seam of the texture).  Two maps are made at most by an export: the first is the one the baked textures are made for.

    uv_box(size=None)        each triangle is projected along the axis its normal is mostly along, seen from outside.  size: the millimetres one repeat of the texture covers,
                             from one common origin (the texture goes on from one surface to the next); None: the texture fits each side once
    uv_planar(axis="z", size=None)   the whole surface along one axis, "x", "y" or "z" ("-z": from below); size as above
    uv_cylinder(axis="z", turns=1, size=None)   u is the angle round the axis (`turns` times round the texture), v the height: size is the millimetres of one repeat of v (None: once up the
                             height of the model)
    uv_sphere(axis="z")      u is the longitude, v the latitude, round the middle of the model's box
    uv_unwrap(angle=60, margin=4, size=1024)   the surface is cut into islands, each laid flat, all at one scale (one texel is the same size everywhere), and packed into the square
                             with `margin` texels of a `size` x `size` texture between them.  The report (`.report` after the export) has the islands, how much of the square they
                             cover and the millimetres of a texel

The unwrap works in four steps.  (1) The islands: grown from the largest triangle left over the neighbours whose normal is within `angle` degrees of the island's average; the small
ones that are left between the large are taken into the island they touch the most when they fit it (within one and a half times the angle).  (2) Each island is laid flat: by the
CONFORMAL map (LSCM, least squares conformal maps: angles are kept, so a texture is not sheared) when the island is a disc of at most 6000 triangles, else by projection along its
average normal.  (3) Each is scaled to the same density, and turned to the angle where its box is smallest.  (4) The boxes are packed in the square (maximal rectangles, a quarter turn
allowed) at the largest scale where they fit.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math
from array import array

__all__ = ['uv_box', 'uv_planar', 'uv_cylinder', 'uv_sphere', 'uv_unwrap', 'uv_armature', 'UVMap']

# The six faces of the box projection: the axis the normal of a triangle is mostly along and its side (+x -x +y -y +z -z) -> (u, v) of a point (x, y, z), seen
# from outside with v up, so that a texture reads the same way on every side and is not mirrored on the back ones
_BOX_UV = (
    lambda x, y, z: (y, z),
    lambda x, y, z: (-y, z),
    lambda x, y, z: (-x, z),
    lambda x, y, z: (x, z),
    lambda x, y, z: (x, y),
    lambda x, y, z: (x, -y),
)
_FACES = {'+x': 0, 'x': 0, '-x': 1, '+y': 2, 'y': 2, '-y': 3, '+z': 4, 'z': 4, '-z': 5}
_LSCM_LIMIT = 6000          # (the triangles of an island above which it is laid flat by projection: the conformal map takes a time that grows faster than the island)


def _used_range(xyz, tri):
    ''' (lo, hi) of the vertices that triangles use: a mesh may carry vertices that no triangle has, and they are not part of the model '''
    used = set(tri)
    lo = [min(xyz[3 * i + c] for i in used) for c in range(3)]
    hi = [max(xyz[3 * i + c] for i in used) for c in range(3)]
    return lo, hi


class UVMap:
    ''' A way to lay a surface on a texture: see uv_box, uv_planar, uv_cylinder, uv_sphere and uv_unwrap '''

    def __init__(self, kind, **options):
        self.kind = kind
        self.options = options
        self.report = None              # (what the last export made of it: only the unwrap has one)

    def __repr__(self):
        return 'uv_%s(%s)' % (self.kind, ', '.join('%s=%r' % kv for kv in sorted(self.options.items())))

    def corner_uvs(self, xyz, tri):
        ''' u and v of every corner of every triangle: a flat f array, (u, v) three times for each triangle '''
        return getattr(self, '_' + self.kind)(xyz, tri, **self.options)

    # -- the projections ---------------------------------------------------------------------------------------------------------------

    def _box(self, xyz, tri, size):
        nt = len(tri) // 3
        fit = size is None
        raw, side = array('f'), array('B')
        for t in range(nt):
            corners = (tri[3 * t], tri[3 * t + 1], tri[3 * t + 2])
            p = [(xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]) for i in corners]
            nx, ny, nz = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
            ax, ay, az = abs(nx), abs(ny), abs(nz)
            if az >= ax and az >= ay:
                face = 4 if nz >= 0 else 5
            elif ax >= ay:
                face = 0 if nx >= 0 else 1
            else:
                face = 2 if ny >= 0 else 3
            for q in p:
                raw.extend(_BOX_UV[face](*q))
                side.append(face)
        us, vs = raw[0::2], raw[1::2]
        if fit:
            lo, hi = _used_range(xyz, tri)
            size = max(hi[c] - lo[c] for c in range(3)) or 1.0
            low = {}
            for u, v, f in zip(us, vs, side):
                lu, lv = low.get(f, (u, v))
                low[f] = (min(lu, u), min(lv, v))
            shift_u, shift_v = [low[f][0] for f in side], [low[f][1] for f in side]
        else:
            shift_u, shift_v = [min(us)] * len(us), [min(vs)] * len(vs)
        out = array('f', [0.0]) * len(raw)
        out[0::2] = array('f', [(u - s) / size for u, s in zip(us, shift_u)])
        out[1::2] = array('f', [(v - s) / size for v, s in zip(vs, shift_v)])
        return out

    def _planar(self, xyz, tri, axis, size):
        face = _FACES[axis]
        raw = array('f')
        for k in range(len(tri)):
            i = tri[k]
            raw.extend(_BOX_UV[face](xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]))
        us, vs = raw[0::2], raw[1::2]
        low_u, low_v = min(us), min(vs)
        if size is None:
            size = max(max(us) - low_u, max(vs) - low_v) or 1.0
        out = array('f', [0.0]) * len(raw)
        out[0::2] = array('f', [(u - low_u) / size for u in us])
        out[1::2] = array('f', [(v - low_v) / size for v in vs])
        return out

    def _round(self, xyz, tri, axis, turns, size, sphere):
        ''' The cylinder and the sphere: u from the angle round the axis, v from the height (or the latitude) '''
        c = 'xyz'.index(axis)
        a, b = (c + 1) % 3, (c + 2) % 3             # (the two others, in the order that turns from the first to the second round the axis)
        lo, hi = _used_range(xyz, tri)
        mid_a, mid_b = (lo[a] + hi[a]) / 2.0, (lo[b] + hi[b]) / 2.0
        mid_c = (lo[c] + hi[c]) / 2.0
        height = (hi[c] - lo[c]) or 1.0
        nv = len(xyz) // 3
        angle, level = array('f', [0.0]) * nv, array('f', [0.0]) * nv
        for i in range(nv):
            da, db = xyz[3 * i + a] - mid_a, xyz[3 * i + b] - mid_b
            angle[i] = math.atan2(db, da) / (2.0 * math.pi) + 0.5
            if sphere:
                r = math.sqrt(da * da + db * db + (xyz[3 * i + c] - mid_c) ** 2) or 1.0
                level[i] = (math.asin(max(-1.0, min(1.0, (xyz[3 * i + c] - mid_c) / r))) + math.pi / 2.0) / math.pi
            else:
                level[i] = (xyz[3 * i + c] - lo[c]) / (size if size is not None else height)
        out = array('f')
        for t in range(0, len(tri), 3):
            corners = (tri[t], tri[t + 1], tri[t + 2])
            us = [angle[i] for i in corners]
            if max(us) - min(us) > 0.5:             # (a triangle across the seam: the corners on the small side go round to the other)
                us = [u + 1.0 if u < 0.5 else u for u in us]
            for u, i in zip(us, corners):
                out.extend((u * turns, level[i]))
        return out

    def _cylinder(self, xyz, tri, axis, turns, size):
        return self._round(xyz, tri, axis, turns, size, False)

    def _sphere(self, xyz, tri, axis):
        return self._round(xyz, tri, axis, 1.0, None, True)

    def _armature(self, xyz, tri, parts, margin, size, axis):
        from fieldev.stdlib import uvparts
        if parts is None:
            raise ValueError('uv_armature: the model has no parts to unwrap by -- export a character made of armatures and stitching loops (character([armature(...), stitching_loops(...)])), '
                             'or give the parts: uv_armature([arm, face, ...])')
        out, self.report = uvparts.unwrap_parts(xyz, tri, parts, margin, size, axis)
        return out

    # -- the unwrap --------------------------------------------------------------------------------------------------------------------

    def _unwrap(self, xyz, tri, angle, margin, size):
        nt = len(tri) // 3
        normal, area = [None] * nt, [0.0] * nt
        for t in range(nt):
            p = [(xyz[3 * tri[3 * t + k]], xyz[3 * tri[3 * t + k] + 1], xyz[3 * tri[3 * t + k] + 2]) for k in range(3)]
            n = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
            length = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
            area[t] = 0.5 * length
            normal[t] = (n[0] / length, n[1] / length, n[2] / length) if length > 1e-30 else (0.0, 0.0, 1.0)
        # (the triangles that share an edge are neighbours)
        edges = {}
        for t in range(nt):
            corners = (tri[3 * t], tri[3 * t + 1], tri[3 * t + 2])
            for k in range(3):
                a, b = corners[k], corners[(k + 1) % 3]
                edges.setdefault((a, b) if a < b else (b, a), []).append(t)
        neighbours = [[] for _ in range(nt)]
        for pair in edges.values():
            if len(pair) == 2:
                neighbours[pair[0]].append(pair[1])
                neighbours[pair[1]].append(pair[0])
        # (the direction of a triangle that the islands are grown by: on a rough surface -- noise, rock, a mesh whose triangles are smaller than the bumps -- the normal of every triangle
        # is turned by a different amount, and islands grown on those would be a few triangles each.  A rough surface is smoothed, the more the rougher it is: each normal made the mean
        # of its own and its neighbours', so the islands follow the shape and not the bumps; a surface of flat faces is left as it is)
        turns, count = 0.0, 0
        for pair in edges.values():
            if len(pair) == 2:
                d = sum(normal[pair[0]][c] * normal[pair[1]][c] for c in range(3))
                turns += math.acos(max(-1.0, min(1.0, d)))
                count += 1
        rough = turns / count if count else 0.0
        passes = 4 if rough > 0.35 else (2 if rough > 0.2 else (1 if rough > 0.1 else 0))
        for _ in range(passes):
            mean = []
            for t in range(nt):
                sx, sy, sz = (c * area[t] for c in normal[t])
                for g in neighbours[t]:
                    sx, sy, sz = sx + normal[g][0] * area[g], sy + normal[g][1] * area[g], sz + normal[g][2] * area[g]
                length = math.sqrt(sx * sx + sy * sy + sz * sz)
                mean.append((sx / length, sy / length, sz / length) if length > 1e-30 else normal[t])
            normal = mean
        # (1) the islands: grown from the largest triangle left, over the neighbours whose normal is within `angle` of the island's average
        limit = math.cos(math.radians(angle))
        island_of = [-1] * nt
        faces, normals_sum, areas = [], [], []
        for seed in sorted(range(nt), key=lambda t: -area[t]):
            if island_of[seed] != -1:
                continue
            number = len(faces)
            members, queue = [seed], [seed]
            island_of[seed] = number
            sx, sy, sz = (c * area[seed] for c in normal[seed])
            total = area[seed]
            at = 0
            while at < len(queue):
                for g in neighbours[queue[at]]:
                    if island_of[g] != -1:
                        continue
                    length = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
                    ng = normal[g]
                    if (ng[0] * sx + ng[1] * sy + ng[2] * sz) / length >= limit:
                        island_of[g] = number
                        members.append(g)
                        queue.append(g)
                        sx, sy, sz = sx + ng[0] * area[g], sy + ng[1] * area[g], sz + ng[2] * area[g]
                        total += area[g]
                at += 1
            faces.append(members)
            normals_sum.append([sx, sy, sz])
            areas.append(total)
        relaxed = math.cos(math.radians(min(89.0, angle * 1.5)))
        # (the edges of the islands, made smooth: a triangle with two of its three neighbours in another island, and a normal that fits it, goes over to it -- the growth over a mesh
        # whose normals are not quite smooth leaves teeth along the edge.  Such a triangle is a leaf of its island, so the island stays in one piece)
        for _ in range(3):
            moved = 0
            for t in range(nt):
                c = island_of[t]
                counts = {}
                for g in neighbours[t]:
                    counts[island_of[g]] = counts.get(island_of[g], 0) + 1
                for d, k in counts.items():
                    if d == c or k < 2:
                        continue
                    length = math.sqrt(sum(v * v for v in normals_sum[d])) or 1.0
                    if sum(normal[t][j] * normals_sum[d][j] for j in range(3)) / length < relaxed:
                        continue
                    for j in range(3):
                        normals_sum[c][j] -= normal[t][j] * area[t]
                        normals_sum[d][j] += normal[t][j] * area[t]
                    areas[c] -= area[t]
                    areas[d] += area[t]
                    island_of[t] = d
                    moved += 1
                    break
            if not moved:
                break
        faces = [[] for _ in faces]
        for t in range(nt):
            faces[island_of[t]].append(t)
        for k in range(len(faces)):
            if not faces[k]:
                faces[k] = None
        # (the small islands left between the large are taken into the one they share most of their edge with, when all their triangles fit it within one and a half times the angle)
        adjacent = [dict() for _ in faces]
        for (a, b), pair in edges.items():
            if len(pair) == 2 and island_of[pair[0]] != island_of[pair[1]]:
                ia, ib = island_of[pair[0]], island_of[pair[1]]
                length = math.sqrt(sum((xyz[3 * a + c] - xyz[3 * b + c]) ** 2 for c in range(3)))
                adjacent[ia][ib] = adjacent[ia].get(ib, 0.0) + length
                adjacent[ib][ia] = adjacent[ib].get(ia, 0.0) + length
        small = 0.01 * sum(areas)
        for c in sorted(range(len(faces)), key=lambda k: areas[k]):
            if faces[c] is None or areas[c] >= small:
                continue
            best = None
            for d, shared in sorted(adjacent[c].items(), key=lambda kv: -kv[1]):
                length = math.sqrt(sum(v * v for v in normals_sum[d])) or 1.0
                axis = tuple(v / length for v in normals_sum[d])
                if all(normal[t][0] * axis[0] + normal[t][1] * axis[1] + normal[t][2] * axis[2] >= relaxed for t in faces[c]):
                    best = d
                    break
            if best is None:
                continue
            faces[best].extend(faces[c])
            for k in range(3):
                normals_sum[best][k] += normals_sum[c][k]
            areas[best] += areas[c]
            for e, shared in adjacent[c].items():
                if e == best:
                    continue
                adjacent[best][e] = adjacent[best].get(e, 0.0) + shared
                adjacent[e][best] = adjacent[e].get(best, 0.0) + shared
                del adjacent[e][c]
            del adjacent[best][c]
            adjacent[c] = {}
            faces[c] = None
        islands = [(faces[k], tuple(v / (math.sqrt(sum(w * w for w in normals_sum[k])) or 1.0) for v in normals_sum[k])) for k in range(len(faces)) if faces[k] is not None]
        # (2) each island laid flat, (3) at the same density, turned to the angle where its box is smallest
        flat, conformal, projected = [], 0, 0
        stretch = []
        for members, n in islands:
            coords = _lay_flat(xyz, tri, members, n)
            if coords[1]:
                conformal += 1
            else:
                projected += 1
            uv = coords[0]                         # the (u, v) of every corner of every triangle of the island, in mm
            total_uv = sum(abs(_area2(uv[3 * s], uv[3 * s + 1], uv[3 * s + 2])) for s in range(len(members)))
            total_3d = sum(area[t] for t in members)
            if total_uv > 1e-20 and total_3d > 0.0:
                k = math.sqrt(total_3d / total_uv)
                uv = [(u * k, v * k) for u, v in uv]
            uv, width, height = _tightest(uv)
            flat.append((members, uv, width, height))
        # (4) the boxes in the square: the largest scale where they fit
        margin_uv = float(margin) / float(size)
        scale, place = _pack(flat, margin_uv)
        out = array('f', [0.0]) * (6 * nt)
        covered = 0.0
        for number, (members, uv, width, height) in enumerate(flat):
            x0, y0, turned = place[number]
            for slot, t in enumerate(members):
                for k in range(3):
                    u, v = uv[3 * slot + k]
                    if turned:
                        u, v = v, width - u
                    out[6 * t + 2 * k] = x0 + u * scale
                    out[6 * t + 2 * k + 1] = y0 + v * scale
        for t in range(nt):
            covered += abs(_area2((out[6 * t], out[6 * t + 1]), (out[6 * t + 2], out[6 * t + 3]), (out[6 * t + 4], out[6 * t + 5])))
        ratios = sorted(abs(_area2((out[6 * t], out[6 * t + 1]), (out[6 * t + 2], out[6 * t + 3]), (out[6 * t + 4], out[6 * t + 5]))) / area[t] for t in range(nt) if area[t] > 1e-12)
        median = ratios[len(ratios) // 2] if ratios else 1.0
        self.report = {'islands': len(flat), 'conformal': conformal, 'projected': projected, 'coverage': covered, 'size': size, 'smoothing': passes, 'roughness': rough,
                       'mm_per_texel': (1.0 / (math.sqrt(median) * size)) if median > 0 else None,
                       'stretch': (ratios[len(ratios) // 100] / median, ratios[-1 - len(ratios) // 100] / median) if ratios else None}
        return out


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _area2(a, b, c):
    ''' The signed area of a triangle in the plane (counter-clockwise: above 0) '''
    return 0.5 * ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def _lay_flat(xyz, tri, members, n):
    ''' An island laid flat: ([(u, v) of every corner of its triangles], conformal): by the conformal map when the island is a disc of a size it can take, else by projection along
        its average direction `n`, with "up" in the model as up in the plane as far as it can be '''
    up = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (0.0, 1.0, 0.0)
    d = up[0] * n[0] + up[1] * n[1] + up[2] * n[2]
    v_axis = (up[0] - d * n[0], up[1] - d * n[1], up[2] - d * n[2])
    length = math.sqrt(sum(c * c for c in v_axis)) or 1.0
    v_axis = (v_axis[0] / length, v_axis[1] / length, v_axis[2] / length)
    u_axis = _cross(v_axis, n)
    local, vertices = {}, []
    for t in members:
        for k in range(3):
            i = tri[3 * t + k]
            if i not in local:
                local[i] = len(vertices)
                vertices.append(i)
    planar = [(xyz[3 * i] * u_axis[0] + xyz[3 * i + 1] * u_axis[1] + xyz[3 * i + 2] * u_axis[2],
               xyz[3 * i] * v_axis[0] + xyz[3 * i + 1] * v_axis[1] + xyz[3 * i + 2] * v_axis[2]) for i in vertices]
    corners = [[local[tri[3 * t + k]] for k in range(3)] for t in members]
    projected = [planar[c] for tri_c in corners for c in tri_c]
    if len(members) > _LSCM_LIMIT or len(members) < 4:
        return projected, False
    # a disc: one boundary loop, and as many vertices and faces as edges say (V - E + F = 1)
    count = {}
    for c0, c1, c2 in corners:
        for a, b in ((c0, c1), (c1, c2), (c2, c0)):
            key = (a, b) if a < b else (b, a)
            count[key] = count.get(key, 0) + 1
    if len(vertices) - len(count) + len(members) != 1 or any(v > 2 for v in count.values()):
        return projected, False
    solved = _conformal(xyz, vertices, corners, planar)
    if solved is None:
        return projected, False
    return [solved[c] for tri_c in corners for c in tri_c], True


def _conformal(xyz, vertices, corners, start):
    ''' The least squares conformal map (Levy et al.) of a disc of triangles: the (u, v) of every vertex, or None when it folds.  Each triangle is laid in its own plane; the condition that
        the map is conformal there is linear in the (u, v) of its three corners; two vertices -- far apart on the boundary -- are held where the projection has them, and the least
        squares of the rest is found by conjugate gradients from the projection '''
    n = len(vertices)
    rows = []                       # per triangle: (the three vertices, s * ex, s * ey)
    for c0, c1, c2 in corners:
        p0, p1, p2 = (tuple(xyz[3 * vertices[c] + k] for k in range(3)) for c in (c0, c1, c2))
        e01, e02 = _sub(p1, p0), _sub(p2, p0)
        x1 = math.sqrt(e01[0] ** 2 + e01[1] ** 2 + e01[2] ** 2)
        if x1 < 1e-20:
            return None
        x2 = (e01[0] * e02[0] + e01[1] * e02[1] + e01[2] * e02[2]) / x1
        y2 = math.sqrt(max(e02[0] ** 2 + e02[1] ** 2 + e02[2] ** 2 - x2 * x2, 0.0))
        d = x1 * y2
        if d < 1e-20:
            return None
        s = 1.0 / math.sqrt(d)
        # the edge opposite each vertex, as a number in the plane of the triangle: z0 = (0, 0), z1 = (x1, 0), z2 = (x2, y2)
        ex = (s * (x2 - x1), s * (0.0 - x2), s * (x1 - 0.0))
        ey = (s * (y2 - 0.0), s * (0.0 - y2), s * (0.0 - 0.0))
        rows.append((c0, c1, c2, ex, ey))
    # the two pins: the vertex farthest from the middle of the projection, and the one farthest from it
    mx = sum(p[0] for p in start) / n
    my = sum(p[1] for p in start) / n
    a = max(range(n), key=lambda i: (start[i][0] - mx) ** 2 + (start[i][1] - my) ** 2)
    b = max(range(n), key=lambda i: (start[i][0] - start[a][0]) ** 2 + (start[i][1] - start[a][1]) ** 2)
    if a == b:
        return None
    u = [p[0] for p in start]
    v = [p[1] for p in start]
    free = [True] * n
    free[a] = free[b] = False
    diagonal = [0.0] * n
    for c0, c1, c2, ex, ey in rows:
        for slot, c in enumerate((c0, c1, c2)):
            diagonal[c] += ex[slot] * ex[slot] + ey[slot] * ey[slot]
    for i in range(n):
        if not free[i] or diagonal[i] < 1e-30:
            diagonal[i] = 1.0

    def gradient(u, v):
        ''' A^T A applied to (u, v), for the free vertices '''
        gu, gv = [0.0] * n, [0.0] * n
        for c0, c1, c2, ex, ey in rows:
            r1 = ex[0] * u[c0] - ey[0] * v[c0] + ex[1] * u[c1] - ey[1] * v[c1] + ex[2] * u[c2] - ey[2] * v[c2]
            r2 = ey[0] * u[c0] + ex[0] * v[c0] + ey[1] * u[c1] + ex[1] * v[c1] + ey[2] * u[c2] + ex[2] * v[c2]
            gu[c0] += ex[0] * r1 + ey[0] * r2
            gv[c0] += -ey[0] * r1 + ex[0] * r2
            gu[c1] += ex[1] * r1 + ey[1] * r2
            gv[c1] += -ey[1] * r1 + ex[1] * r2
            gu[c2] += ex[2] * r1 + ey[2] * r2
            gv[c2] += -ey[2] * r1 + ex[2] * r2
        return gu, gv
    gu, gv = gradient(u, v)
    ru = [(-gu[i] if free[i] else 0.0) for i in range(n)]
    rv = [(-gv[i] if free[i] else 0.0) for i in range(n)]
    zu = [ru[i] / diagonal[i] for i in range(n)]
    zv = [rv[i] / diagonal[i] for i in range(n)]
    pu, pv = zu[:], zv[:]
    rz = sum(ru[i] * zu[i] + rv[i] * zv[i] for i in range(n))
    r0 = math.sqrt(sum(ru[i] * ru[i] + rv[i] * rv[i] for i in range(n))) or 1.0
    for _ in range(min(600, 4 * n)):
        qu, qv = gradient(pu, pv)
        for i in range(n):
            if not free[i]:
                qu[i] = qv[i] = 0.0
        pq = sum(pu[i] * qu[i] + pv[i] * qv[i] for i in range(n))
        if abs(pq) < 1e-300:
            break
        alpha = rz / pq
        for i in range(n):
            u[i] += alpha * pu[i]
            v[i] += alpha * pv[i]
            ru[i] -= alpha * qu[i]
            rv[i] -= alpha * qv[i]
        if math.sqrt(sum(ru[i] * ru[i] + rv[i] * rv[i] for i in range(n))) < 1e-7 * r0:
            break
        zu = [ru[i] / diagonal[i] for i in range(n)]
        zv = [rv[i] / diagonal[i] for i in range(n)]
        rz_new = sum(ru[i] * zu[i] + rv[i] * zv[i] for i in range(n))
        beta = rz_new / rz if rz > 0 else 0.0
        rz = rz_new
        pu = [zu[i] + beta * pu[i] for i in range(n)]
        pv = [zv[i] + beta * pv[i] for i in range(n)]
    # (seen from outside, counter-clockwise: when most triangles came out turned over the map is the mirror image: it is mirrored back; when it still folds it is not used)
    signs = [_area2((u[c0], v[c0]), (u[c1], v[c1]), (u[c2], v[c2])) for c0, c1, c2, _, _ in rows]
    negative = sum(1 for s in signs if s < 0.0)
    if negative > 0.5 * len(signs):
        u = [-x for x in u]
        negative = len(signs) - negative
    if negative > 0.02 * len(signs):
        return None
    return list(zip(u, v))


def _tightest(uv):
    ''' The corners (u, v) turned to the angle (a multiple of 3 degrees, to a quarter turn) where the box of them is the smallest, then moved to start at (0, 0): (the corners, the width,
        the height).  A box that is taller than wide is turned a quarter, so it is wide '''
    best = None
    sample = uv if len(uv) <= 3000 else uv[::max(1, len(uv) // 3000)]
    for step in range(30):
        a = math.radians(3.0 * step)
        c, s = math.cos(a), math.sin(a)
        us = [c * u - s * v for u, v in sample]
        vs = [s * u + c * v for u, v in sample]
        w, h = max(us) - min(us), max(vs) - min(vs)
        if best is None or w * h < best[0] * (1.0 - 1e-9):
            best = (w * h, step)
    a = math.radians(3.0 * best[1])
    c, s = math.cos(a), math.sin(a)
    turned = [(c * u - s * v, s * u + c * v) for u, v in uv]
    lu, hu = min(p[0] for p in turned), max(p[0] for p in turned)
    lv, hv = min(p[1] for p in turned), max(p[1] for p in turned)
    width, height = hu - lu, hv - lv
    if height > width:
        return [(v - lv, hu - u) for u, v in turned], height, width
    return [(u - lu, v - lv) for u, v in turned], width, height


class _Free:
    ''' The free rectangles of a square that boxes are put in (maximal rectangles, best short side fit) '''

    def __init__(self, width, height):
        self.free = [(0.0, 0.0, width, height)]

    def insert(self, w, h, turn=True):
        ''' (x, y, turned) where a box of w x h goes, or None (`turn`: it may go a quarter turn) '''
        best = None
        for fx, fy, fw, fh in self.free:
            for turned, bw, bh in ((False, w, h), (True, h, w)) if turn else ((False, w, h),):
                if bw <= fw + 1e-12 and bh <= fh + 1e-12:
                    score = (min(fw - bw, fh - bh), max(fw - bw, fh - bh))
                    if best is None or score < best[0]:
                        best = (score, fx, fy, bw, bh, turned)
        if best is None:
            return None
        _, x, y, bw, bh, turned = best
        old, new = [], []
        for fx, fy, fw, fh in self.free:
            if x >= fx + fw - 1e-12 or x + bw <= fx + 1e-12 or y >= fy + fh - 1e-12 or y + bh <= fy + 1e-12:
                old.append((fx, fy, fw, fh))
                continue
            if x > fx + 1e-12:
                new.append((fx, fy, x - fx, fh))
            if x + bw < fx + fw - 1e-12:
                new.append((x + bw, fy, fx + fw - x - bw, fh))
            if y > fy + 1e-12:
                new.append((fx, fy, fw, y - fy))
            if y + bh < fy + fh - 1e-12:
                new.append((fx, y + bh, fw, fy + fh - y - bh))
        # (what the box cut is kept as the pieces; a piece that lies inside another rectangle is dropped -- only the new ones can, they are parts of old ones)
        keep = []
        everything = old + new
        for i, r in enumerate(new):
            inside = False
            for o in everything:
                if o is not r and o[0] <= r[0] + 1e-12 and o[1] <= r[1] + 1e-12 and o[0] + o[2] >= r[0] + r[2] - 1e-12 and o[1] + o[3] >= r[1] + r[3] - 1e-12 and (o != r or any(p is o for p in keep)):
                    inside = True
                    break
            if not inside:
                keep.append(r)
        self.free = old + keep
        return x, y, turned


def _pack(flat, margin, turn=True):
    ''' (the scale, {island: (x, y, turned)}): the boxes of the islands (width, height in mm, margin on every side) in the square, at the largest scale where they all fit
        (`turn`: they may be put a quarter turn) '''
    order = sorted(range(len(flat)), key=lambda k: -max(flat[k][2], flat[k][3]))
    widest = max(max(f[2], f[3]) for f in flat) or 1.0
    total = sum(f[2] * f[3] for f in flat) or 1.0

    def attempt(scale):
        pack = _Free(1.0, 1.0)
        place = {}
        for k in order:
            w, h = flat[k][2] * scale + 2.0 * margin, flat[k][3] * scale + 2.0 * margin
            if max(w, h) > 1.0 + 1e-9:
                return None
            spot = pack.insert(w, h, turn)
            if spot is None:
                return None
            place[k] = (spot[0] + margin, spot[1] + margin, spot[2])
        return place
    low, high = 0.0, min((1.0 - 2.0 * margin) / widest, 1.0 / math.sqrt(total))
    best = None
    for _ in range(28):
        mid = 0.5 * (low + high)
        got = attempt(mid) if mid > 0 else None
        if got is not None:
            low, best = mid, got
        else:
            high = mid
    if best is None:                                    # (so many islands that the margins fill the square: the margins give way)
        return _pack(flat, margin * 0.5, turn) if margin > 1e-6 else (low, {k: (0.0, 0.0, False) for k in range(len(flat))})
    return low, best


def _size_of(size, what):
    if size is None:
        return None
    size = float(size)
    if not size > 0:
        raise ValueError('%s: the millimetres of one repeat of the texture are above 0, not %r' % (what, size))
    return size


def _axis_of(axis, what, signed=False):
    text = str(axis).strip().lower()
    allowed = ('x', 'y', 'z', '-x', '-y', '-z', '+x', '+y', '+z') if signed else ('x', 'y', 'z')
    if text not in allowed:
        raise ValueError('%s: the axis is %s, not %r' % (what, ', '.join('"%s"' % a for a in allowed if not a.startswith('+')), axis))
    return text


def uv_box(size=None):
    ''' The box projection: each triangle is projected along the axis its normal is mostly along, seen from outside, so a texture is not mirrored on the back faces.
        size: the millimetres one repeat of the texture covers, from one common origin, so that it goes on from one surface to the next in the world (a tiling texture);
        None: the texture fits each side once (the largest side of the model is 0 to 1) '''
    return UVMap('box', size=_size_of(size, 'uv_box'))


def uv_planar(axis='z', size=None):
    ''' One projection along an axis for the whole surface ("x", "y", "z", or "-z" for seen from below): a floor, a wall, a relief.  size as in uv_box (None: the projected
        box fits the texture once) '''
    return UVMap('planar', axis=_axis_of(axis, 'uv_planar', True), size=_size_of(size, 'uv_planar'))


def uv_cylinder(axis='z', turns=1, size=None):
    ''' u is the angle round an axis through the middle of the model's box (the texture goes `turns` times round), v the height along it: `size` is the millimetres of one
        repeat of v, None for once from the bottom to the top of the model.  On the axis itself the angle has no value: a cap on the axis is stretched '''
    if not isinstance(turns, (int, float)) or isinstance(turns, bool) or not turns > 0:
        raise ValueError('uv_cylinder: turns is a number above 0, not %r' % (turns,))
    return UVMap('cylinder', axis=_axis_of(axis, 'uv_cylinder'), turns=float(turns), size=_size_of(size, 'uv_cylinder'))


def uv_sphere(axis='z'):
    ''' u is the longitude and v the latitude (from the bottom pole to the top one) about the middle of the model's box: the equirectangular map a globe is drawn on '''
    return UVMap('sphere', axis=_axis_of(axis, 'uv_sphere'))


def uv_unwrap(angle=60, margin=4, size=1024):
    ''' The surface cut into islands, laid flat and packed into the square of the texture.

        angle   the most, in degrees, that a triangle of an island may be turned from the island's average direction (smaller: more, flatter islands and less stretching)
        margin  the gap between islands, in texels of a `size` x `size` texture: a texture with mip maps and a filter does not bleed one island into the next
        size    the size of the texture in texels that the margin is counted in

        Every island is at the same scale, so a texel is the same size everywhere on the model; the islands are cut where the surface turns by more than `angle`, and the
        triangles along a cut are made again for each side of it (a seam).  An island that is a disc is laid flat by the conformal map (angles are kept); the others by projection '''
    if not isinstance(angle, (int, float)) or isinstance(angle, bool) or not 1.0 <= angle <= 89.0:
        raise ValueError('uv_unwrap: angle is a number of degrees from 1 to 89, not %r' % (angle,))
    if not isinstance(margin, (int, float)) or isinstance(margin, bool) or margin < 0:
        raise ValueError('uv_unwrap: margin is a number of texels, 0 or more, not %r' % (margin,))
    if not isinstance(size, int) or isinstance(size, bool) or not 16 <= size <= 16384:
        raise ValueError('uv_unwrap: size is the texels of the texture across, from 16 to 16384, not %r' % (size,))
    return UVMap('unwrap', angle=float(angle), margin=float(margin), size=int(size))


def uv_armature(parts=None, margin=4, size=1024):
    ''' The surface laid on the texture from the armature it was made of, part by part (see uvparts.py).

            export_mesh(hero, "hero.glb", uvs="armature")
            export_mesh(hero, "hero.glb", uvs=uv_armature(margin=8, size=2048))

        parts   the armatures and stitching loops to unwrap by, or None for the parts of the model that is exported (a `character` knows them)
        margin  the gap between islands, in texels of a `size` x `size` texture
        size    the size of the texture in texels that the margin is counted in

        Each triangle belongs to the part whose surface it is nearest to.  An ARMATURE is unwrapped as a tube along its path: u round the path, v along it, the seam straight along its
        back, the rounded ends carried on.  STITCHING LOOPS are laid flat as they were drawn, in the picture of their view: u to the right, v up; what faces away from
        the viewer is an island of its own.  Every island is in millimetres, so a texel is the same size everywhere, and none is turned: the texture runs the way the part does '''
    if parts is not None and (not isinstance(parts, (list, tuple)) or not parts):
        raise ValueError('uv_armature: parts is a list of armatures and stitching loops, or None for the parts of the exported model, not %r' % (parts,))
    if not isinstance(margin, (int, float)) or isinstance(margin, bool) or margin < 0:
        raise ValueError('uv_armature: margin is a number of texels, 0 or more, not %r' % (margin,))
    if not isinstance(size, int) or isinstance(size, bool) or not 16 <= size <= 16384:
        raise ValueError('uv_armature: size is the texels of the texture across, from 16 to 16384, not %r' % (size,))
    return UVMap('armature', parts=None if parts is None else list(parts), margin=float(margin), size=int(size), axis=None)


def bind_parts(maps, part):
    """ The UV maps by armature that were not given parts get the parts (and the symmetry) of the model that is exported """
    from fieldev.stdlib import uvparts
    for m in maps:
        if m.kind == 'armature' and m.options.get('parts') is None:
            m.options['parts'] = uvparts.parts_of(part) or None
            m.options['axis'] = uvparts.symmetry_axis_of(part)
    return maps


def as_uv_maps(uvs):
    ''' The list of UV maps (one or two) for what export_mesh was given as `uvs`: a text ("box", "planar", "cylinder", "sphere", "unwrap", "armature"), ("box", 500), a UVMap, or a list of them '''
    if uvs is None or uvs is False:
        return []
    if isinstance(uvs, UVMap):
        return [uvs]
    if isinstance(uvs, (list, tuple)) and uvs and not (len(uvs) == 2 and isinstance(uvs[0], str) and isinstance(uvs[1], (int, float)) and not isinstance(uvs[1], bool)):
        if len(uvs) > 2:
            raise ValueError('export_mesh: uvs has at most two sets (the second is for a lightmap), not %d' % len(uvs))
        return [m for item in uvs for m in as_uv_maps(item)]
    if isinstance(uvs, (list, tuple)):
        name, size = uvs
        if str(name).strip().lower() != 'box':
            raise ValueError('export_mesh: uvs=(%r, %r) -- the one with a size is ("box", the millimetres of one repeat)' % (name, size))
        return [uv_box(size)]
    name = str(uvs).strip().lower()
    makers = {'box': uv_box, 'planar': uv_planar, 'cylinder': uv_cylinder, 'sphere': uv_sphere, 'unwrap': uv_unwrap, 'armature': uv_armature}
    if name not in makers:
        raise ValueError('export_mesh: uvs=%r -- the UV maps there are: %s' % (uvs, ', '.join(sorted(makers))))
    return [makers[name]()]


def apply_uv_maps(xyz, tri, maps):
    ''' The mesh with the vertices made again where the UV maps give a vertex more than one place: (xyz, tri, [the u, v of every vertex, one flat f array for each map]) '''
    sets = [m.corner_uvs(xyz, tri) for m in maps]
    out_xyz, out_tri = array('f'), array('I')
    out_sets = [array('f') for _ in sets]
    made = {}
    for k in range(len(tri)):
        key = (tri[k],) + tuple(int(round(s[2 * k] * 1e6)) for s in sets) + tuple(int(round(s[2 * k + 1] * 1e6)) for s in sets)
        j = made.get(key)
        if j is None:
            j = made[key] = len(out_xyz) // 3
            i = tri[k]
            out_xyz.extend((xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]))
            for s, o in zip(sets, out_sets):
                o.extend((s[2 * k], s[2 * k + 1]))
        out_tri.append(j)
    return out_xyz, out_tri, out_sets
