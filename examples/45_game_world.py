# A small game world, made of fields: terrain with a hill, a road, a river and a cave; a keep built from the space inside it, a house from a modular kit; trees, rocks,
# crates and barrels that stand on the ground where its slope and a rule of ours allow.  Everything is arithmetic on fields, so nothing has a seam -- and the materials
# of the ground (grass, rock, sand) follow its slope and height.
#
# TRY: drag a material from View > Materials onto the keep, the house, a tree: a line `keep = with_materials(keep, material_preset("stone"))` is written under it.
#      Change a number of the ground (the hill's height, the road's path) and everything that stands on it is placed again.
#
# One number of this scene is one metre.  It is a large scene: give it a moment to mesh.
#
#   export_terrain_chunks(ground, "world", 80)           the ground in squares, with its materials
#   export_scatter(trees, "world", name="tree")           the trees: each variant once, and the list of where they stand
import math
from fieldev import *

view.set_bounds([-80, -80, -22], [80, 80, 30])
view.set_resolution(0.7)
view.set_quality(8)

# ---- the ground
ground = terrain(size=(160, 160), height=5, scale=55, seed=11, ridges=0.25)
ground = ground.raised((45, 35), radius=26, height=14)                       # a hill ...
ground = ground.flattened((-30, 45), radius=22)                               # a plot to build on
ROAD = [(-75, -50), (-45, -10), (-10, 20), (20, 30), (60, 10), (78, -20)]
ground = ground.road(ROAD, width=5)
ground = ground.river([(70, 75), (40, 40), (10, 5), (-10, -30), (-20, -78)], width=7, depth=2.5)   # it crosses the road: a ford
ground = ground.cave([(30, 20, 3), (42, 33, 7), (52, 44, 10)], radius=3.0)    # ... with a cave in it

land = ground.textured(snow_line=14, beach=-0.5)
land
lake = water(size=(158, 158), level=-3.0, depth=2.5)
lake

# ---- a keep, from the space inside it: a hall and a tower, a door between, a gate, an arrow slit, a pillar
floor = ground.height_at(-30, 45) + 0.05
hall = room((-38, 38, floor), (-24, 52, floor + 4))
tower = room((-23.6, 42, floor), (-17.6, 48, floor + 9))
door = doorway((-23.8, 45, floor), width=1.8, height=2.6, axis="x", arch=True)
slit = window_opening((-17.4, 45, floor), width=0.8, height=2.0, sill=3.0, axis="x")
gate = doorway((-31, 37.8, floor), width=2.4, height=3.0, axis="y", arch=True)
keep = build_level([hall, tower], openings=[door, slit, gate], solids=[pillar((-34, 45), radius=0.4, height=4, base=floor, capital=0.3)])
keep

# ---- a house, from a kit of pieces that fit on a grid
walls = kit(cell=(3, 3, 2.6), wall=0.25, floor=0.2)
house = move(walls.build(["##", "##"], edges={(0, 1, 2): "door", (1, 0, 0): "window"}), (-20, 30, floor))
house


# ---- what stands on the ground: where it is flat enough (max_slope) and a rule of ours allows
def near_road(x, y, reach=6.0):
    for (ax, ay), (bx, by) in zip(ROAD, ROAD[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        if math.hypot(x - ax - t * dx, y - ay - t * dy) < reach:
            return True
    return False


def on_plot(x, y):
    return math.hypot(x + 30, y - 45) < 24


trees = scatter(lambda s: tree(height=6 + s % 3, seed=s, crown=1.8 + 0.2 * (s % 2), kind="pine" if s % 3 == 0 else "round"), 28, ground=ground, seed=5,
                min_distance=7, max_slope=22, where=lambda x, y, z: z > 0.5 and not near_road(x, y) and not on_plot(x, y), variants=4)
trees
rocks = scatter(lambda s: rock(0.7 + 0.3 * (s % 3), seed=s, crag=0.5), 14, ground=ground, seed=9, min_distance=5, max_slope=70,
                where=lambda x, y, z: ground.slope_at(x, y) > 14 and not near_road(x, y), variants=3)
rocks
yard = merge([placed(crate(1.0), (-35, 36.2, floor), turn=15), placed(crate(0.8), (-36.3, 36.4, floor), turn=-10),
              placed(barrel(), (-26.5, 36.4, floor)), placed(barrel(), (-25.7, 36.6, floor))])
yard
