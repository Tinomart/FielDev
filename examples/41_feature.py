# A feature: a surface stitched through loops of points, for the delicate parts of a character -- a face, an ear, a hand -- and a UV map made from the armature.
#
#   face = feature([outline, eye, mouth, nose], mirror="x", name="face")     every point is a vertex of the surface, every loop an edge loop of it
#   loop(points, closed=, mirror=, opening=)                                  one loop, with a choice of its own (ring(...) is a closed round one)
#   hero = character([head, face], blend=1)                                   a feature joins the body as a limb does
#   export_mesh(hero, "feature_face.obj", uvs="armature")                     every limb and feature an island of its own: a feature flat, as it was drawn
#
# The points are joined in the plane of a view (here the front: x to the right, z up) and keep their own depth (y). Nothing is automatic unless it is written: the mirror, the
# snap, the openings, the trimming, the holes and the back are arguments of feature(...), and a loop can say its own choice. The script writes the file, reads the report of the UV
# map, and prints a line that starts with ok or FAIL for every check (in the output pane).
import math

from fieldev import *

view.set_bounds((-14, -16, -10), (14, 8, 14))
view.set_resolution(2)


def front(x):
    # the surface of the head in front: a capsule of radius 7 along z (the face looks along -y)
    return -math.sqrt(49.0 - x * x)


head = limb([(0, 0, -4), (0, 0, 8)], radii=7, name="head")
head

# half of the face, drawn on the front view: the outline from the chin to the top of the head (open: its two ends are on the plane x = 0, so mirroring makes it a ring), an eye
# (a closed ring, one side only), a mouth (open, one end on the plane) and a nose (open, both ends on the plane, a ridge in front of the face)
outline = loop([(x, front(x) - 0.2, z) for x, z in ((0, -2.5), (2.2, -1.8), (4.0, 0.0), (4.4, 2.5), (3.6, 4.8), (1.8, 5.8), (0, 6.2))])
eye = ring((2.2, front(2.2) - 0.2, 3.0), (0.9, 0.5), 8)
mouth = loop([(0, front(0) - 0.2, 0.2), (1.2, front(1.2) - 0.2, 0.1), (2.2, front(2.2) - 0.2, 0.5)])
nose = loop([(0, -7.8, 2.4), (0.7, -7.6, 1.2), (0, -7.7, 0.8)])
face = feature([outline, eye, mouth, nose], view="front", mirror="x", snap=0, openings=True, trim=True, fill_holes=8, back=False, thickness=0.6, name="face")
face

hero = character([head, face], blend=1)
hero

failed = []
total = [0]


def check(label, ok, detail=""):
    total[0] += 1
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def at(shape, x, y, z):
    return float(shape(x, y, z))


# 1. the face is a shell round the surface that was stitched: every point of a loop is on the surface (inside the shell by half its thickness), the eye is an opening, and the
# face is mirrored: the same on both sides of x = 0
corner = outline[2]
check("feature: the points of the loops are on the surface (half the thickness inside)", all(abs(at(face, *p) + 0.3) < 0.02 for p in (outline[2], outline[4], mouth[1], nose[1])),
      "%.3f" % at(face, *corner))
eye_middle = (2.2, front(2.2) - 0.2, 3.0)
check("feature: the eye is an opening, with no surface in it", at(face, *eye_middle) > 0.1, "%.3f" % at(face, *eye_middle))
check("feature: mirrored across x = 0", all(abs(at(face, x, y, z) - at(face, -x, y, z)) < 1e-3 for x, y, z in ((corner[0], corner[1], corner[2]), (1.4, front(1.4), 1.0), (2.2, -7.0, 3.0))))

# 2. nothing is automatic: the same loops without the mirror are one side of the face, with the openings off the eye is surface, with a closed back the face is a solid
one_side = feature([outline, eye, mouth, nose], mirror=None, name="one side")
check("feature: without a mirror only the side that was drawn is there (the loops of the other side are not made)", at(one_side, *corner) < 0 and at(one_side, -corner[0], corner[1], corner[2]) > 0.5,
      "%.3f and %.3f" % (at(one_side, *corner), at(one_side, -corner[0], corner[1], corner[2])))
filled = feature([outline, eye, mouth, nose], mirror="x", openings=False, name="filled")
check("feature: openings=False stitches across the eye", at(filled, *eye_middle) < 0, "%.3f" % at(filled, *eye_middle))
own_choice = feature([outline, loop(eye, closed=True, opening=False), mouth, nose], mirror="x", name="own choice")
check("feature: a loop says its own choice (opening=False for the eye alone)", at(own_choice, *eye_middle) < 0 and at(own_choice, *corner) < 0)
solid = feature([outline, mouth, nose], mirror="x", back=True, name="solid")
check("feature: with a closed back it is a solid (no open edge, negative inside)", solid._feature.surface.closed and at(solid, 0, -5.5, 2.5) < 0, "%.3f" % at(solid, 0, -5.5, 2.5))

# 3. the vertices are the points: nothing is added to the loops, and loops that cross are refused
surface = face._feature.surface
# (the outline is a ring of 2 * 7 - 2 points once mirrored, the eye and its image 2 * 8, the mouth 2 * 3 - 1, the nose 2 * 3 - 2: the points and their images, and nothing else)
check("feature: every vertex of the surface comes from a point of a loop, or its mirror image",
      all(s is not None for s in surface.sources) and len(surface.vertices) == (2 * len(outline) - 2) + 2 * len(eye) + (2 * len(mouth) - 1) + (2 * len(nose) - 2),
      "%d vertices" % len(surface.vertices))
try:
    feature([loop([(0, 0, 0), (4, 0, 4)]), loop([(0, 0, 4), (4, 0, 0)])])
    check("feature: loops that cross are refused", False)
except ValueError:
    check("feature: loops that cross are refused", True)

# 4. the UV map by part: the head a tube along its path, the face flat as it was drawn
uv = uv_armature(margin=4, size=512)
path = export_mesh(hero, "feature_face.obj", resolution=2, uvs=uv)
report = uv.report or {}
parts = report.get("parts", [])
check("uv_armature: an island for the head and one for the face", "head" in parts and "face" in parts, "%s" % (parts,))
us, vs = [], []
with open(path) as f:
    for line in f:
        if line.startswith("vt "):
            a = line.split()
            us.append(float(a[1]))
            vs.append(float(a[2]))
check("uv_armature: every place is inside the square of the texture", bool(us) and min(us) >= -1e-6 and max(us) <= 1 + 1e-6 and min(vs) >= -1e-6 and max(vs) <= 1 + 1e-6,
      "u %.3f..%.3f, v %.3f..%.3f" % (min(us), max(us), min(vs), max(vs)) if us else "no vt lines")
flat = [d for d in report.get("detail", []) if d[0] == "face" and d[1] and d[2] > 0.02 * d[1]]
check("uv_armature: the face, laid flat as it was drawn, has no triangle without area in the texture", not flat, "%s" % (flat,))

print("")
print("all %d checks passed" % total[0] if not failed else "%d of the checks failed: %s" % (len(failed), ", ".join(failed)))
