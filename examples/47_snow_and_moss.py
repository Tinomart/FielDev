# Snow, moss and dust as geometry: `covered(model, depth, angle)` lays a cover of that depth on every surface that faces up -- thickest where it faces straight up, thinning
# to nothing at `angle` degrees from straight up -- and gives it a material of its own (see docs/gamedev.md).
#
#   covered(rock(size=1.3, seed=7), depth=0.1, angle=55)                         snow on a rock
#   covered(crate(1.0), depth=0.05, angle=60, name="moss", color="#4f7a34")      moss on a crate
#   covered(barrel(), depth=0.04, angle=45, name="dust", color="#b9a98a")        dust on a barrel
#
# It is arithmetic on the field of the model (which way its surface faces), so it works on anything: a prop, a piece of a kit, a level.  What to look at: the cover is
# thick on top and gone on the sides; the rock keeps its stone below the snow, the crate its wood; one number of this scene is one metre.
from fieldev import *

view.set_bounds([-2, -2, -0.2], [9, 3, 3.5])
view.set_resolution(12)
view.set_quality(8)

snowy_rock = covered(rock(size=1.3, seed=7), depth=0.1, angle=55)
mossy_crate = covered(crate(1.0), depth=0.05, angle=60, name="moss", color="#4f7a34")
dusty_barrel = covered(barrel(), depth=0.04, angle=45, name="dust", color="#b9a98a")
snowy_pine = covered(tree(height=3.2, kind="pine", seed=2, crown=1.1), depth=0.08, angle=60)

row = merge([placed(snowy_rock, (0, 0, 0)), placed(mossy_crate, (2.8, 0, 0), turn=20), placed(dusty_barrel, (4.8, 0, 0)), placed(snowy_pine, (7, 0, 0))])
row
