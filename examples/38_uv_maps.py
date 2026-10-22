# UV maps: how a surface is laid out on a texture.  export_mesh(..., uvs=...) gives every corner of every triangle a place (u, v) on the picture.
#
#   uvs="box"                    each triangle projected along the axis its normal is mostly along; ("box", 500) repeats the texture every 500 mm
#   uvs=uv_planar("z")           one projection for the whole surface (a floor, a wall); uv_cylinder("z"), uv_sphere() wrap round
#   uvs="unwrap"                 the surface cut into islands, laid flat at ONE scale and packed into the square: an atlas.  uv_unwrap(angle=45, margin=8)
#   uvs=[uv_unwrap(), uv_unwrap(margin=12)]       two sets: the second (TEXCOORD_1 in a glTF) is for a lightmap
#   uv_layout="layout.png"       a picture of the first map: the islands and the edges of the triangles, to look at
#
# The figure is drawn.  The script writes each map, reads the files back, and prints a line that starts with ok or FAIL for each check (in the output pane): that the
# places are inside the square, that no two islands overlap, that a texel is the same size everywhere, that the box repeat is what was asked, that the seam of a cylinder is
# where it should be.  The layout of the atlas is in meshes/figure_layout.png.
import json
import math
import struct
from fieldev import *
from fieldev.stdlib.pngfile import read_png

view.set_bounds((-70, -40, -12), (70, 40, 185))
view.set_resolution(1)
view.set_quality(8)

figure = symmetric_x(union_all([
    chain([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5]),
    chain([(0, 2, 163)], radii=11),
    chain([(18, 0, 138), (31, 0, 113), (37, 8, 92)], radii=[6, 4.5, 3.5]),
    chain([(9, 0, 88), (11, 0, 48), (11, 0, 9)], radii=[8, 5.5, 4]),
    chain([(11, 0, 9), (11, 14, 4)], radii=[4.5, 3]),
], blend=4))
figure

crate = box((100, 100, 0), (140, 130, 30))
crate

failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def read_obj(path):
    ''' (the places, the (u, v)s, the triangles as three (vertex, uv) pairs): an OBJ as export_mesh writes it '''
    v, vt, faces = [], [], []
    for line in open(path):
        w = line.split()
        if not w:
            continue
        if w[0] == "v":
            v.append(tuple(float(c) for c in w[1:4]))
        elif w[0] == "vt":
            vt.append((float(w[1]), float(w[2])))
        elif w[0] == "f":
            faces.append(tuple(tuple(int(i) - 1 for i in c.split("/")[:2]) for c in w[1:4]))
    return v, vt, faces


def area3(a, b, c):
    e1 = [b[i] - a[i] for i in range(3)]
    e2 = [c[i] - a[i] for i in range(3)]
    x = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
    return 0.5 * math.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)


def area2(a, b, c):
    return 0.5 * ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def covered_texels(vt, faces, n):
    ''' how many texels of an n x n picture the triangles cover (the centre of a texel inside a triangle), and the sum of the areas of the triangles in texels '''
    seen = set()
    total = 0.0
    for f in faces:
        p = [(vt[c[1]][0] * n, vt[c[1]][1] * n) for c in f]
        total += abs(area2(*p))
        x0, x1 = int(min(q[0] for q in p)), int(max(q[0] for q in p)) + 1
        y0, y1 = int(min(q[1] for q in p)), int(max(q[1] for q in p)) + 1
        d = (p[1][0] - p[0][0]) * (p[2][1] - p[0][1]) - (p[2][0] - p[0][0]) * (p[1][1] - p[0][1])
        if abs(d) < 1e-12:
            continue
        for y in range(y0, y1):
            for x in range(x0, x1):
                xc, yc = x + 0.5, y + 0.5
                b1 = ((xc - p[0][0]) * (p[2][1] - p[0][1]) - (p[2][0] - p[0][0]) * (yc - p[0][1])) / d
                b2 = ((p[1][0] - p[0][0]) * (yc - p[0][1]) - (xc - p[0][0]) * (p[1][1] - p[0][1])) / d
                if b1 >= 0 and b2 >= 0 and b1 + b2 <= 1:
                    seen.add((x, y))
    return len(seen), total


# 1. the unwrap: islands packed into the square
atlas = uv_unwrap(angle=45, margin=4, size=512)
export_mesh(figure, "meshes/figure_uv.obj", uvs=atlas, uv_layout="meshes/figure_layout.png")
v, vt, faces = read_obj("meshes/figure_uv.obj")
us, vs = [t[0] for t in vt], [t[1] for t in vt]
check("unwrap: every place is inside the square of the texture", min(us) >= 0 and max(us) <= 1 and min(vs) >= 0 and max(vs) <= 1, "u %.3f to %.3f, v %.3f to %.3f" % (min(us), max(us), min(vs), max(vs)))
report = atlas.report
check("unwrap: a few dozen islands at most, and a good part of the square used", report is not None and 6 <= report["islands"] <= 80 and report["coverage"] > 0.35,
      "%d islands (%d conformal), %.0f %% of the square, %.3f mm a texel (of 512), stretch %.2f to %.2f" % (
          report["islands"], report["conformal"], 100 * report["coverage"], report["mm_per_texel"], report["stretch"][0], report["stretch"][1]))
n_tex = 512
distinct, total = covered_texels(vt, faces, n_tex)
check("unwrap: no two islands overlap (the texels covered are the sum of the triangles)", abs(distinct - total) / total < 0.04, "%d texels covered, %.0f the triangles' own" % (distinct, total))
ratios = sorted(abs(area2(*[vt[c[1]] for c in f])) / max(area3(*[v[c[0]] for c in f]), 1e-12) for f in faces)
median = ratios[len(ratios) // 2]
good = sum(1 for r in ratios if 0.35 < r / median < 2.5) / len(ratios)
check("unwrap: a texel is the same size everywhere (90 % of the triangles within 0.35 to 2.5 of the median)", good > 0.9, "%.0f %% of %d triangles" % (100 * good, len(ratios)))
width, height, channels, pixels = read_png("meshes/figure_layout.png")
check("uv_layout: a picture of 1024 x 1024 with the islands in it", (width, height, channels) == (1024, 1024, 3) and len(set(pixels[i:i + 3] for i in range(0, len(pixels), 3 * 997))) >= 3,
      "%d x %d" % (width, height))

# 2. a finer angle: more, flatter islands
fine = uv_unwrap(angle=25, margin=4, size=512)
export_mesh(figure, "meshes/figure_uv_fine.obj", uvs=fine)
check("unwrap: a smaller angle cuts more islands", fine.report["islands"] > report["islands"], "%d against %d" % (fine.report["islands"], report["islands"]))

# 3. the box projection, world-scaled: the texture repeats every 40 mm, going on from one surface to the next
export_mesh(crate, "meshes/crate_box.obj", uvs=("box", 40))
v, vt, faces = read_obj("meshes/crate_box.obj")
tops = [f for f in faces if all(abs(v[c[0]][2] - 30) < 1e-4 for c in f)]
xs = [v[c[0]][0] for f in tops for c in f]
tu = [vt[c[1]][0] for f in tops for c in f]
check("box: the top of the crate (40 mm across) is one repeat of a 40 mm texture", abs((max(tu) - min(tu)) - (max(xs) - min(xs)) / 40.0) < 1e-4, "u spans %.3f for %.0f mm" % (max(tu) - min(tu), max(xs) - min(xs)))
export_mesh(crate, "meshes/crate_fit.obj", uvs="box")
v, vt, faces = read_obj("meshes/crate_fit.obj")
check("box: with no size the largest side of the model is 0 to 1", abs(max(t[0] for t in vt) - 1.0) < 1e-4 or abs(max(t[1] for t in vt) - 1.0) < 1e-4)

# 4. planar, cylinder and sphere
export_mesh(crate, "meshes/crate_planar.obj", uvs=uv_planar("z"))
v, vt, faces = read_obj("meshes/crate_planar.obj")
check("planar: along z the crate's x and y are u and v (0 to 1 over the largest side)", abs(max(t[0] for t in vt) - 1.0) < 1e-4 and 0 <= min(t[1] for t in vt) and max(t[1] for t in vt) <= 1.0001)
export_mesh(figure, "meshes/figure_cyl.obj", uvs=uv_cylinder("z"))
v, vt, faces = read_obj("meshes/figure_cyl.obj")
v_top = max(t[1] for t in vt)
check("cylinder: v goes up the height of the model, from 0 to 1", abs(min(t[1] for t in vt)) < 1e-4 and abs(v_top - 1.0) < 1e-4, "v from %.3f to %.3f" % (min(t[1] for t in vt), v_top))
bad = 0
for f in faces:
    p = [vt[c[1]][0] for c in f]
    if max(p) - min(p) > 0.5:
        bad += 1
check("cylinder: no triangle is stretched across the seam (u goes on past 1 instead) -- but for the few on the axis itself, where the angle has no value", bad <= 0.005 * len(faces),
      "%d of %d across" % (bad, len(faces)))
export_mesh(figure, "meshes/figure_sphere.obj", uvs=uv_sphere())
v, vt, faces = read_obj("meshes/figure_sphere.obj")
check("sphere: u is the longitude and v the latitude, both 0 to 1", 0 <= min(t[1] for t in vt) and max(t[1] for t in vt) <= 1.0001 and min(t[0] for t in vt) >= -1e-6)

# 5. two sets, in a glTF
export_mesh(figure, "meshes/figure_two.glb", uvs=[uv_unwrap(angle=45, size=512), uv_unwrap(angle=45, margin=12, size=512)])
data = open("meshes/figure_two.glb", "rb").read()
jsize = struct.unpack_from("<I", data, 12)[0]
doc = json.loads(data[20:20 + jsize].decode("utf-8"))
attributes = doc["meshes"][0]["primitives"][0]["attributes"]
check("two sets: TEXCOORD_0 and TEXCOORD_1 are in the glTF", "TEXCOORD_0" in attributes and "TEXCOORD_1" in attributes)

# 6. what is refused
for label, call in (("an STL has no texture coordinates", lambda: export_mesh(figure, "meshes/x.stl", uvs="unwrap")),
                    ("a UV map that is not there", lambda: export_mesh(figure, "meshes/x.obj", uvs="spherical")),
                    ("an angle of 0", lambda: uv_unwrap(angle=0)),
                    ("three sets", lambda: export_mesh(figure, "meshes/x.glb", uvs=["box", "unwrap", "sphere"])),
                    ("a second set in an OBJ", lambda: export_mesh(figure, "meshes/x.obj", uvs=["box", "unwrap"])),
                    ("a texture size of 0 mm", lambda: uv_box(0))):
    try:
        call()
        check(label + " is refused", False)
    except (ValueError, TypeError) as e:
        check(label + " is refused", True, str(e)[:70])

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")
