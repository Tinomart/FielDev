# Exporting for a game engine: the unit and the up axis of the file, a budget of triangles, and a mesh that is symmetric to the last bit.
#
#   export_mesh(part, "hero.obj", units="m", up="y")     metres, Y up
#   export_mesh(part, "hero.obj", max_triangles=2000)    the finest mesh of at most 2000 triangles
#   export_mesh(part, "hero.obj", symmetric="x")         the x >= 0 half, cut exactly at x = 0, and its mirror image
#
# The script writes the files, reads them back with a reader of its own and prints what it finds in the output pane: every line starts with ok or FAIL.
import os
import struct
from fieldes import *

view.set_bounds((-45, -30, -30), (45, 30, 30))
view.set_resolution(1)       # (the meshes the script exports are made at the scene's resolution: a cell of a millimetre)
view.set_quality(8)

# A body that is NOT symmetric: a ball with a second, smaller ball on its +x side.  symmetric="x" keeps the +x half, so the small ball appears on both sides.
part = union(sphere(20, (0, 0, 0)), sphere(9, (24, 4, 3)))


def read_obj(path):
    verts, tris = [], []
    for line in open(path):
        w = line.split()
        if w and w[0] == "v":
            verts.append(tuple(float(t) for t in w[1:4]))
        elif w and w[0] == "f":
            idx = [int(t.split("/")[0]) - 1 for t in w[1:]]
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
    return verts, tris


def study(verts, tris):
    ''' bounds, volume (positive: the triangles face outwards) and whether the surface is closed: every edge in two triangles, one each way '''
    weld = {}
    ids = [weld.setdefault(v, len(weld)) for v in verts]
    edges = {}
    for a, b, c in tris:
        for p, q in ((a, b), (b, c), (c, a)):
            e = (ids[p], ids[q])
            edges[e] = edges.get(e, 0) + 1
    closed = all(n == 1 and edges.get((q, p)) == 1 for (p, q), n in edges.items())
    vol = 0.0
    for a, b, c in tris:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = verts[a], verts[b], verts[c]
        vol += (ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)) / 6.0
    lo = tuple(min(v[i] for v in verts) for i in range(3))
    hi = tuple(max(v[i] for v in verts) for i in range(3))
    return lo, hi, vol, closed


def near(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def mirrored(verts, axis, plane, tol=1e-3):
    ''' every vertex has its mirror image across the plane among the vertices '''
    key = lambda v: tuple(round(c / tol) for c in v)
    have = set(key(v) for v in verts)
    for v in verts:
        w = list(v)
        w[axis] = 2 * plane - w[axis]
        k = list(key(w))
        found = False
        for step in (-1, 0, 1):          # (the mirror image is only as exact as a float32 is: it may fall in the next cell of the grid)
            k[axis] += step
            found = found or tuple(k) in have
            k[axis] -= step
        if not found:
            return False
    return True


failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


# 1. as modelled: millimetres, Z up
export_mesh(part, "meshes/hero_mm.obj")
v0, t0 = read_obj("meshes/hero_mm.obj")
lo0, hi0, vol0, closed0 = study(v0, t0)
check("millimetres, Z up: a closed surface that faces outwards", closed0 and vol0 > 0, "%d triangles, %.0f mm3, x %.1f .. %.1f" % (len(t0), vol0, lo0[0], hi0[0]))

# 2. centimetres
export_mesh(part, "meshes/hero_cm.obj", units="cm")
lo, hi, vol, closed = study(*read_obj("meshes/hero_cm.obj"))
check("units='cm': a tenth of the numbers", near([c * 10 for c in lo + hi], lo0 + hi0, 1e-3) and abs(vol * 1000 / vol0 - 1) < 1e-4, "x %.2f .. %.2f cm" % (lo[0], hi[0]))
check("units='cm': the file says so", "centimetres" in open("meshes/hero_cm.obj").readline())

# 3. Y up: (x, y, z) becomes (x, z, -y), a turn about X, so the volume and the sides of the triangles stay
export_mesh(part, "meshes/hero_y.obj", up="y")
lo, hi, vol, closed = study(*read_obj("meshes/hero_y.obj"))
check("up='y': the old z is y, the old -y is z", near((lo[0], lo[1], lo[2], hi[0], hi[1], hi[2]), (lo0[0], lo0[2], -hi0[1], hi0[0], hi0[2], -lo0[1]), 1e-3) and closed and abs(vol / vol0 - 1) < 1e-4,
      "y %.1f .. %.1f, z %.1f .. %.1f" % (lo[1], hi[1], lo[2], hi[2]))

# 4. a format that states its own unit and axes does not take them
for path, args in (("meshes/a.3mf", dict(units="cm")), ("meshes/a.glb", dict(up="z"))):
    try:
        export_mesh(part, path, **args)
        check(path + " with " + str(args) + " is refused", False)
    except ValueError as e:
        check(path + " with " + str(args) + " is refused", True, str(e)[:70])

# 5. a budget of triangles
budget = len(t0) // 3
export_mesh(part, "meshes/hero_budget.obj", max_triangles=budget)
lo, hi, vol, closed = study(*read_obj("meshes/hero_budget.obj"))
count = len(read_obj("meshes/hero_budget.obj")[1])
check("max_triangles=%d: within it, and not far under" % budget, count <= budget and count >= 0.5 * budget and closed, "%d triangles (it was %d), volume %.0f mm3" % (count, len(t0), vol))

# 6. symmetric across x = 0
export_mesh(part, "meshes/hero_sym.obj", symmetric="x")
vs, ts = read_obj("meshes/hero_sym.obj")
lo, hi, vol, closed = study(vs, ts)
check("symmetric='x': closed, facing outwards", closed and vol > 0, "%d triangles, %.0f mm3 (was %.0f)" % (len(ts), vol, vol0))
check("symmetric='x': every vertex has its mirror image, and the x range is symmetric", mirrored(vs, 0, 0.0, 1e-5) and abs(lo[0] + hi[0]) < 1e-4, "x %.3f .. %.3f" % (lo[0], hi[0]))
check("symmetric='x': the +x half is the one that was modelled (the small ball is on both sides)", abs(hi[0] - hi0[0]) < 1.0 and vol > vol0, "x max %.1f (was %.1f)" % (hi[0], hi0[0]))

# 7. the other side, and a plane that is not through the origin
export_mesh(part, "meshes/hero_neg.obj", symmetric="-x")
lo, hi, vol, closed = study(*read_obj("meshes/hero_neg.obj"))
check("symmetric='-x': the -x half is the one kept: no small ball", closed and abs(hi[0] - 20) < 1.0 and vol < vol0, "x %.1f .. %.1f, %.0f mm3" % (lo[0], hi[0], vol))
export_mesh(part, "meshes/hero_y4.obj", symmetric=("y", 4))
vy, ty = read_obj("meshes/hero_y4.obj")
lo, hi, vol, closed = study(vy, ty)
check("symmetric=('y', 4): across the plane y = 4", closed and mirrored(vy, 1, 4.0, 1e-3), "y %.2f .. %.2f" % (lo[1], hi[1]))

# 8. all of it together, and a binary STL in metres with Y up
export_mesh(part, "meshes/hero_all.stl", units="m", up="y", max_triangles=budget // 2, symmetric="x")
data = open("meshes/hero_all.stl", "rb").read()
n = struct.unpack_from("<I", data, 80)[0]
pts = []
for k in range(n):
    f = struct.unpack_from("<12f", data, 84 + 50 * k)
    pts += [f[3:6], f[6:9], f[9:12]]
ys = [p[1] for p in pts]
check("all together (STL, m, Y up, symmetric, budget %d)" % (budget // 2), n <= budget // 2 and len(data) == 84 + 50 * n and abs(min(p[0] for p in pts) + max(p[0] for p in pts)) < 1e-6 and abs(max(ys) - hi0[2] / 1000) < 3e-3,
      "%d triangles, height %.3f m" % (n, max(ys) - min(ys)))

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")

# The symmetric mesh, read back: the small ball on both sides
sym, _ = import_model("meshes/hero_sym.obj", file_units="mm")[0]
sym
