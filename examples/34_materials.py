# Materials and vertex colours from fields, for a game engine: material(...) says what a surface is made of and WHERE (a body or a field), export_mesh writes them.
#
#   skin = material("skin", color=(0.93, 0.74, 0.62), roughness=0.7)                    the base: everywhere
#   shirt = material("shirt", color="#3a6ea5", where=box((-45, -30, 100), (45, 30, 150)))   on what is inside the box
#   export_mesh(figure, "hero.glb", materials=[skin, shirt], colors=(r_field, g_field, b_field))
#   with_materials(figure, [skin, shirt])                                               the figure in the viewport in their colours (and what export_mesh writes without materials=)
#
# The materials are LAYERS: each triangle takes the last material that covers the middle of it, so the base goes first.  A .glb or .gltf gets a material
# and a primitive of the mesh for each; an .obj gets a .mtl file; vertex colours are in OBJ, PLY and glTF.  The script writes the files, reads them back with
# readers of its own and prints a line that starts with ok or FAIL for every check (in the output pane).
import json
import os
import struct
from fieldev import *

view.set_bounds((-70, -40, -12), (70, 40, 185))
view.set_resolution(1)
view.set_quality(8)

# A figure of round cones (see example 33): spine, head, one arm, leg and foot, and the other half by a mirror
figure = symmetric_x(union_all([
    chain([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5]),
    chain([(0, 2, 163)], radii=11),
    chain([(18, 0, 138), (31, 0, 113), (37, 8, 92)], radii=[6, 4.5, 3.5]),
    chain([(9, 0, 88), (11, 0, 48), (11, 0, 9)], radii=[8, 5.5, 4]),
    chain([(11, 0, 9), (11, 14, 4)], radii=[4.5, 3]),
], blend=4))

shirt_box = ((-45, -30, 100), (45, 30, 150))
trousers_box = ((-26, -30, 12), (26, 30, 100))
shoes_box = ((-45, -30, -10), (45, 30, 14))
skin = material("skin", color=(0.93, 0.74, 0.62), roughness=0.7)
shirt = material("shirt", color="#3a6ea5", roughness=0.9, where=box(*shirt_box))
trousers = material("trousers", color="#2b2b33", roughness=0.8, where=box(*trousers_box))
shoes = material("shoes", color="#5a3a22", roughness=0.5, where=box(*shoes_box))
layers = [skin, shirt, trousers, shoes]
# The viewport shows the figure in the colours of its materials, with a key of their names at the right; the file gets the same materials without being told twice
shown = with_materials(figure, layers)
shown
# vertex colours: a gradient with the height (a field is evaluated at every vertex)
tint = (0.2 + z_field() / 250, 0.5, 0.9 - z_field() / 250)

failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def inside(box_, p):
    (x0, y0, z0), (x1, y1, z1) = box_
    return x0 < p[0] < x1 and y0 < p[1] < y1 and z0 < p[2] < z1


def read_obj(path):
    ''' vertices (with their colours, if there are), triangles of each material (None: no material), the .mtl file named '''
    verts, colours, groups, mtl, current = [], [], {}, None, None
    for line in open(path):
        w = line.split()
        if not w:
            continue
        if w[0] == "v":
            verts.append(tuple(float(t) for t in w[1:4]))
            if len(w) >= 7:
                colours.append(tuple(float(t) for t in w[4:7]))
        elif w[0] == "mtllib":
            mtl = w[1]
        elif w[0] == "usemtl":
            current = w[1]
        elif w[0] == "f":
            groups.setdefault(current, []).append(tuple(int(t.split("/")[0]) - 1 for t in w[1:4]))
    return verts, colours, groups, mtl


def centre(verts, t):
    return tuple(sum(verts[i][c] for i in t) / 3.0 for c in range(3))


# 1. an OBJ with materials, and its .mtl
export_mesh(figure, "meshes/hero.obj", materials=layers)
verts, _, groups, mtl = read_obj("meshes/hero.obj")
total = sum(len(g) for g in groups.values())
check("obj: a .mtl file beside it, four materials used", mtl == "hero.mtl" and os.path.exists("meshes/hero.mtl") and set(groups) == {"skin", "shirt", "trousers", "shoes"},
      "%d triangles: %s" % (total, ", ".join("%s %d" % (k, len(g)) for k, g in sorted(groups.items(), key=lambda kv: str(kv[0])))))
text = open("meshes/hero.mtl").read()
kd = [float(t) for t in text.split("newmtl shirt")[1].split("Kd")[1].split("\n")[0].split()]
check("mtl: a newmtl for each, the colour of the shirt is #3a6ea5", all(("newmtl " + m.name) in text for m in layers) and all(abs(a - b / 255.0) < 1e-6 for a, b in zip(kd, (0x3a, 0x6e, 0xa5))),
      "Kd %s" % kd)
check("obj: the shoes are the triangles whose middle is in the shoes box", all(inside(shoes_box, centre(verts, t)) for t in groups["shoes"]))
check("obj: the shirt is where the shirt box is and the shoes do not cover it", all(inside(shirt_box, centre(verts, t)) and not inside(shoes_box, centre(verts, t)) for t in groups["shirt"]))
check("obj: the trousers are in their box and under the shoes layer", all(inside(trousers_box, centre(verts, t)) and not inside(shoes_box, centre(verts, t)) for t in groups["trousers"]))
check("obj: the skin is what none of the other boxes covers", not any(inside(b, centre(verts, t)) for t in groups["skin"] for b in (shirt_box, trousers_box, shoes_box)))
check("obj: an arm, a head and a foot are there to see: all four are more than a few triangles", all(len(g) > 100 for g in groups.values()))

# 2. a GLB with the same materials and the vertex colours
export_mesh(figure, "meshes/hero.glb", materials=layers, colors=tint)
data = open("meshes/hero.glb", "rb").read()
magic, version, length = struct.unpack_from("<4sII", data, 0)
jsize = struct.unpack_from("<I", data, 12)[0]
doc = json.loads(data[20:20 + jsize].decode("utf-8"))
prims = doc["meshes"][0]["primitives"]
nverts = doc["accessors"][0]["count"]
shirt_gltf = next(m for m in doc["materials"] if m["name"] == "shirt")["pbrMetallicRoughness"]
check("glb: four materials, a primitive for each, vertex colours", magic == b"glTF" and len(doc["materials"]) == 4 and len(prims) == 4 and all("COLOR_0" in p["attributes"] for p in prims)
      and doc["accessors"][prims[0]["attributes"]["COLOR_0"]]["count"] == nverts, "%d vertices" % nverts)
check("glb: the same triangles as the obj, the shirt's colour and its roughness", sum(doc["accessors"][p["indices"]]["count"] for p in prims) == 3 * total
      and abs(shirt_gltf["baseColorFactor"][2] - 0.647) < 1e-3 and shirt_gltf["roughnessFactor"] == 0.9 and length == len(data))

# 2b. a model shown with its materials carries them: no materials= is needed
export_mesh(shown, "meshes/hero_shown.glb")
data = open("meshes/hero_shown.glb", "rb").read()
doc_shown = json.loads(data[20:20 + struct.unpack_from("<I", data, 12)[0]].decode("utf-8"))
check("glb: a model shown with with_materials writes its materials without materials=", [m["name"] for m in doc_shown["materials"]] == [m.name for m in layers]
      and len(doc_shown["meshes"][0]["primitives"]) == 4 and sum(doc_shown["accessors"][p["indices"]]["count"] for p in doc_shown["meshes"][0]["primitives"]) == 3 * total)
# (and an STL, which has no materials, is not refused for them)
export_mesh(shown, "meshes/hero_shown.stl")
check("stl: a model shown with its materials is written as any other", os.path.getsize("meshes/hero_shown.stl") > 1000)

# 3. a PLY with vertex colours only
export_mesh(figure, "meshes/hero.ply", colors=tint)
data = open("meshes/hero.ply", "rb").read()
header, _, rest = data.partition(b"end_header\n")
lines = header.decode("ascii").split("\n")
count = int(next(l for l in lines if l.startswith("element vertex")).split()[2])
# (the vertex is what the header says -- x, y, z, the normal, the colours -- read by the names of the properties)
props = [l.split() for l in lines if l.startswith("property") and "list" not in l]
fmt = "<" + "".join({"float": "f", "uchar": "B"}[p[1]] for p in props)
names = [p[2] for p in props]
first = []
for i in range(0, count, max(1, count // 25)):
    row = dict(zip(names, struct.unpack_from(fmt, rest, struct.calcsize(fmt) * i)))
    first.append((row["x"], row["y"], row["z"], row["red"], row["green"], row["blue"]))
ok = all(abs(r - round((0.2 + z / 250) * 255)) <= 1 and g == 128 and abs(b - round((0.9 - z / 250) * 255)) <= 1 for x, y, z, r, g, b in first if 0 <= z <= 180)
check("ply: red, green, blue of every vertex, and they follow the height", "property uchar red" in lines and count == nverts and ok, "%d vertices" % count)

# 4. what is refused, and what is not a material
for label, call in (("an STL has no materials", lambda: export_mesh(figure, "meshes/hero.stl", materials=layers)),
                    ("an FBX has no vertex colours", lambda: export_mesh(figure, "meshes/hero.fbx", colors=tint)),
                    ("two materials with one name", lambda: export_mesh(figure, "meshes/hero2.obj", materials=[skin, skin])),
                    ("a roughness of 2", lambda: material("x", roughness=2)),
                    ("a colour that is no colour", lambda: material("x", color="blue")),
                    ("with_materials of names that are no materials", lambda: with_materials(figure, ["skin"]))):
    try:
        call()
        check(label + " is refused", False)
    except (ValueError, TypeError) as e:
        check(label + " is refused", True, str(e)[:70])

# 5. the OBJ with materials and colours is read back by import_model
export_mesh(figure, "meshes/hero_colors.obj", materials=layers, colors=tint)
back, (blo, bhi) = import_model("meshes/hero_colors.obj", file_units="mm")[0]
check("import_model reads the obj with colours and materials back", bhi[2] - blo[2] > 150, "%.0f mm tall" % (bhi[2] - blo[2]))

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")
