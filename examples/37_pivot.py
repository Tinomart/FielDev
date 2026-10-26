# Where the origin of a game asset is: export_mesh(..., pivot=...).
#
#   export_mesh(figure, "hero.glb", pivot="base")                    the middle of the bottom of the model is the origin: the character stands on the ground, at 0
#   export_mesh(figure, "hero.glb", pivot=(0, 0, 92))                or a place of your own (here the hips); the skeleton moves with it
#
# The script writes the files, reads them back with readers of its own and prints a line that starts with ok or FAIL for every check (in the output pane).
import json
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
bones = [joint("hips", (0, 0, 92)), joint("chest", (0, 0, 128), parent="hips"), joint("head", (0, 2, 163), parent="chest")]

failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def read_obj(path):
    verts, tris = [], []
    for line in open(path):
        w = line.split()
        if w and w[0] == "v":
            verts.append(tuple(float(t) for t in w[1:4]))
        elif w and w[0] == "f":
            tris.append(tuple(int(t.split("/")[0]) - 1 for t in w[1:4]))
    return verts, tris


def box_of(verts):
    lo = tuple(min(v[c] for v in verts) for c in range(3))
    hi = tuple(max(v[c] for v in verts) for c in range(3))
    return lo, hi, tuple((a + b) / 2 for a, b in zip(lo, hi))


def read_glb(path):
    data = open(path, "rb").read()
    jsize = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + jsize].decode("utf-8")), data[20 + jsize + 8:]


# 1. the origin
export_mesh(figure, "meshes/as_modelled.obj")
export_mesh(figure, "meshes/base.obj", pivot="base")
export_mesh(figure, "meshes/center.obj", pivot="center")
export_mesh(figure, "meshes/place.obj", pivot=(10, 0, 5))
(lo0, hi0, c0) = box_of(read_obj("meshes/as_modelled.obj")[0])
(lo1, hi1, c1) = box_of(read_obj("meshes/base.obj")[0])
(lo2, hi2, c2) = box_of(read_obj("meshes/center.obj")[0])
(lo3, hi3, c3) = box_of(read_obj("meshes/place.obj")[0])
check("pivot='base': the feet are at z = 0, the middle of the model is at x = 0, y = 0, and nothing else changed", abs(lo1[2]) < 1e-4 and abs(c1[0]) < 1e-3 and abs(c1[1]) < 1e-3
      and all(abs((h1 - l1) - (h0 - l0)) < 1e-3 for l1, h1, l0, h0 in zip(lo1, hi1, lo0, hi0)), "z %.2f .. %.2f (was %.2f .. %.2f)" % (lo1[2], hi1[2], lo0[2], hi0[2]))
check("pivot='center': the middle of the box is the origin", all(abs(c) < 1e-3 for c in c2), "box from (%.1f, %.1f, %.1f)" % lo2)
check("pivot=(10, 0, 5): the model moved by (-10, 0, -5)", all(abs(a - (b - s)) < 1e-3 for a, b, s in zip(lo3, lo0, (10, 0, 5))) and all(abs(a - (b - s)) < 1e-3 for a, b, s in zip(hi3, hi0, (10, 0, 5))))

# 2. the skeleton moves with the pivot: the inverse bind matrix of the hips is the translation back from where they are now
export_mesh(figure, "meshes/rigged_base.glb", skeleton=bones, pivot="base")
doc, binary = read_glb("meshes/rigged_base.glb")
skin = doc["skins"][0]
view_ = doc["bufferViews"][doc["accessors"][skin["inverseBindMatrices"]]["bufferView"]]
matrices = struct.unpack_from("<%df" % (16 * len(bones)), binary, view_["byteOffset"])
hips = matrices[0:16]
# (the hips were at (0, 0, 92); the base of the model is the middle of its bottom: x, y of its box, z of its lowest point.  In the file: metres, Y up)
base_shift = ((lo0[0] + hi0[0]) / 2, (lo0[1] + hi0[1]) / 2, lo0[2])
here = ((0 - base_shift[0]) * 0.001, (92 - base_shift[2]) * 0.001, -(0 - base_shift[1]) * 0.001)
check("pivot with a skeleton: the hips are where the pivot puts them (the inverse bind matrix and the node)", all(abs(hips[12 + c] + here[c]) < 2e-6 for c in range(3))
      and all(abs(a - b) < 2e-6 for a, b in zip(doc["nodes"][skin["joints"][0]]["translation"], here)))

# 3. what is refused
for label, call in (("a pivot of 'top'", lambda: export_mesh(figure, "meshes/x.obj", pivot="top")),
                    ("a pivot of two numbers", lambda: export_mesh(figure, "meshes/x.obj", pivot=(1, 2)))):
    try:
        call()
        check(label + " is refused", False)
    except (ValueError, TypeError) as e:
        check(label + " is refused", True, str(e)[:70])

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")
