# Characters

A character is modelled from **points**: a skeleton of joints, each with a size, and the flesh round them. `chain` makes a limb through points,
`round_cone` is the segment it is made of. Both are fields like everything else in the library, so a character is blended, offset, textured, mirrored and
exported like any other model (see [Meshes](meshes.md)).

```python
from fieldev import *

shoulder = point(18, 0, 138)
elbow = point(31, 0, 113)
hand = point(37, 8, 92)

arm = chain([shoulder, elbow, hand], radii=[6, 4.5, 3.5])        # a limb that tapers: a round cone from joint to joint
leg = chain([(9, 0, 88), (11, 0, 48), (11, 0, 9)], radii=[8, 5.5, 4])
head = chain([(0, 2, 163)], radii=11)                          # one point: a ball
body = symmetric_x(union_all([arm, leg, head], blend=4))       # the right half, blended, and its mirror image
```

[`examples/33_character.py`](../examples/33_character.py) is a whole figure made this way.

## `round_cone(a, b, ra, rb)`

Two balls -- radius `ra` at `a`, radius `rb` at `b` (the same as `ra` when it is left out) -- and the surface between them, whose radius changes along
the way from one to the other: a bone with its two joints, a tapering limb. `a` and `b` are points or tuples of numbers; the radii are numbers or fields
(a radius that is thick here and thin there). Each end is a ball, so limbs that meet at a joint are one smooth body there.

Where the radius changes fast over a short way the surface is steeper than the field is: it is a body, not a distance. Offsets and shells of a very
tapered cone are not exact.

## `chain(points, radii=None, blend=0)`

A round cone between each two points that follow each other, joined as one body.

- **`points`** are the joints in order: points (`point(x, y, z)`, dragged in the viewport with their gizmos) or tuples of numbers. One point makes a ball.
- **The radius at a joint is the size of its point times `radii[i]`.** The size of a point is the scale of its gizmo (the gold ring round it, 1 for a point
  that has no gizmo). With no `radii` the size of a point is its radius, so the limb is shaped in the viewport: drag the points to move it, drag
  the rings to make it thicker or thinner there. `radii` is a number for all the joints, or a list with one for each; its numbers can be fields.
- **`blend`** is the radius of a smooth blend where the segments meet. The default, 0, is no blend: the joints are balls already, so a chain is
  smooth without it. A blend adds a little material at every joint.

A chain is a line. A body that branches -- a torso with arms, legs and a head -- is several chains joined with `union_all(chains, blend=4)` or
`smooth_union(a, b, 4)`; the blend there makes the shoulder and the hip.

## Armatures: limbs, a character, a skeleton

A **limb** is a path extruded: a cross-section swept along a smooth curve through its nodes, thicker or thinner at each node. The nodes of a limb are the joints
of a skeleton, so one armature is the body and the rig.

```python
spine = limb([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5], name="spine", joints=["hips", "spine", "chest", "neck"])
head = limb([(0, 0, 147), (0, 2, 163)], radii=[5, 11], name="head")                  # begins on the neck: a branch of it
arm = limb([shoulder, elbow, hand], radii=[6, 4.5, 3.5], name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"], parent="chest")
hero = character([spine, head, arm], blend=4, symmetric="x")                        # the limbs joined with a blend; the left half a mirror image
bones = skeleton_of([spine, head, arm], mirror="x")                                 # a joint at each node, each hanging from the one before it
export_mesh(hero, "hero.glb", symmetric="x", skeleton=bones)
```

- **`limb(points, radii, profile, name, joints, parent, detail, twist)`**. The nodes are points or tuples; the thickness at a node is its `radii` times the size of
  the point, as in `chain`. With no `profile` the cross-section is round and the sweep is made of round cones along a Catmull-Rom spline through the nodes (`detail`
  of them between two nodes) -- every number in it is an expression of the nodes, so a node dragged in the viewport moves the limb at once. With `profile=` any
  2D shape -- a square, a polygon, a profile of your own -- the limb is `path_extrude(profile, spline(nodes), twist)`: the cross-section keeps its shape along the
  path, and the point's rotation twists it.
- **`character(limbs, blend=3, symmetric=None)`** joins the limbs into one body with a smooth blend where they meet, and with `symmetric="x"` adds the mirror image.
- **`skeleton_of(limbs, mirror=None, plane=0.0, join=None)`** makes a joint at each node, named by the limb's `joints` (or `name_0`, `name_1` ...). A limb whose first
  node is the same place as a joint of an earlier limb (within half a millimetre: the same point, or the same place typed again) is a **branch** of it: that
  joint is its first and its other nodes hang from it. A limb that is not on any joint hangs from the joint `parent=` names. `mirror="x"` gives every joint whose
  name ends with `.R` a `.L` one across that plane. There is one root, the first node of the first limb.
- **Joints with a place of their own.** `joint(name, position, parent, tip, influence=body_or_field)` owns the skin where `influence` is negative: the jaw
  follows the jaw alone inside its box, and fades to the weights of the bones over `skin_falloff`. `mirror_joints` mirrors the influence with the joint.
- **`export_mesh(..., max_influences=4)`**: the most joints that move a vertex, 1 to 8 (4 is what engines run; above 4 the file has `JOINTS_1` and `WEIGHTS_1` as well).

[`examples/40_armature.py`](../examples/40_armature.py) builds the figure of example 33 from limbs, reads the rigged file back and checks the joints, the hierarchy,
where the weights go, the jaw's influence and the bones a vertex can have.

### Building a character in the viewport

The **Character** section of the right-click menu is made for building this by hand, node after node, the way Dust3D does -- with a camera you can turn:

1. **Reference image →** *Front* (then *Right*): choose a drawing of the character; `reference_image(...)` stands it in the scene behind the models ([Reference images](interface.md#reference-images)).
   Set `height` and `center` in the script so that it is the size of the character and stands on the ground.
2. **Draw a limb**: the work plane opens facing the picture and the *Limb* button is on; click the nodes of the spine, the neck, an arm, a leg -- one limb at a time, `Enter` ends each -- and each is a
   `limb(...)` of points with gizmos. A node's scale is how thick the limb is there; drag a node to move it (`Ctrl+Shift+W` makes a work plane from another view, to move the nodes over the side picture).
3. Start a limb on a joint of another to branch it (the arm on the chest); **character** (right-click a limb, or select several) joins them with a blend, `symmetric="x"` adds the mirror image, and **skeleton_of** makes
   the joints for the export.

## The other half

A body is modelled once and mirrored. `symmetric_x(body)` keeps the part with x of 0 or more and adds its mirror image, so the left arm follows the right
one while you drag it. For a mesh that is symmetric to the last bit -- for a game engine's mirrored skinning and normal maps -- export with the mesh's
own symmetry instead: `export_mesh(body, "hero.glb", symmetric="x")` cuts the half exactly at x = 0 and mirrors it, with no seam
(see [Units, axes, a budget of triangles, symmetry](meshes.md#units-axes-a-budget-of-triangles-symmetry)).

## The skeleton

A character is rigged with `joint(...)`s -- the same points the limbs are made of can be the joints -- and `export_mesh(body, "hero.glb", skeleton=bones)` writes
them with the skin weights for a game engine: see [Skeleton and skin weights](meshes.md#skeleton-and-skin-weights-gltf). `mirror_joints` makes the left side of a
skeleton from the right, as `symmetric_x` makes the left half of the body.
[`examples/36_skeleton.py`](../examples/36_skeleton.py) does it for the figure of example 33.

## Menus

In the viewport's menu of empty space the shapes the library makes of points are under **Parametric shapes**; select points first and the entry is made
from them, in the order you selected them. The same is true of a profile, a polyline and a spline.
