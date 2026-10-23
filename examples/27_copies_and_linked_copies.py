# Two kinds of duplicate: a COPY and a LINKED copy.
#
# With a model selected and the viewport (or the model tree) focused:
#
#   Shift+D   a COPY: the model's statements are written again under it, with free names. The copy is a model of its own: change either and
#             the other stays as it was.  (Below: lug_2, a second lug that is a copy of lug and was then made thicker.)
#   Ctrl+D    a LINKED copy: `peg_2 = instance(peg)`. It IS the peg -- the same shape, the same size, every property -- and follows it: change the
#             peg and all its linked copies change with it. All a linked copy has of its own is WHERE it is: it can only be moved and rotated, its
#             gizmo has no scale and its surfaces cannot be dragged. The peg is held by a reference (`# shadow: peg`): it keeps its own row in the
#             model tree and each copy shows a faded "shadow" of it, whether the peg is locked or not.
#
# Things to try:
#   * Drag a face of the peg (its top, its side): the three linked copies change with it. Do the same to lug_2: lug is not affected.
#   * Select peg_3, press Shift and look at the gizmo: the arrows become flat squares that move it along a plane, and the three scale squares
#     are replaced by ONE gold ring that scales everything evenly -- which a linked copy does not have: it is not scaled.
#   * Select the peg and press Ctrl+D for a fourth one; Operation > Repeating > instance does the same.
from fieldev import *

view.set_bounds([-15, -15, -5], [95, 55, 40], auto_scale=True)
view.set_resolution(2)
view.set_quality(8)

# A tile with a lug, and a copy of the lug that was made thicker.
base = box((-10, -10, 0), (90, 40, 4))
base
lug = box((0, 10, 4), (14, 20, 24))
lug
lug_2 = box((60, 10, 4), (74, 20, 24))
lug_2 = handles(lug_2, [var(67.0), var(7.0), var(18.0), var(8.0), var(14.0), var(10.0)])
lug_2

# One peg, drawn with its numbers as handles, and three linked copies of it set out along the tile.
peg = cylinder(3, 12, (20, 30, 4))
peg = handles(peg, [var(20.0), var(30.0), var(3.0), var(4.0), var(16.0)])
peg
peg_2 = instance(peg)  # shadow: peg
peg_2 = gizmo(
    peg_2,
    move=(var(15), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
)
peg_2
peg_3 = instance(peg)  # shadow: peg
peg_3 = gizmo(
    peg_3,
    move=(var(30), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
)
peg_3
peg_4 = instance(peg)  # shadow: peg
peg_4 = gizmo(
    peg_4,
    move=(var(45), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
)
peg_4
