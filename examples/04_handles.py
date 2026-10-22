# Edit a part by dragging.
#
# Two ways of editing a part by dragging in the viewport work together:
#   handles  hover a surface of the part and drag it: the numbers that place that surface change
#            (a call `x = handles(x, [var(...), ...])` is written under the part).  This is always there.
#   gizmo    arrows (move), rings (rotate) and squares (scale) at the part; the numbers you drag
#            are written into the var(...) arguments of the call `x = gizmo(x, move=..., rotate=..., scale=...)`
#            below.  Where it is shown it can be grabbed where it is drawn; a press next to it on the part drags the part's surface.
# The gizmo button of the model tree row (key E) says when the gizmo is shown: click (the default: while
# the part is selected), never, always -- E goes round them.  Try them.
# The lock button beside it (key R) is a switch of its own: `crate = lock(crate)` under the part, and
# nothing can be dragged until the line is deleted.
#
# The part here, a small crate, has its gizmo call.  Click the part and drag the gizmo's blue arrow: the third number moves.
#
from fieldes import *

view.set_bounds([-30, -30, -5], [30, 30, 45])
view.set_resolution(2)
view.set_quality(8)

body = rounded_box((-20, -20, 0), (20, 20, 40), 0.1)
slots = union(box((-22, -6, 4), (22, 6, 36)), box((-6, -22, 4), (6, 22, 36)))
crate = difference(body, slots)

crate = gizmo(
    crate,
    move=(var(0), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(1), var(1), var(1)),
)
crate
