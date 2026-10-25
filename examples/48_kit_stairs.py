# Stairs in a kit's plan: `stairs={(i, j, k): turn}` puts a stairs piece in the cell (i, j) of level k, rising towards north, west, south or east for turn 0, 1, 2, 3;
# the floor above it is left out, and it leads up into the next cell in that direction (see docs/gamedev.md).
#
#   walls = kit(cell=(4, 4, 3), wall=0.3, floor=0.25)
#   walls.build(plan, levels=2, stairs={(0, 0, 0): 3})        stairs in the south-west cell, rising east into the cell beside it, one level up
#
# What to look at: the stairs reach the floor of the next cell at the height of its top; there is no floor above the stairs; the outside walls stand on both levels.
# The roof is left off (`ceiling=False`) so that you can look in.
# The kit's seam check (`walls.check()`) does not cover stairs.  One number of this scene is one metre.
from fieldev import *

view.set_bounds([-1, -1, -0.5], [13, 9, 7])
view.set_resolution(6)
view.set_quality(8)

walls = kit(cell=(4, 4, 3), wall=0.3, floor=0.25)
house = walls.build(["###",
                     "###"], levels=2, ceiling=False, edges={(1, 0, 0): "arch", (2, 1, 2): "window"}, stairs={(0, 0, 0): 3})
house
