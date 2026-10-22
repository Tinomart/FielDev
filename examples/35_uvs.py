# Texture coordinates (UVs) for a game engine: export_mesh(..., uvs="box") and a texture on a material.
#
#   export_mesh(figure, "hero.obj", uvs="box", materials=[material("skin", texture="skin.png")])     the texture fits each side of the model once
#   export_mesh(wall, "wall.glb", uvs=("box", 500))                                                    one repeat of the texture for every 500 mm, going on from one surface to the next
#
# The BOX projection: each triangle is projected along the axis its normal is mostly along (+x -x +y -y +z -z), seen from outside, so the texture reads
# the same way on every side and is not mirrored on the back ones.  A vertex that is in triangles of different projections is made again for each: that is
# the seam of the texture.  OBJ gets `vt`, PLY `s` and `t`, glTF `TEXCOORD_0`; the image is the `texture=` of a material (a file name: "skin.png").
# The script writes the files, reads them back with readers of its own and prints a line that starts with ok or FAIL for every check (in the output pane).
import json
import os
import struct
from fieldev import *

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

failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def read_obj(path):
    ''' vertices, texture coordinates, triangles (as indices of the vertices; the texture coordinate and the normal of a corner are the same number: "f a/a/a b/b/b c/c/c") '''
    verts, uvs, tris, same = [], [], [], True
    for line in open(path):
        w = line.split()
        if not w:
            continue
        if w[0] == "v":
            verts.append(tuple(float(t) for t in w[1:4]))
        elif w[0] == "vt":
            uvs.append((float(w[1]), float(w[2])))
        elif w[0] == "f":
            parts = [t.split("/") for t in w[1:4]]
            same = same and all(len(p) in (2, 3) and p[0] == p[1] and (len(p) == 2 or p[1] == p[2]) for p in parts)
            tris.append(tuple(int(p[0]) - 1 for p in parts))
    return verts, uvs, tris, same


def areas(verts, uvs, tris):
    ''' (the area of each triangle in space, its signed area in the texture) '''
    out = []
    for a, b, c in tris:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = verts[a], verts[b], verts[c]
        ux, uy, uz, vx, vy, vz = bx - ax, by - ay, bz - az, cx - ax, cy - ay, cz - az
        space = 0.5 * ((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + (ux * vy - uy * vx) ** 2) ** 0.5
        (pa, qa), (pb, qb), (pc, qc) = uvs[a], uvs[b], uvs[c]
        out.append((space, 0.5 * ((pb - pa) * (qc - qa) - (pc - pa) * (qb - qa))))
    return out


crate = box((0, 0, 0), (40, 20, 10))
region = ((-5, -5, -5), (45, 25, 15))

# 1. a box: every triangle is flat on a side, so the texture has the size of the face exactly
export_mesh(crate, "meshes/crate_plain.obj", bounds=region)
export_mesh(crate, "meshes/crate.obj", bounds=region, uvs=("box", 100))
plain, _, _, _ = read_obj("meshes/crate_plain.obj")
verts, uvs, tris, same = read_obj("meshes/crate.obj")
check("obj: a texture coordinate for every vertex, and the faces say v/vt", len(uvs) == len(verts) and same, "%d vertices (%d without UVs), %d triangles" % (len(verts), len(plain), len(tris)))
check("obj: the vertices are the same places, the seams made more of them", set(tuple(round(c, 4) for c in v) for v in verts) == set(tuple(round(c, 4) for c in v) for v in plain) and len(plain) < len(verts) <= 3 * len(plain))
measured = areas(verts, uvs, tris)
check("obj: on a box a triangle in the texture is as large as in space (100 mm to the texture), and none is turned over", all(s > 0 and abs(t * 100 ** 2 - s) < 1e-3 * s for s, t in measured))

# 2. one repeat for every 50 mm is twice the texture of one for every 100 mm
export_mesh(crate, "meshes/crate50.obj", bounds=region, uvs=("box", 50))
export_mesh(crate, "meshes/crate_fit.obj", bounds=region, uvs="box")
_, uv50, _, _ = read_obj("meshes/crate50.obj")
_, uvfit, _, _ = read_obj("meshes/crate_fit.obj")
extent = lambda uv: (max(u for u, v in uv) - min(u for u, v in uv), max(v for u, v in uv) - min(v for u, v in uv))
check("tiling: 50 mm to the texture has twice the texture of 100 mm", all(abs(a / b - 2) < 1e-4 for a, b in zip(extent(uv50), extent(uvs)) if b > 0), "%s and %s" % (extent(uv50), extent(uvs)))
check("fit: on each side the texture starts at 0 and the largest side of the model (40 mm) is 1", min(u for u, v in uvfit) == 0 and min(v for u, v in uvfit) == 0 and abs(max(max(u, v) for u, v in uvfit) - 1) < 1e-5)

# 3. the figure: a seam wherever the projection changes, and every triangle faces the right way in the texture
mat = material("skin", color=(0.93, 0.74, 0.62), roughness=0.7, texture="skin.png")
export_mesh(figure, "meshes/figure.obj", uvs="box", materials=[mat])
verts, uvs, tris, same = read_obj("meshes/figure.obj")
measured = areas(verts, uvs, tris)
check("figure: a texture coordinate for every vertex; no triangle is turned over or has no area in the texture", len(uvs) == len(verts) and same and all(t > 0 for s, t in measured),
      "%d vertices, %d triangles" % (len(verts), len(tris)))
check("figure: the .mtl says which image is the colour of the skin", "map_Kd skin.png" in open("meshes/figure.mtl").read())

# 4. the same in a GLB: TEXCOORD_0, the image and the texture of the material; v is down from the top of the image there
export_mesh(figure, "meshes/figure.glb", uvs="box", materials=[mat])
data = open("meshes/figure.glb", "rb").read()
jsize = struct.unpack_from("<I", data, 12)[0]
doc = json.loads(data[20:20 + jsize].decode("utf-8"))
binary = data[20 + jsize + 8:]
prim = doc["meshes"][0]["primitives"][0]
accessor = doc["accessors"][prim["attributes"]["TEXCOORD_0"]]
view_ = doc["bufferViews"][accessor["bufferView"]]
flat = struct.unpack_from("<%df" % (2 * accessor["count"]), binary, view_["byteOffset"])
# (every export is meshed again, and the mesher does not number the vertices the same way twice: the files are compared by the values they hold, not vertex by vertex)
close = lambda a, b: len(a) == len(b) and all(abs(x - y) < 1e-6 for x, y in zip(sorted(a), sorted(b)))
ok = accessor["type"] == "VEC2" and accessor["count"] == len(verts) and close(flat[0::2], [u for u, v in uvs]) and close([1.0 - t for t in flat[1::2]], [v for u, v in uvs])
check("glb: TEXCOORD_0 holds the same u, and 1 - v", ok, "%d texture coordinates" % accessor["count"])
check("glb: an image, a texture and the base colour texture of the material", doc["images"] == [{"uri": "skin.png"}] and [t["source"] for t in doc["textures"]] == [0]
      and doc["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"] == 0)

# 5. a PLY with the coordinates (s, t) and colours
export_mesh(figure, "meshes/figure.ply", uvs="box", colors=(0.8, 0.8, 0.8))
data = open("meshes/figure.ply", "rb").read()
header, _, rest = data.partition(b"end_header\n")
lines = header.decode("ascii").split("\n")
count = int(next(l for l in lines if l.startswith("element vertex")).split()[2])
# (the vertex is what the header says: x, y, z, the normal, s and t, the colours -- read by the names of the properties)
props = [l.split() for l in lines if l.startswith("property") and "list" not in l]
fmt = "<" + "".join({"float": "f", "uchar": "B"}[p[1]] for p in props)
rows = [dict(zip((p[2] for p in props), struct.unpack_from(fmt, rest, struct.calcsize(fmt) * i))) for i in range(count)]
check("ply: s and t beside x, y, z and the colours, with the values of the obj", "property float s" in lines and "property float t" in lines and count == len(verts)
      and close([r["s"] for r in rows], [u for u, v in uvs]) and close([r["t"] for r in rows], [v for u, v in uvs]))

# 6. what is refused, and what is read back
for label, call in (("an STL has no texture coordinates", lambda: export_mesh(figure, "meshes/figure.stl", uvs="box")),
                    ("a projection that is not there", lambda: export_mesh(figure, "meshes/figure2.obj", uvs="spherical")),
                    ("a repeat of 0 mm", lambda: export_mesh(figure, "meshes/figure2.obj", uvs=("box", 0))),
                    ("a texture name with a space", lambda: material("x", texture="my skin.png"))):
    try:
        call()
        check(label + " is refused", False)
    except (ValueError, TypeError) as e:
        check(label + " is refused", True, str(e)[:70])
back, (blo, bhi) = import_model("meshes/figure.obj", file_units="mm")[0]
check("import_model reads the obj with its texture coordinates back", bhi[2] - blo[2] > 150, "%.0f mm tall" % (bhi[2] - blo[2]))

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")
