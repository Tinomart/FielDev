# A skeleton and the weights of a skin for a game engine: joint(...) and export_mesh(..., skeleton=[...]).
#
#   hips = joint("hips", (0, 0, 92))
#   spine = joint("spine", (0, 0, 106), parent="hips")
#   bones = mirror_joints([hips, spine, ..., joint("shoulder.R", point, parent="chest"), ...])      every ".R" joint gets a ".L" one across x = 0
#   export_mesh(figure, "hero.glb", skeleton=bones)
#
# The GLB has the joints as nodes (each a translation from its parent), the skin with its inverse bind matrices, and for every vertex the four joints that move
# it and how much (JOINTS_0, WEIGHTS_0).  The weights are made from the distance of the vertex to the bones -- the bone of a joint is the segments from it to its
# children, so the geometry between the elbow and the hand follows the elbow, and a joint at the end of the body (the hand, the head, the toe) has a bone to its
# tip -- a vertex follows the nearest bone alone, and shares itself with a bone that is about as near: `skin_falloff` is the width of that blend.
# The script writes the file, reads it back with a reader of its own, and prints a line that starts with ok or FAIL for every check (in the output pane).
# The bones are drawn over the figure.
import json
import os
import struct
from fieldes import *

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

# The joints of one side (".R"); mirror_joints makes the other (".L").  The head says where its bone ends; the hand and the toe go on as the bone before them does
bones = mirror_joints([
    joint("hips", (0, 0, 92)),
    joint("spine", (0, 0, 106), parent="hips"),
    joint("chest", (0, 0, 128), parent="spine"),
    joint("neck", (0, 0, 147), parent="chest"),
    joint("head", (0, 2, 163), parent="neck", tip=(0, 2, 175)),
    joint("shoulder.R", (18, 0, 138), parent="chest"),
    joint("elbow.R", (31, 0, 113), parent="shoulder.R"),
    joint("hand.R", (37, 8, 92), parent="elbow.R"),
    joint("hip.R", (9, 0, 88), parent="hips"),
    joint("knee.R", (11, 0, 48), parent="hip.R"),
    joint("ankle.R", (11, 0, 9), parent="knee.R"),
    joint("toe.R", (11, 14, 4), parent="ankle.R"),
])
names = [j.name for j in bones]

# the bones, drawn: a line from every joint to its parent
for j in bones:
    parent = next((p for p in bones if p.name == j.parent), None)
    if parent is not None:
        polyline([parent.position, j.position])

failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


SIZES = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    data = open(path, "rb").read()
    jsize = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + jsize].decode("utf-8")), data[20 + jsize + 8:]


def accessor(doc, binary, index):
    ''' the values of an accessor, as tuples of its type '''
    a = doc["accessors"][index]
    v = doc["bufferViews"][a["bufferView"]]
    code, size = SIZES[a["componentType"]]
    n = COUNTS[a["type"]]
    flat = struct.unpack_from("<%d%s" % (a["count"] * n, code), binary, v.get("byteOffset", 0) + a.get("byteOffset", 0))
    return [flat[i * n:(i + 1) * n] for i in range(a["count"])]


# 1. the GLB
export_mesh(figure, "meshes/hero.glb", skeleton=bones)
doc, binary = read_glb("meshes/hero.glb")
skin = doc["skins"][0]
prim = doc["meshes"][0]["primitives"][0]
nverts = doc["accessors"][prim["attributes"]["POSITION"]]["count"]
check("skin: %d joints as nodes, the skin lists them all, and the mesh node uses the skin" % len(bones),
      len(skin["joints"]) == len(bones) and [doc["nodes"][k]["name"] for k in skin["joints"]] == names and doc["nodes"][0].get("skin") == 0 and doc["nodes"][0]["mesh"] == 0)
by_name = {doc["nodes"][k]["name"]: doc["nodes"][k] for k in skin["joints"]}
check("hierarchy: the elbow holds the hand, the root is a root of the scene", [doc["nodes"][c]["name"] for c in by_name["elbow.R"]["children"]] == ["hand.R"]
      and doc["nodes"][skin["skeleton"]]["name"] == "hips" and skin["skeleton"] in doc["scenes"][0]["nodes"] and "elbow.R" not in doc["scenes"][0]["nodes"])
# (glTF has metres and Y up: x, z, -y of the millimetres)
shoulder, elbow = (18, 0, 138), (31, 0, 113)
t = by_name["elbow.R"]["translation"]
check("hierarchy: the elbow is where it is from the shoulder (a translation, in metres, Y up)",
      all(abs(a - b) < 1e-7 for a, b in zip(t, ((elbow[0] - shoulder[0]) * 0.001, (elbow[2] - shoulder[2]) * 0.001, -(elbow[1] - shoulder[1]) * 0.001))))
ibm = accessor(doc, binary, skin["inverseBindMatrices"])
hand = by_name["hand.R"]
hand_index = skin["joints"].index(doc["nodes"].index(hand))
check("inverse bind matrices: the matrix of the hand moves it back from where it is", len(ibm) == len(bones) and abs(ibm[hand_index][12] + 37 * 0.001) < 1e-7 and abs(ibm[hand_index][13] + 92 * 0.001) < 1e-7
      and abs(ibm[hand_index][14] - 8 * 0.001) < 1e-7 and ibm[hand_index][15] == 1.0)

# 2. the weights of every vertex
joints = accessor(doc, binary, prim["attributes"]["JOINTS_0"])
weights = accessor(doc, binary, prim["attributes"]["WEIGHTS_0"])
positions = accessor(doc, binary, prim["attributes"]["POSITION"])
check("weights: four joints and four weights for every vertex, each set adding up to 1, the biggest first, every joint a joint of the skin",
      len(joints) == len(weights) == nverts and all(abs(sum(w) - 1) < 1e-5 and w[0] >= w[1] >= w[2] >= w[3] >= 0 for w in weights) and all(max(j) < len(bones) for j in joints), "%d vertices" % nverts)


def main_joint(vertex):
    return names[joints[vertex][0]]


def near(point, radius):
    ''' the vertices within `radius` mm of a place of the model (the positions in the file are metres, Y up) '''
    return [v for v, (x, y, z) in enumerate(positions)
            if (x * 1000 - point[0]) ** 2 + (-z * 1000 - point[1]) ** 2 + (y * 1000 - point[2]) ** 2 < radius ** 2]


for label, point, radius, joint_name in (("the tip of the hand", (37, 8, 89), 2.5, "hand.R"), ("the top of the head", (0, 2, 172), 3, "head"),
                                         ("the middle of the right forearm", (34, 4, 102), 4, "elbow.R"), ("the middle of the left forearm", (-34, 4, 102), 4, "elbow.L"),
                                         ("the right shin", (11, 0, 30), 5, "knee.R"), ("the front of the right foot", (11, 16.5, 3), 3, "toe.R")):
    found = near(point, radius)
    share = sum(1 for v in found if main_joint(v) == joint_name) / max(1, len(found))
    check("weights: %s is moved by %s" % (label, joint_name), len(found) > 3 and share > 0.9, "%d vertices, %.0f %%" % (len(found), 100 * share))
blended = sum(1 for w in weights if w[1] > 0.01)
middle = near((11, 0, 29), 5)
alone = sum(1 for v in middle if weights[v][1] < 0.01) / max(1, len(middle))
check("weights: the middle of a long bone (the shin) follows its joint alone, the parts at the joints are shared", alone > 0.9 and 0.02 * nverts < blended < 0.9 * nverts,
      "%d of %d vertices of the shin alone; %d of %d vertices share" % (round(alone * len(middle)), len(middle), blended, nverts))
# (a bone that is only near does not move a vertex: nothing of the left half is moved by a joint of the right one, and the other way round)
right = [v for v, (x, y, z) in enumerate(positions) if x * 1000 > 4 and z * -1000 > -80 and y * 1000 < 80]
left = [v for v, (x, y, z) in enumerate(positions) if x * 1000 < -4 and y * 1000 < 80]
used = lambda vs, suffix: sum(1 for v in vs for k, w in zip(joints[v], weights[v]) if w > 0 and names[k].endswith(suffix))
check("weights: the right half is moved by no joint of the left, the left by none of the right", used(right, ".L") == 0 and used(left, ".R") == 0, "%d and %d vertices" % (len(right), len(left)))

# 3. a wider blend shares more
export_mesh(figure, "meshes/hero_soft.glb", skeleton=bones, skin_falloff=20)
doc2, binary2 = read_glb("meshes/hero_soft.glb")
weights2 = accessor(doc2, binary2, doc2["meshes"][0]["primitives"][0]["attributes"]["WEIGHTS_0"])
blended2 = sum(1 for w in weights2 if w[1] > 0.01)
check("skin_falloff: 20 mm shares more vertices than 4 % of the model", blended2 > blended, "%d against %d" % (blended2, blended))

# 4. with materials and texture coordinates in the same file
export_mesh(figure, "meshes/hero_all.glb", skeleton=bones, uvs="box", materials=[material("skin", texture="skin.png")])
doc3, binary3 = read_glb("meshes/hero_all.glb")
attributes = doc3["meshes"][0]["primitives"][0]["attributes"]
check("together: the skin, the texture coordinates and the material are in one file", all(k in attributes for k in ("POSITION", "TEXCOORD_0", "JOINTS_0", "WEIGHTS_0"))
      and doc3["materials"][0]["name"] == "skin" and len(doc3["skins"][0]["joints"]) == len(bones))

# 5. what is refused
for label, call in (("an OBJ has no skeleton", lambda: export_mesh(figure, "meshes/hero.obj", skeleton=bones)),
                    ("two joints with one name", lambda: export_mesh(figure, "meshes/x.glb", skeleton=[joint("a", (0, 0, 0)), joint("a", (1, 0, 0), parent="a")])),
                    ("a joint that hangs from one that is not there", lambda: export_mesh(figure, "meshes/x.glb", skeleton=[joint("a", (0, 0, 0)), joint("b", (1, 0, 0), parent="c")])),
                    ("two roots", lambda: export_mesh(figure, "meshes/x.glb", skeleton=[joint("a", (0, 0, 0)), joint("b", (1, 0, 0))])),
                    ("a joint that hangs from itself", lambda: joint("a", (0, 0, 0), parent="a")),
                    ("a falloff of 0", lambda: export_mesh(figure, "meshes/x.glb", skeleton=bones, skin_falloff=0))):
    try:
        call()
        check(label + " is refused", False)
    except (ValueError, TypeError) as e:
        check(label + " is refused", True, str(e)[:70])

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")
