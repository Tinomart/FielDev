# Custom blocks: your own functions, kept in a folder, there in every script.
#
# Every function in a .py file of the blocks folder is a block.  This repository's `blocks/sample_blocks.py` has four:
#
#     windows(body, radius, spacing)    a grid of round windows right through a wall
#     rounded(body, radius)             smooths every edge and bump smaller than the radius
#     hollow(body, wall)                a body hollowed to a wall, empty inside
#     stairs(steps, width, rise, run)   a flight of steps
#
# There is nothing to import: they are used like sphere() or smooth(), with call tips, completion (Ctrl+Space) and the
# right-click menus (Operations > Custom blocks).  Ctrl+click a block's name to read it; edit it, save the file, and this
# script runs again.  Settings > Blocks folder... chooses another folder, for blocks of your own.
#
# A block is a few lines:
#
#     def windows(body, radius=2.0, spacing=10.0):
#         ''' Cuts a grid of round windows right through a wall, along z '''
#         holes = repeat(cylinder(radius, 100000, (0, 0, -50000)), (spacing, spacing, 0))
#         return difference(body, holes)
#
# Every number of a block can be a field, like every number of the library: the windows below get bigger along x.
from fieldev import *

view.set_bounds([-5, -5, -5], [95, 95, 45], auto_scale=True)
view.set_resolution(5)
view.set_quality(8)

tile = box((0, 0, 0), (90, 50, 6))
wall = windows(tile, ramp(x_field(), (0, 90), (1.0, 3.5)), 10)      # the radius of the windows is a field
wall = gizmo(
    wall,
    move=(var(0), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(1), var(1), var(1)),
)
wall

flight = stairs(6, 30, 3, 5)
moved = move(flight, (0, 60, 0))
moved = gizmo(
    moved,
    move=(var(0), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(1), var(1), var(1)),
)
moved
