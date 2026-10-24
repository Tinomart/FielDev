# A character: armatures that taper between joints, joined into one body, with the other half made by a mirror.
#
#   arm = armature([shoulder, elbow, hand], radii=6)          a tube through the points, as thick at each as 6 times its size
#   hero = character([spine, head, arm, leg, foot], blend=4, symmetric="x")
#
# The radius at a joint is `radii` times the SIZE of its point -- the scale of its gizmo.  Things to try, with the viewport focused:
#   * Press a point (the shoulder, the elbow, the hand) and drag it: the arm follows, and so does the arm on the other side.
#   * Select the elbow: the gold ring round it is its size.  Drag it and the arm is thicker or thinner there.
#   * The body is modelled once, on the right of x = 0; symmetric="x" makes the left half.  An armature takes points or tuples of numbers: the spine, the
#     head, the leg and the foot are tuples -- nothing to drag -- the arm is made of points.
#   * export_mesh(hero, "character.glb") would write it as a mesh (see example 32).
#
# The script also checks the fields it makes and prints a line that starts with ok or FAIL for each (in the output pane).
from fieldev import *

view.set_bounds((-70, -40, -12), (70, 40, 185))
view.set_resolution(1)
view.set_quality(8)

# The arm: three points, each a model of its own.  The radius there is 6 times the size of the point: the elbow is 0.75 of that (4.5) and the hand 0.58 (3.5), as their gizmos say.
shoulder = point(18, 0, 138)
shoulder
elbow = point(31, 0, 113)
elbow = gizmo(
    elbow,
    move=(var(0), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(0.75), var(0.75), var(0.75)),
)
elbow
hand = point(37, 8, 92)
hand = gizmo(
    hand,
    move=(var(0), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(0.58), var(0.58), var(0.58)),
)
hand

# The parts, each an armature -- a tube along its nodes.  The tuples are the nodes of the spine, the head, the leg and the foot; a list of radii says how thick each is
arm = armature([shoulder, elbow, hand], radii=6, name="arm")
spine = armature([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5], name="spine")
head = armature([(0, 2, 159), (0, 2, 167)], radii=11, name="head")
leg = armature([(9, 0, 88), (11, 0, 48), (11, 0, 9)], radii=[8, 5.5, 4], name="leg")
foot = armature([(11, 0, 9), (11, 14, 4)], radii=[4.5, 3], name="foot")

# The character: the armatures joined as one body, blended where they meet (4 mm), the other half a mirror image
hero = character([spine, head, arm, leg, foot], blend=4, symmetric="x")
hero


failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def at(shape, x, y, z):
    return float(shape(x, y, z))


# round_cone: a ball of radius 2 at one end, of 4 at the other, and the surface between them
cone = round_cone((0, 0, 0), (0, 0, 10), 2, 4)
ends = ((2, 0, 0), (0, -2, 0), (0, 0, -2), (4, 0, 10), (0, 4, 10), (0, 0, 14))
check("round_cone: the surface is 2 from the first end and 4 from the second", all(abs(at(cone, *p)) < 1e-6 for p in ends))
check("round_cone: half way the radius is 3", abs(at(cone, 3, 0, 5)) < 1e-6 and abs(at(cone, 0, -3, 5)) < 1e-6)
check("round_cone: negative inside, positive outside", at(cone, 0, 0, 5) < 0 < at(cone, 9, 0, 5), "%.2f inside, %.2f outside" % (at(cone, 0, 0, 5), at(cone, 9, 0, 5)))

# chain: the radius at a joint is radii[i] times the size (the scale of the gizmo) of its point
fat = gizmo(
    point(0, 0, 0),
    move=(var(0), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(2), var(2), var(2)),
)
check("chain: one point is a ball, its radius is radii times its size (3 * 2)", abs(at(chain([fat], radii=3), 6, 0, 0)) < 1e-6)
check("chain: with no radii the size of the point is the radius (1 * 2)", abs(at(chain([fat]), 0, 2, 0)) < 1e-6)
check("chain: a tuple has the size 1", abs(at(chain([(0, 0, 0), (0, 0, 10)], radii=[3, 3]), 3, 0, 5)) < 1e-6)
try:
    chain([(0, 0, 0), (0, 0, 10)], radii=[1, 2, 3])
    check("chain: three radii for two points is refused", False)
except ValueError as e:
    check("chain: three radii for two points is refused", True, str(e)[:60])

# the character: a body where the armatures are, nothing where they are not, the same on both sides
inside = ((0, 0, 120), (0, 2, 163), (30, 0, 112), (-30, 0, 112), (11, 0, 30), (-11, 0, 30), (11, 10, 5))
outside = ((0, 0, 190), (60, 0, 112), (-60, 0, 112), (0, 30, 100), (25, 0, 60))
check("character: inside the body, the arms, the head, the legs and the feet", all(at(hero, *p) < 0 for p in inside))
check("character: outside between the arms and the legs, and beyond", all(at(hero, *p) > 0 for p in outside))
check("character: the left is the mirror of the right", all(abs(at(hero, x, y, z) - at(hero, -x, y, z)) < 1e-6 for x, y, z in ((25, 5, 100), (33, 4, 105), (14, 3, 60), (8, 0, 20))))

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")
