# A feature: a surface stitched through loops of points, for the delicate parts of a character -- a nose, a muzzle, an ear, a finger -- and a UV map made from the armature.
#
#   bridge = ring((0, -5, 1), (3.2, 2.8), 8, (0, -1, 0))             the points of a loop: a centre, a radius (or wide and high), how many, the way it faces
#   nose = feature([bridge, middle, tip, nostrils], detail=3, name="nose")      the skin from one loop to the next, closed at the first and the last
#   hero = character([head, nose], blend=1)                           a feature joins the body as a limb does
#   export_mesh(hero, "feature_nose.obj", uvs="armature")             every limb and feature an island of its own: a limb along its path, a feature along its loops
#
# The loops of a feature are like cross-sections: they are stacked in the way the feature runs (here out from the face, along -y), and each faces that way. The loops are points
# (`point(x, y, z)`, dragged with their gizmos) or tuples; every number of the feature is an expression of them. The script writes the file, reads the report of the UV map, and prints
# a line that starts with ok or FAIL for every check (in the output pane).
from fieldev import *

view.set_bounds((-16, -18, -16), (16, 12, 16))
view.set_resolution(2)

head = limb([(0, 0, -4), (0, 0, 8)], radii=7, name="head")
head

bridge = ring((0, -5, 1), (3.2, 2.8), 8, (0, -1, 0))
middle = ring((0, -7.5, 0.5), (2.6, 2.4), 8, (0, -1, 0))
tip = ring((0, -9.5, 0), (3.0, 2.6), 8, (0, -1, 0))
nostrils = ring((0, -10.5, 0), (1.8, 1.5), 8, (0, -1, 0))
nose = feature([bridge, middle, tip, nostrils], detail=3, name="nose")
nose

hero = character([head, nose], blend=1)
hero

failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def at(shape, x, y, z):
    return float(shape(x, y, z))


# 1. the feature is a body between its loops: inside near the middle of the loops, outside beyond them and beside them
check("feature: inside, between the loops, off the axis", all(at(nose, *p) < 0 for p in ((1.0, -6.5, 0.8), (-1.5, -8.5, 0.3), (0.5, -10.0, -0.5), (2.0, -5.8, 1.5))))
check("feature: outside, beyond the first and the last loop and beside the loops", all(at(nose, *p) > 0 for p in ((0, -11.6, 0), (0, -3.6, 1), (5.5, -7.5, 0.5), (0, -7.5, 5))))
check("feature: the loops are the ones it was given (its rings are the loops, with the rings between them)", nose._feature.loops == 4 and len(nose._feature.rings) == 3 * 3 + 1,
      "%d rings" % len(nose._feature.rings))
try:
    feature([bridge, ring((0, -5, 0), 2, 6, (0, -1, 0))])
    check("feature: loops of different sizes are refused", False)
except ValueError:
    check("feature: loops of different sizes are refused", True)

# 2. the UV map by part: the head a tube along its path, the nose along its loops
uv = uv_armature(margin=4, size=512)
path = export_mesh(hero, "feature_nose.obj", resolution=2, uvs=uv)
report = uv.report or {}
check("uv_armature: an island for the head and an island for the nose", report.get("islands") == 2 and set(report.get("parts", [])) == {"head", "nose"}, "%s" % (report.get("parts"),))
us, vs = [], []
with open(path) as f:
    for line in f:
        if line.startswith("vt "):
            a = line.split()
            us.append(float(a[1]))
            vs.append(float(a[2]))
check("uv_armature: every place is inside the square of the texture", bool(us) and min(us) >= -1e-6 and max(us) <= 1 + 1e-6 and min(vs) >= -1e-6 and max(vs) <= 1 + 1e-6,
      "u %.3f..%.3f, v %.3f..%.3f" % (min(us), max(us), min(vs), max(vs)) if us else "no vt lines")
stretch = report.get("stretch")
check("uv_armature: the texture is not stretched much (the 1st and 99th percentile of the area in the texture against the median: a few triangles where the nose joins the head differ)",
      stretch is not None and 0.05 < stretch[0] and stretch[1] < 8.0, "%s" % (stretch,))
flat = [d for d in report.get("detail", []) if d[1] and d[2] > 0.02 * d[1]]
check("uv_armature: no island has more than a fiftieth of its triangles with no area in the texture", not flat, "%s" % (flat,))

print("")
print("all %d checks passed" % 8 if not failed else "%d of the checks failed: %s" % (len(failed), ", ".join(failed)))
