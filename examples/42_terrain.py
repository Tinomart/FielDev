# Terrain as a field: hills from noise, a hill, a flat place to build on, a road, a river and a cave -- all arithmetic on one field, so nothing leaves a seam --
# shown in grass, rock, sand, road and river bed by the slope, the height and the paths of the ground (see docs/gamedev.md).
#
#   ground = terrain(size=(120, 120), height=5, scale=40, seed=3)         the slab: a solid whose top is noise
#   ground.raised(...)  .flattened(...)  .road(...)  .river(...)  .cave(...)      each gives a new ground; the old one is left as it was
#   ground.textured(snow_line=9, beach=0.5)                               the materials: where the ground is steep, high, low
#   ground.chunk(ix, iy, 60)    ground.chunks(60)                                 squares of the ground that fit exactly: they are cut from the one field
#
# What to look at: the road keeps its width over the hill; the river's banks slope into the ground; the flat place is flat; the cave goes into the hill (it is
# a cut of the solid -- a heightmap cannot have one); rock shows where the ground is steep, sand where it is low.  One number of this scene is one metre.
from fieldev import *

view.set_bounds([-60, -60, -25], [60, 60, 30])
view.set_resolution(0.8)
view.set_quality(8)

ground = terrain(size=(120, 120), height=5, scale=40, seed=3)
ground = ground.raised((20, -10), radius=18, height=10)                     # a hill
ground = ground.flattened((-30, 25), radius=9)                              # a flat place, as high as the ground is at its middle
ground = ground.road([(-55, -40), (-20, -10), (15, 5), (55, 30)], width=5)  # a road: a place with no height is as high as the ground is there
ground = ground.river([(-50, 50), (-10, 20), (40, -50)], width=5, depth=2)  # a channel with banks
ground = ground.cave([(10, -30, 2), (20, -12, 5), (28, 4, 7)], radius=3.5)  # a tunnel through the hill

shown = ground.textured(snow_line=9, beach=-1.0)                            # grass, rock, sand, snow, the road and the river bed
shown
