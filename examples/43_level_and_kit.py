# A level from the space inside it, and a modular kit.
#
# LEVEL: you say where the EMPTY space is -- rooms and a corridor -- and the walls are what is left round it: the same thickness everywhere, a corridor that runs
# into a room opens into it, a doorway or a window is a cutter.  Here the roof is cut away to show the plan; take the `plan` line out to see the outside.
#
# KIT: pieces that are one grid cell each and end exactly on the cell's faces, set out by a floor plan.  `walls.check()` asks the pieces what is solid on the faces
# they share (an empty list: every piece meets every other).
# One number of this scene is one metre.
from fieldev import *

view.set_bounds([-4, -4, -2], [60, 28, 12])
view.set_resolution(4)
view.set_quality(8)

# ---- the level
hall = room((0, 0, 0), (12, 8, 3.5))
cell = room((16, 1, 0), (22, 7, 3.5))
link = corridor([(10, 4, 0), (19, 4, 0)], width=2.4, height=2.8)           # from inside the hall to inside the cell
gate = doorway((-0.2, 4, 0), width=1.6, height=2.4, axis="x", arch=True)   # a door with a round top, in the hall's west wall
look = window_opening((6, 8.2, 0), width=1.4, height=1.2, sill=1.0, axis="y")
keep = build_level([hall, cell, link], openings=[gate, look],
                   solids=[staircase((2, 1, 0), (2, 6, 1.5), width=1.6, steps=8), pillar((9, 2), radius=0.35, height=3.5, capital=0.3)])
plan = difference(keep, box((-5, -5, 1.8), (30, 15, 10)))                  # the roof cut away
plan

# ---- the kit
walls = kit(cell=(4, 4, 3), wall=0.3, floor=0.25)
problems = walls.check()                                                   # [] when every piece meets its neighbours
house = walls.build(["#####",
                     "#####",
                     "##  #"], edges={(2, 2, 2): "door", (1, 0, 0): "window", (1, 1, 1): "arch"}, ceiling=False)
house = move(house, (30, 2, 0))                                            # a kit is built at the origin and put where it is wanted
house
