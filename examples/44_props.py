# Props: a rock, three kinds of tree, a crate and a barrel -- made by number, varied by seed, each in its own materials -- set in a row, and then scattered over
# terrain by a field's rules (see docs/gamedev.md).
#
#   rock(size, seed, roughness, flat, crag)   tree(height, trunk, crown, seed, kind)   crate(size)   barrel(radius, height)
#   placed(prop, (x, y, z), turn=30, scale=1.2)    merge([a, b, c])                    the materials go with them
#   scatter(make, count, ground=..., min_distance, max_slope, where, variants)         props where the ground is flat enough and a rule allows
#   export_scatter(forest, "out/forest")                                              the few meshes once, and a list of places for an engine
#
# One number of this scene is one metre.
from fieldev import *

view.set_bounds([-4, -30, -10], [92, 30, 16])
view.set_resolution(3)
view.set_quality(8)

row = merge([placed(rock(1.2, seed=3, crag=0.4), (0, 0, 0)),
             placed(tree(6, seed=2), (6, 0, 0)),
             placed(tree(7, kind="pine", seed=4), (12, 0, 0)),
             placed(tree(kind="bush", crown=1.2), (17, 0, 0)),
             placed(crate(1.0), (21, 0, 0), turn=20),
             placed(barrel(), (24.5, 0, 0))])
row

field = terrain(size=(50, 50), height=3, scale=25, seed=5, center=(62, 0))
grove = scatter(lambda s: tree(height=6, seed=s, crown=1.8), 14, ground=field, seed=2, min_distance=6, max_slope=25, variants=2)
field = field.textured(beach=-2.0)
field
grove
