# Characters

A character is modelled from **points**: a skeleton of joints, each with a size, and the flesh round them. `chain` makes an armature through points,
`round_cone` is the segment it is made of. Both are fields like everything else in the library, so a character is blended, offset, textured, mirrored and
exported like any other model (see [Meshes](meshes.md)).

```python
from fieldev import *

shoulder = point(18, 0, 138)
elbow = point(31, 0, 113)
hand = point(37, 8, 92)

arm = chain([shoulder, elbow, hand], radii=[6, 4.5, 3.5])        # an armature that tapers: a round cone from joint to joint
leg = chain([(9, 0, 88), (11, 0, 48), (11, 0, 9)], radii=[8, 5.5, 4])
head = chain([(0, 2, 163)], radii=11)                          # one point: a ball
body = symmetric_x(union_all([arm, leg, head], blend=4))       # the right half, blended, and its mirror image
```

[`examples/33_character.py`](../examples/33_character.py) is a whole figure made this way.

## `round_cone(a, b, ra, rb)`

Two balls -- radius `ra` at `a`, radius `rb` at `b` (the same as `ra` when it is left out) -- and the surface between them, whose radius changes along
the way from one to the other: a bone with its two joints, a tapering armature. `a` and `b` are points or tuples of numbers; the radii are numbers or fields
(a radius that is thick here and thin there). Each end is a ball, so armatures that meet at a joint are one smooth body there.

Where the radius changes fast over a short way the surface is steeper than the field is: it is a body, not a distance. Offsets and shells of a very
tapered cone are not exact.

## `chain(points, radii=None, blend=0)`

A round cone between each two points that follow each other, joined as one body.

- **`points`** are the joints in order: points (`point(x, y, z)`, dragged in the viewport with their gizmos) or tuples of numbers. One point makes a ball.
- **An armature has the gizmo of an outline, as a profile, a polyline or a spline has**: it has no numbers of its own, its nodes do. Selected as a whole, its nodes share **one gizmo** -- arrows and a dot that move all of it, knobs that stretch it, rings that turn it and scale it about the middle of its nodes. The gizmo button of its row in the model tree (off until you switch it on) writes `arm = gizmo(arm, mode='click')`, which returns the armature itself. A feature model is the same, with its points.
- **The radius at a joint is the size of its point times `radii[i]`.** The size of a point is the scale of its gizmo (the gold ring round it, 1 for a point
  that has no gizmo). With no `radii` the size of a point is its radius, so the armature is shaped in the viewport: drag the points to move it, drag
  the rings to make it thicker or thinner there. `radii` is a number for all the joints, or a list with one for each; its numbers can be fields.
- **`blend`** is the radius of a smooth blend where the segments meet. The default, 0, is no blend: the joints are balls already, so a chain is
  smooth without it. A blend adds a little material at every joint.

A chain is a line. A body that branches -- a torso with arms, legs and a head -- is several chains joined with `union_all(chains, blend=4)` or
`smooth_union(a, b, 4)`; the blend there makes the shoulder and the hip.

## Armatures: armatures, a character, a skeleton

An **armature** is a path extruded: a cross-section swept along a smooth curve through its nodes, thicker or thinner at each node. The nodes of an armature are the joints
of a skeleton, so one armature is the body and the rig.

```python
spine = armature([(0, 0, 92), (0, 0, 106), (0, 0, 128), (0, 0, 147)], radii=[13, 11, 15, 5], name="spine", joints=["hips", "spine", "chest", "neck"])
head = armature([(0, 0, 147), (0, 2, 163)], radii=[5, 11], name="head")                  # begins on the neck: a branch of it
arm = armature([shoulder, elbow, hand], radii=4.5, name="arm.R", joints=["shoulder.R", "elbow.R", "hand.R"], parent="chest")
hero = character([spine, head, arm], blend=4, symmetric="x")                        # the armatures joined with a blend; the left half a mirror image
bones = skeleton_of([spine, head, arm], mirror="x")                                 # a joint at each node, each hanging from the one before it
export_mesh(hero, "hero.glb", symmetric="x", skeleton=bones)
```

- **`armature(points, radii, profile, name, joints, parent, twist, sizing)`**. An armature is a **path extrude**: a cross-section swept along a Catmull-Rom spline through the nodes -- every
  number in it is an expression of the nodes, so a node dragged in the viewport moves the armature at once. The nodes are points or tuples. **The size of a node -- the gold
  ring of its gizmo -- is how thick the armature is there**, and while the armature is selected **every one of its nodes** has that ring, a circle round the node of the armature's **real radius** there: size it against
  the picture you model over, by dragging the ring of a node out or in (the radius is the size of the profile times the node's size). The cross-section is a **profile**: by default
  one made for the armature, a **square whose corners are spline points** (so it is nearly round) with the radius `radii` (a number, 1 by default; for nodes that are tuples, a list
  with one number for each node); or any 2D shape of your own, `profile=my_profile` -- a profile made of points, a polygon, a rectangle -- with its own size, so `radii`
  and `profile=` are not given together. The same profile is swept along the whole armature, from the first node wherever the profile is, and the point's rotation twists it. **The ends are round** where the node there is a spline point -- every node is one, unless it says `point(..., smooth=False)`; the nodes put down in the viewport are corners except the first and the last -- a dome as thick as the armature is at that node (the cross-section shrinking toward the middle of its box, which keeps it inside a round, convex or star-like cross-section; a U or an L, whose box middle is in the notch, gets a dome that covers the notch); a node that is a corner ends the armature flat, with the face of the cross-section. The cross-section at the first node is turned the least that puts it across the path, so that both ends are square to it. The size of a node is the radius there, exactly: a node of size 2 is twice as thick as one of size 1. `sizing="offset"` (off by default; the way a plain `path_extrude` scales is `"scale"`) moves the outline of the cross-section in or out by (size - 1) times the radius of the widest circle it holds instead of scaling it, so that a thinner cross-section of any shape stays inside a thicker one and the round ends close along the same offset; a notch narrower than the push fills in, and an arm thinner than the pull vanishes.
- **`cut_face(armature)`** shows the profile of an armature at its **first node**, as a linked clone of it (`instance`) turned the way the armature leaves the node, with a dot for
  each of the profile's points: pull a dot, double click it, or press the outline to put a point on it, and it is the profile that changes -- and with it the armature. An armature
  made from the menu is written with it: the profile above the armature (a model of its own, `armature_1_cut`), the armature with `profile=armature_1_cut`, and `armature_1_face = cut_face(armature_1)` under it. The face is the armature's **child** in the model tree: it is hidden, isolated, copied and deleted with it, and a profile dropped on it replaces the cross-section.
  To use another cross-section, **drop a profile on the armature** in the model tree (or on the profile the armature uses): it takes its place in the call.
- **`character(armatures, blend="auto", symmetric=None)`** joins the armatures into one body with a smooth blend where they meet, and with `symmetric="x"` adds the mirror image. The default blend, `"auto"`, is as wide as the armature that is joined is thick, so a branch grows out of its parent the way a limb grows out of a body, whatever the size of the character; `blend=3` is 3 mm everywhere (0: none).
- **`skeleton_of(armatures, mirror=None, plane=0.0, join=None)`** makes a joint at each node, named by the armature's `joints` (or `name_0`, `name_1` ...). An armature whose first
  node is the same place as a joint of an earlier armature (within half a millimetre: the same point, or the same place typed again) is a **branch** of it: that
  joint is its first and its other nodes hang from it. An armature that is not on any joint hangs from the joint `parent=` names. `mirror="x"` gives every joint whose
  name ends with `.R` a `.L` one across that plane. There is one root, the first node of the first armature.
- **Joints with a place of their own.** `joint(name, position, parent, tip, influence=body_or_field)` owns the skin where `influence` is negative: the jaw
  follows the jaw alone inside its box, and fades to the weights of the bones over `skin_falloff`. `mirror_joints` mirrors the influence with the joint.
- **`export_mesh(..., max_influences=4)`**: the most joints that move a vertex, 1 to 8 (4 is what engines run; above 4 the file has `JOINTS_1` and `WEIGHTS_1` as well).

[`examples/40_armature.py`](../examples/40_armature.py) builds the figure of example 33 from armatures, reads the rigged file back and checks the joints, the hierarchy,
where the weights go, the jaw's influence and the bones a vertex can have.

### Building a character in the viewport

The **Characters** section of the right-click menu is made for building this by hand, node after node, the way Dust3D does -- with a camera you can turn. It has nothing to do with the
work plane, which is for 2D drawing only:

1. **Reference image →** *Front* (then *Right*): choose a drawing of the character; `reference_image(...)` stands it in the scene behind the models ([Reference images](interface.md#reference-images)).
   Set `height` and `center` in the script so that it is the size of the character and stands on the ground.
2. **New armature**: click the nodes one after another -- the spine, the neck, an arm, a leg. **Each click writes its node into the script at once**: a point with its gizmo, in the list of
   an `armature(...)` call. A node goes in the plane through the node before it that faces the camera, so turning the view to the side puts the next node in depth. A node's scale is how
   thick the armature is there; drag a node to move it. As the cursor moves, a ring shows how thick the next node will be -- as thick as the node before it, and the armature through it is drawn; **Shift + mouse wheel** makes it thicker or thinner before the click, and the next node is as thick as this one again -- and the armature stays selected after every click, so the rings of all its nodes stay on the screen -- and the nodes in the middle are corners: only the first and the last are spline points. **Right click** (or `Esc`, or `Enter`) says this armature is done -- the next click begins another one -- and a right click again
   leaves the mode. `Ctrl+Z` takes the last node back.
3. **Click a node** of an armature to go on from it: the next click puts a node after it. From a node in the middle the armature **branches**: a new `armature(...)` that begins on that same
   point (the arm on the chest), as thick there as the armature it grows from. The menu of a node has **Add nodes from here** for the same.
4. **New character** -- the first entry of the section, with the character icon (select the armatures, or right-click one) -- joins them with a blend, `symmetric="x"` adds the mirror image, and **skeleton_of** makes the joints for the export. In the model tree the character holds its armatures, and each armature holds its points.

## Features: feature models

An armature has the same cross-section all along. For the **delicate parts** -- a face, an ear, a hand -- use a **feature model**: a surface made through **features** -- loops of points -- the way Dust3D's
*feature models* model a face from a reference picture. You draw the outline of the face, of an eye, of the mouth, over the picture; **every point you place is a vertex of the
surface** -- none is added, none is moved -- and **every feature is an edge loop of it**, wherever the points are dragged.

```python
outline = feature([point(0, 0.5, -10), point(4, 0.2, -9), point(7, 0, -5), point(8.5, 0, 0), point(8, 0, 5), point(5, 0.2, 9), point(0, 0.5, 10)])   # half of the face
eye = feature_ring((3.2, -0.4, 3), 1.3, 8)                                    # a closed feature of 8 points: a centre, a radius (or wide and high), how many
nose = feature([(0, -1.5, 1), (0.8, -1.0, -1.5), (0, -1.6, -2.5)])      # points are tuples of numbers or point(...) models, dragged with their gizmos
face = feature_model([outline, eye, nose], mirror="x", name="face")
hero = character([head, face], blend=1)
```

The points are joined in the plane of a **view** (the front view by default: x to the right, z up): a Delaunay triangulation of the points seen from there, with every loop edge
forced into it. The points keep their places in space -- each has its own depth, y in the front view -- so the view only decides what is joined to what; a face is stitched from the
front, an ear from `view="right"`, anything from along any direction. Dust3D has two views; here you drag the points in the whole viewport.

**Nothing is automatic unless the arguments ask for it.** Each is written in the script (the *New feature model* entry writes them all, for half a face), and a feature can say its own choice:

| `feature_model(loops, ...)` | |
|---|---|
| `view="front"` | `"front"`, `"back"`, `"left"`, `"right"`, `"top"`, `"bottom"`, or `(direction, up)`: the direction you look along and which way is up in the picture |
| `mirror=None` | no mirror: the loops are used as they are. `"x"`, `"y"`, `"z"`, `("x", 2)` (the plane x = 2) or `(point, normal)` mirrors them across that plane. An open loop is **half of a shape**: with both ends on the plane it becomes a ring (A-B-C-D-C'-B'), with one end on it a path (A-B-C-D-C'-B'-A'), with neither it gets a mirror image of its own; a ring on one side gets a mirror image; a loop across the plane stays as it is |
| `snap=0` | how near the plane the end of an open loop may be to be put onto it (0: only the ends on it already) |
| `openings=True` | a closed loop with nothing in it, inside another closed loop, is an **opening** (an eye, a nostril), not surface. `False`: every loop is stitched across |
| `trim=True` | drop the triangles that join the points of one loop alone outside every closed loop (`False`: keep all that the triangulation makes) |
| `fill_holes=8` | close holes of this many edges or fewer (0: none). An opening is not a hole |
| `back=False` | `True` closes the outer boundary with rings that shrink to a point behind the surface, so it is a solid; `back_depth=1` is how deep (a share of the mean radius), `back_sharpness=0` (0 to 1) how much the rings keep the shape of the outline |
| `thickness=0.2` | an open surface is a **shell** of this thickness (the surface is its middle); a closed one is a solid |
| `name=None` | what the UV map and the model tree call it |

`feature(points, closed=None, mirror=None, opening=None)` is one feature: a list of points, or a polyline, spline or profile (their points are the nodes). `closed=True` joins the last point to
the first. `mirror=False` keeps this loop from being mirrored, `True` mirrors it across the plane of the feature, or give it a plane of its own. `opening=True` makes a closed loop an
opening whatever is in it; `False` stitches it across. `feature_ring(center, radius, count, facing)` makes a round closed feature.

- If two loops cross, the surface cannot have both as edge loops: the error names the loops and the view -- move a point, or look at the part from another side.
- A closed back leaves the openings (an eye) open, so such a feature is a shell of `thickness` and not a solid; close it by switching the eye to `opening=False`, or leave the back off.
- The surface is a mesh, and the feature is the exact distance to it, so it blends with the other parts and is exported with them. It is made when the script runs: dragging a point changes the
  surface when the script runs again, not while the drag is going on, as the sweep of an armature does.
- A feature is **skin, not bone**: `skeleton_of` leaves it out, and the export skins it to the nearest joints.

### UV maps by part

`export_mesh(hero, "hero.glb", uvs="armature")` (or `uv_armature(margin, size)`) lays the texture out from the **armature the character was made of**, not from the mesh alone.
Every triangle belongs to the part -- armature or feature -- whose surface it is nearest to; each part is an **island** of its own, laid flat from what it is:

- a **armature** as a tube along its path: u goes round the path, v along it, the seam straight along the back (the character faces -y), the rounded ends carried on past the first and the last node;
- a **feature** flat, as it was drawn: in the picture of the view it was stitched in (u to the right, v up), so that a texture painted over the reference picture of a face lands where it was
  drawn; the triangles that face away from the viewer -- the back of a shell, a closed back -- are an island of their own, seen from behind;
- both halves of a `character(..., symmetric="x")` get an island each, the second mirrored back so that a texture painted on one is not mirrored on the other.

The islands are in millimetres, so a texel is the same size everywhere, and none is turned: the texture runs the way the part runs. Packed into the square with `margin` texels between them.
`uvs="unwrap"` (the surface cut into islands where it turns) stays for models that are not made of an armature.

## The other half

A body is modelled once and mirrored. `symmetric_x(body)` keeps the part with x of 0 or more and adds its mirror image, so the left arm follows the right
one while you drag it. For a mesh that is symmetric to the last bit -- for a game engine's mirrored skinning and normal maps -- export with the mesh's
own symmetry instead: `export_mesh(body, "hero.glb", symmetric="x")` cuts the half exactly at x = 0 and mirrors it, with no seam
(see [Units, axes, a budget of triangles, symmetry](meshes.md#units-axes-a-budget-of-triangles-symmetry)).

## The skeleton

A character is rigged with `joint(...)`s -- the same points the armatures are made of can be the joints -- and `export_mesh(body, "hero.glb", skeleton=bones)` writes
them with the skin weights for a game engine: see [Skeleton and skin weights](meshes.md#skeleton-and-skin-weights-gltf). `mirror_joints` makes the left side of a
skeleton from the right, as `symmetric_x` makes the left half of the body.
[`examples/36_skeleton.py`](../examples/36_skeleton.py) does it for the figure of example 33.

## Menus

In the viewport's menu of empty space the shapes the library makes of points are under **Parametric shapes**; select points first and the entry is made
from them, in the order you selected them. The same is true of a profile, a polyline and a spline.
