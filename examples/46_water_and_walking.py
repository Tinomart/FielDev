# Water in a river, and a check of where a character can walk -- both are arithmetic on the one height field of the ground (see docs/gamedev.md).
#
#   ground.river(...)                the channel (as in example 42)
#   ground.river_water(0.4)          its water: a body of its own that fills the channel to 0.4 below the ground the river was cut into, and follows the river downhill
#   ground.steep_places(32)          the ground in its colours, with red wherever it is steeper than 32 degrees
#   ground.walkable_fraction(32)     how much of the ground is not: a number from 0 to 1
#   export_terrain_chunks(ground, "world", 35, lods=[4000, 1000, 250])    every square of the world at three levels of detail: the field is meshed coarser, not cut down
#
# What to look at: the water ends where the bank rises above it; the red places are the steep sides of the hills (the road and the flat place are not red);
# the number is in the output.  One number of this scene is one metre.
from fieldev import *

view.set_bounds([-35, -35, -12], [35, 35, 14])
view.set_resolution(0.7)
view.set_quality(8)

ground = terrain(size=(70, 70), height=4, scale=30, seed=11)
ground = ground.flattened((-18, -15), radius=8)                              # a place to build on
ground = ground.river([(-34, 20), (-8, 8), (14, -4), (34, -20)], width=5, depth=2.5)
ground = ground.road([(-30, -30), (-18, -15), (0, -12), (30, -5)], width=4)

print("a character can walk on %.0f%% of the ground (up to 32 degrees)" % (100 * ground.walkable_fraction(32, samples=24)))

shown = ground.steep_places(32)
lake = ground.river_water(0.4)
shown
lake
