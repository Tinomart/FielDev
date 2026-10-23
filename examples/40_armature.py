# An armature: a character made of armatures -- paths of nodes, each with a thickness -- and the skeleton that comes from the same nodes.
#
#   arm = armature([shoulder, elbow, hand], radii=4.5, name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"], parent="chest")
#   hero = character([spine, head, arm, leg ...], blend=4, symmetric="x")       the armatures joined with a blend; the left half is the mirror image
#   bones = skeleton_of([spine, head, arm, leg ...], mirror="x")                a joint at each node, each hanging from the one before it
#   export_mesh(hero, "hero.glb", symmetric="x", skeleton=bones)
#
# An armature is a path extruded: a round cross-section swept along a smooth curve through the nodes (or any 2D shape: armature(..., profile=rectangle(...))).  The thickness at a node is
# the size of its point -- the gold ring of its gizmo -- times radii; every number is an expression of the nodes, so a node dragged in the viewport moves its armature at once.
# An armature that starts on a node of another armature (the same point, or a place within half a millimetre) hangs from that joint; `parent="chest"` says where an armature is joined when it does
# not start on a node.  A joint with an `influence` (a body or a field) owns the skin where that field is negative: here the jaw owns a small box of the head.
#
# The figure is drawn (the joints are inside it; the nodes of the arm are points, and are seen through it).  The script writes the file, reads it back, and prints a line that starts with ok or FAIL for every check (in the output pane).
import json
import struct
from fieldev import *

view.set_bounds((-70, -40, -12), (70, 40, 185))
view.set_resolution(1)
view.set_quality(8)

shoulder = point(18, 0, 138)
shoulder
elbow = point(31, 0, 113)
elbow
hand = point(37, 8, 92)
hand

spine = armature([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5], name="spine", joints=["hips", "spine", "chest", "neck"])
head = armature([(0, 0, 147), (0, 2, 163)], radii=[5, 11], name="head", joints=["neck_top", "head"])
arm = armature([shoulder, elbow, hand], radii=4.5, name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"], parent="chest")
leg = armature([(9, 0, 88), (11, 0, 48), (11, 0, 9)], radii=[8, 5.5, 4], name="leg.R", joints=["hip.R", "knee.R", "ankle.R"], parent="hips")
foot = armature([(11, 0, 9), (11, 14, 4)], radii=[4.5, 3], name="foot.R", joints=["ankle_foot.R", "toe.R"])
armatures = [spine, head, arm, leg, foot]

hero = character(armatures, blend=4, symmetric="x")
hero

failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def at(shape, x, y, z):
    return float(shape(x, y, z))


# 1. the body: where the armatures are, nothing where they are not, the same on both sides
inside = ((0, 0, 120), (0, 2, 163), (30, 0, 112), (-30, 0, 112), (11, 0, 30), (-11, 0, 30), (11, 10, 5))
outside = ((0, 0, 190), (60, 0, 112), (-60, 0, 112), (0, 30, 100), (25, 0, 60))
check("character: inside the body, the arms, the head, the legs and the feet", all(at(hero, *p) < 0 for p in inside))
check("character: outside between the arms and the legs, and beyond", all(at(hero, *p) > 0 for p in outside))
check("character: the left is the mirror of the right", all(abs(at(hero, x, y, z) - at(hero, -x, y, z)) < 1e-6 for x, y, z in ((25, 5, 100), (33, 4, 105), (14, 3, 60), (8, 0, 20))))
check("armature: thick where the radius says (13 at the hips, 5 at the neck; the cross-section is a rounded square, so the edge is within a tenth of the radius of it)",
      abs(at(spine, 13, 0, 92)) < 1.3 and abs(at(spine, 5, 0, 147)) < 0.5,
      "%.2f at the hips, %.2f at the neck" % (at(spine, 13, 0, 92), at(spine, 5, 0, 147)))
check("armature: a smooth curve through the nodes (the arm passes the elbow)", abs(at(arm, 31 + 4.5, 0, 113)) < 1.2 and at(arm, 31, 0, 113) < 0)

# 2. an armature with a profile of its own: a square cross-section, swept along the path
square_arm = armature([point(60, 0, 100), point(60, 0, 130), point(60, 20, 150)], profile=rectangle((-4, -4), (4, 4)))
square_arm
check("profile: a square armature is a body along its path (inside on the path, outside beside it)", at(square_arm, 60, 0, 115) < 0 < at(square_arm, 72, 0, 115))

# 3. the skeleton
bones = skeleton_of(armatures, mirror="x")
names = [j.name for j in bones]
check("skeleton: a joint for every node that is not another armature's (the head's first node is the neck, the foot's the ankle), the left side made by the mirror",
      len(bones) == 19 and "elbow.L" in names and "hips" in names and "neck_top" not in names and len(set(names)) == len(names), "%d joints" % len(bones))
parents = {j.name: j.parent for j in bones}
check("skeleton: the arm hangs from the chest, the head from the neck, the leg from the hips, the foot from the ankle, the hips are the root",
      parents["shoulder.R"] == "chest" and parents["head"] == "neck" and parents["hip.R"] == "hips" and parents["toe.R"] == "ankle.R" and parents["hips"] is None,
      "%s" % sorted(parents.items())[:3])

# 4. the rigged file, read back
SIZES = {5121: ("B", 1), 5126: ("f", 4), 5125: ("I", 4)}
COUNTS = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "VEC2": 2, "MAT4": 16}


def read_glb(path):
    data = open(path, "rb").read()
    jsize = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + jsize].decode("utf-8")), data[20 + jsize + 8:]


def accessor(doc, binary, index):
    a = doc["accessors"][index]
    v = doc["bufferViews"][a["bufferView"]]
    code, size = SIZES[a["componentType"]]
    n = COUNTS[a["type"]]
    flat = struct.unpack_from("<%d%s" % (a["count"] * n, code), binary, v.get("byteOffset", 0) + a.get("byteOffset", 0))
    return [flat[i * n:(i + 1) * n] for i in range(a["count"])]


export_mesh(hero, "meshes/hero_armature.glb", symmetric="x", skeleton=bones)
doc, binary = read_glb("meshes/hero_armature.glb")
prim = doc["meshes"][0]["primitives"][0]
joints = accessor(doc, binary, prim["attributes"]["JOINTS_0"])
weights = accessor(doc, binary, prim["attributes"]["WEIGHTS_0"])
positions = accessor(doc, binary, prim["attributes"]["POSITION"])
check("file: a skin with all the joints, weights adding up to 1 for every vertex", len(doc["skins"][0]["joints"]) == len(bones) and all(abs(sum(w) - 1) < 1e-5 for w in weights),
      "%d vertices" % len(positions))


def near(point, radius):
    return [v for v, (x, y, z) in enumerate(positions) if (x * 1000 - point[0]) ** 2 + (-z * 1000 - point[1]) ** 2 + (y * 1000 - point[2]) ** 2 < radius ** 2]


def main_joint(vertex):
    return names[joints[vertex][0]]


for label, place, radius, joint_name in (("the end of the hand (the flat end of the last armature, where the bone of the forearm ends)", (37, 8, 92), 3, ("hand.R", "elbow.R")),
                                         ("the middle of the right forearm", (34, 4, 102), 4, "elbow.R"),
                                         ("the middle of the left forearm", (-34, 4, 102), 4, "elbow.L"), ("the right shin", (11, 0, 30), 5, "knee.R")):
    found = near(place, radius)
    allowed = joint_name if isinstance(joint_name, tuple) else (joint_name,)
    share = sum(1 for v in found if main_joint(v) in allowed) / max(1, len(found))
    check("weights: %s is moved by %s" % (label, " or ".join(allowed)), len(found) > 3 and share > 0.9, "%d vertices, %.0f %%" % (len(found), 100 * share))

# 5. a joint that owns a place: the jaw owns a box of the head
jaw_box = box((-8, 4, 150), (8, 14, 158))
with_jaw = armatures + [armature([(0, 2, 163), (0, 10, 154)], radii=[3, 3], name="jaw", joints=["head_jaw", "jaw"])]
jaw_bones = skeleton_of(with_jaw, mirror="x")
jaw_bones = [Joint(j.name, j.position, j.parent, j.tip, jaw_box) if j.name == "jaw" else j for j in jaw_bones]
export_mesh(hero, "meshes/hero_jaw.glb", symmetric="x", skeleton=jaw_bones, skin_falloff=2)
doc2, binary2 = read_glb("meshes/hero_jaw.glb")
prim2 = doc2["meshes"][0]["primitives"][0]
j2 = accessor(doc2, binary2, prim2["attributes"]["JOINTS_0"])
w2 = accessor(doc2, binary2, prim2["attributes"]["WEIGHTS_0"])
pos2 = accessor(doc2, binary2, prim2["attributes"]["POSITION"])
names2 = [j.name for j in jaw_bones]
owned = [v for v, (x, y, z) in enumerate(pos2) if -6 < x * 1000 < 6 and 6 < -z * 1000 < 12 and 151 < y * 1000 < 157]
share = sum(1 for v in owned if names2[j2[v][0]] == "jaw" and w2[v][0] > 0.95) / max(1, len(owned))
check("influence: the skin inside the jaw's box follows the jaw alone", len(owned) > 3 and share > 0.9, "%d vertices, %.0f %%" % (len(owned), 100 * share))

# 6. up to eight joints a vertex
export_mesh(hero, "meshes/hero_eight.glb", symmetric="x", skeleton=bones, max_influences=8)
doc3, binary3 = read_glb("meshes/hero_eight.glb")
attributes = doc3["meshes"][0]["primitives"][0]["attributes"]
check("max_influences: eight a vertex gives JOINTS_1 and WEIGHTS_1", "JOINTS_1" in attributes and "WEIGHTS_1" in attributes and "JOINTS_2" not in attributes)
w3a, w3b = accessor(doc3, binary3, attributes["WEIGHTS_0"]), accessor(doc3, binary3, attributes["WEIGHTS_1"])
check("max_influences: the weights of the two sets add up to 1", all(abs(sum(a) + sum(b) - 1) < 1e-5 for a, b in zip(w3a, w3b)))
export_mesh(hero, "meshes/hero_two.glb", symmetric="x", skeleton=bones, max_influences=2)
doc4, binary4 = read_glb("meshes/hero_two.glb")
w4 = accessor(doc4, binary4, doc4["meshes"][0]["primitives"][0]["attributes"]["WEIGHTS_0"])
check("max_influences: two a vertex leaves the third and fourth weight at 0, the rest adding up to 1", all(a[2] == 0 and a[3] == 0 and abs(a[0] + a[1] - 1) < 1e-5 for a in w4))

# 7. what is refused
for label, call in (("an armature with no nodes", lambda: armature([])),
                    ("radii for the wrong number of nodes", lambda: armature([(0, 0, 0), (0, 0, 10)], radii=[1, 2, 3])),
                    ("joint names that are not one for each node", lambda: armature([(0, 0, 0), (0, 0, 10)], joints=["a"])),
                    ("an armature that is joined nowhere", lambda: skeleton_of([armature([(0, 0, 0), (0, 0, 10)]), armature([(50, 0, 0), (50, 0, 10)], name="far")])),
                    ("a parent that is not a joint", lambda: skeleton_of([armature([(0, 0, 0), (0, 0, 10)]), armature([(50, 0, 0), (50, 0, 10)], parent="nobody")])),
                    ("a character with no armatures", lambda: character([]))):
    try:
        call()
        check(label + " is refused", False)
    except (ValueError, TypeError) as e:
        check(label + " is refused", True, str(e)[:70])

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")
