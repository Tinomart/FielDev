# Characters

A character is modelled from **points**: a skeleton of joints, each with a size, and the flesh round them. `chain` makes a limb through points,
`round_cone` is the segment it is made of. Both are fields like everything else in the library, so a character is blended, offset, textured, mirrored and
exported like any other model (see [Meshes](meshes.md)).

```python
from fieldes import *

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

## The other half

A body is modelled once and mirrored. `symmetric_x(body)` keeps the part with x of 0 or more and adds its mirror image, so the left arm follows the right
one while you drag it. For a mesh that is symmetric to the last bit -- for a game engine's mirrored skinning and normal maps -- export with the mesh's
own symmetry instead: `export_mesh(body, "hero.glb", symmetric="x")` cuts the half exactly at x = 0 and mirrors it, with no seam
(see [Units, axes, a budget of triangles, symmetry](meshes.md#units-axes-a-budget-of-triangles-symmetry)).

## Menus

In the viewport's menu of empty space the shapes the library makes of points are under **Parametric shapes**; select points first and the entry is made
from them, in the order you selected them. The same is true of a profile, a polyline and a spline.
